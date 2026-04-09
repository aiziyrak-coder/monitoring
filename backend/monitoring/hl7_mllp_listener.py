"""HL7 ORU^R01 (MLLP) — port 6006: Mindray, Creative K12 / Comen uslubi, peer IP yoki MSH-3 bo'yicha Device."""
from __future__ import annotations

import datetime
import ipaddress
import logging
import socket
import sys
import threading
import time
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import close_old_connections

from monitoring.asgi_support import schedule_vitals_emit
from monitoring.models import Device
from monitoring.ingest_stats import (
    record_hl7_device_message,
    record_hl7_tcp_external_accept,
    record_hl7_tcp_external_no_device,
    record_hl7_tcp_session_with_device,
)
from monitoring.services.device_ingest import apply_device_vitals_dict
from monitoring.services.hl7_obx import extract_msh_sending_application, obx_to_vitals_dict

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

_listener_thread: threading.Thread | None = None
_lock = threading.Lock()


def _peer_ip(addr: tuple) -> str:
    ip = addr[0]
    if isinstance(ip, str) and ip.startswith("::ffff:"):
        return ip[7:]
    return str(ip)


def _normalize_peer_ip(peer: str) -> str:
    """Socketdan kelgan manzilni DB (GenericIPAddressField) bilan solishtirish uchun."""
    s = (peer or "").strip()
    if not s:
        return s
    try:
        ip_obj = ipaddress.ip_address(s)
        if isinstance(ip_obj, ipaddress.IPv6Address):
            if ip_obj.ipv4_mapped:
                return str(ip_obj.ipv4_mapped)
            return ip_obj.compressed
        return str(ip_obj)
    except ValueError:
        return s


def _resolve_device(msg: str, peer: str) -> Device | None:
    """
    Qurilmani aniqlash tartibi:
    1. MSH-3 (HL7 Sending Application) — aniq ID
    2. Lokal IP manzil
    3. NAT tashqi IP (hl7_nat_source_ip)
    4. Fallback: bitta qurilma bo'lsa, uni qaytaradi (HL7_NAT_SINGLE_DEVICE_FALLBACK)
    """
    close_old_connections()
    app = extract_msh_sending_application(msg)
    if app:
        q = Device.objects.filter(hl7_sending_application=app).exclude(
            hl7_sending_application=""
        )
        dev = q.first()
        if dev:
            return dev
    dev = Device.objects.filter(ip_address=peer).first()
    if dev:
        return dev
    nat_qs = Device.objects.filter(hl7_nat_source_ip=peer).exclude(
        hl7_nat_source_ip__isnull=True
    )
    nat_n = nat_qs.count()
    if nat_n > 1:
        log.warning(
            "HL7: bir xil NAT IP (%s) ga %s ta qurilma — birinchisi ishlatiladi; HL7 ID bilan ajrating",
            peer,
            nat_n,
        )
    dev = nat_qs.first()
    if dev:
        return dev

    # Fallback: agar faqat bitta qurilma ro'yxatda bo'lsa va sozlamada yoqilgan bo'lsa.
    if getattr(settings, "HL7_NAT_SINGLE_DEVICE_FALLBACK", False):
        all_devs = list(Device.objects.all()[:2])
        if len(all_devs) == 1:
            log.info(
                "HL7: NAT_SINGLE_DEVICE_FALLBACK — peer=%s uchun yagona qurilma %r ishlatildi",
                peer,
                all_devs[0].pk,
            )
            return all_devs[0]

    if msg:
        app2 = extract_msh_sending_application(msg)
        if app2:
            log.debug(
                "HL7: peer=%s MSH-3=%r — qurilma topilmadi; "
                "Qurilma sozlamalarida HL7 Sending Application ni %r ga tenglang",
                peer, app2, app2,
            )

    return None


def _obx_segment_count(msg: str) -> int:
    return sum(
        1
        for seg in msg.replace("\n", "\r").split("\r")
        if seg.strip().upper().startswith("OBX|")
    )


def _decode_hl7_bytes(raw: bytes) -> str:
    """Xitoy monitorlar (Comen/K12) GB18030; Yevropa UTF-8."""
    if not raw:
        return ""
    fallback: str | None = None
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "cp936", "latin-1"):
        try:
            t = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if fallback is None:
            fallback = t
        if "MSH|" in t:
            return t
    return fallback if fallback is not None else raw.decode("utf-8", errors="replace")


def _strip_bom(data: bytes) -> bytes:
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:]
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data[2:]
    return data


def _try_consume_unframed_hl7(buf: bytearray, peer: str) -> bool:
    """
    Ba'zi monitorlar MLLP boshlang'ich bayti (0x0B) yubormaydi yoki faqat FS+CR bilan tugatadi.
    True — kamida bitta xabar _process_one_message ga berildi.
    """
    did = False
    while True:
        data = _strip_bom(bytes(buf))
        if not data:
            return did
        i = data.find(b"MSH|")
        if i < 0:
            return did
        if i > 0:
            del buf[:i]
            data = bytes(buf)
            i = 0
        j = data.find(b"\x1c\x0d", 4)
        if j < 0:
            j = data.find(b"\x1c\r", 4)
        if j >= 0:
            raw = data[: j + 2]
            del buf[: j + 2]
            _process_one_message(_decode_hl7_bytes(raw), peer)
            did = True
            continue
        found_end = False
        for end_seq in (b"\r\x1c\x0d", b"\r\x1c\r", b"\r\x1c\n", b"\n\x1c\x0d", b"\n\x1c\r"):
            j2 = data.find(end_seq, 4)
            if j2 >= 0:
                raw = data[: j2 + len(end_seq)]
                del buf[: j2 + len(end_seq)]
                _process_one_message(_decode_hl7_bytes(raw), peer)
                did = True
                found_end = True
                break
        if found_end:
            continue
        k = data.find(b"\rMSH|", 10)
        if k < 0:
            k = data.find(b"\nMSH|", 10)
        if k >= 0:
            raw = data[:k]
            del buf[: k + 1]
            _process_one_message(_decode_hl7_bytes(raw), peer)
            did = True
            continue
        return did


def _try_consume_segment_only_oru(buf: bytearray, peer: str) -> bool:
    """
    FS va MLLP bo'lmasa, lekin segmentlar \\r yoki \\n bilan tugasa (ochiq TCP oqimi).
    Comen/K12 ko'pincha shunday yuboradi; ulanish yopilmasa ham har recv dan keyin tekshiriladi.
    """
    data = _strip_bom(bytes(buf))
    i = data.find(b"MSH|")
    if i < 0:
        return False
    if i > 0:
        del buf[:i]
        data = bytes(buf)
    du = data.upper()
    if b"OBX|" not in du:
        return False
    if not (data.endswith(b"\r") or data.endswith(b"\n")):
        return False
    text = _decode_hl7_bytes(data).strip()
    if "OBX|" not in text.upper():
        return False
    log.info(
        "HL7: faqat segment (\\r/\\n) bilan ORU, %s bayt peer=%s",
        len(data),
        peer,
    )
    try:
        _process_one_message(text, peer)
    except Exception:
        log.exception("HL7: segment-only qayta ishlash xato peer=%s", peer)
    buf.clear()
    return True


def _flush_hl7_buffer_on_close(buf: bytearray, peer: str) -> None:
    """Ulanish yopilganda MLLP/FS bo'lmagan qoldiqni bitta ORU deb qayta ishlash."""
    while _try_consume_unframed_hl7(buf, peer):
        pass
    if _try_consume_segment_only_oru(buf, peer):
        return
    if not buf:
        return
    data = _strip_bom(bytes(buf))
    if b"MSH|" not in data:
        if len(data) > 0:
            log.debug(
                "HL7: ulanish yopildi, MSH yo'q (%d bayt) peer=%s",
                len(data),
                peer,
            )
        buf.clear()
        return
    text = _decode_hl7_bytes(data).strip()
    if "MSH|" not in text:
        buf.clear()
        return
    log.info(
        "HL7: ulanish yopilganda to'liq xabar (FS/MLLP bo'lmasligi mumkin), %d bayt peer=%s",
        len(data),
        peer,
    )
    try:
        _process_one_message(text, peer)
    except Exception:
        log.exception("HL7: yopilishdagi buferni qayta ishlash xato peer=%s", peer)
    buf.clear()


def _process_one_message(msg: str, peer: str) -> None:
    dev = _resolve_device(msg, peer)
    obx_n = _obx_segment_count(msg)
    vitals = obx_to_vitals_dict(msg)

    if dev:
        # Agar MSH-3 mavjud va device da hl7_sending_application bo'sh bo'lsa — avtomatik saqlash
        app = extract_msh_sending_application(msg)
        if app and not dev.hl7_sending_application:
            Device.objects.filter(pk=dev.pk).update(hl7_sending_application=app)
            dev.hl7_sending_application = app
            log.info(
                "HL7: qurilma %r MSH-3=%r avtomatik saqlandi",
                dev.pk,
                app,
            )

        record_hl7_device_message(
            obx_segment_count=obx_n, vitals_non_empty=bool(vitals)
        )
        if vitals:
            payload = apply_device_vitals_dict(dev, vitals)
            if payload:
                schedule_vitals_emit([payload])
        else:
            empty_payload = apply_device_vitals_dict(dev, {})
            if empty_payload:
                schedule_vitals_emit([empty_payload])
            if obx_n:
                sample = ""
                for seg in msg.replace("\n", "\r").split("\r"):
                    s = seg.strip()
                    if s.upper().startswith("OBX|"):
                        sample = s[:240]
                        break
                log.warning(
                    "HL7: %s ta OBX bor, lekin vitallar ajratilmadi (peer=%s, device=%s). Birinchi OBX (240 belgigacha): %r",
                    obx_n,
                    peer,
                    dev.pk,
                    sample,
                )
            else:
                log.info(
                    "HL7: OBX yo'q — faqat ulanish / boshqa xabar (peer=%s); ORU vitallar yuborilishi kerak",
                    peer,
                )
        return

    app = extract_msh_sending_application(msg)
    if vitals:
        if app:
            log.warning(
                "HL7: Device topilmadi peer=%s MSH-3=%r — HL7 ID yoki «NAT tashqi IP»ni tekshiring",
                peer,
                app,
            )
        else:
            log.warning(
                "HL7: Device topilmadi peer=%s (MSH-3 yo'q) — lokal IP / NAT tashqi IP / HL7 ID",
                peer,
            )
    else:
        if "MSH|" in msg.upper() and len(msg.strip()) > 15:
            log.warning(
                "HL7: qurilma topilmadi peer=%s (NAT IP / lokal IP / HL7 ID ni tekshiring). "
                "Boshlang'ich matn: %r",
                peer,
                msg.replace("\r", "\\r").replace("\n", "\\n")[:400],
            )
        else:
            log.debug(
                "HL7: qurilma topilmadi va OBX yo'q peer=%s MSH-3=%r",
                peer,
                app,
            )


def _build_mllp_qry(msg_id: str) -> bytes:
    """
    Creative K12 / Comen uchun MLLP-framed HL7 QRY^Q01 xabari.
    Monitor bu so'rovni olganda joriy vitals bilan ORU^R01 javob berishi kerak.
    """
    now = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    msh = f"MSH|^~\\&|ClinSys|Hospital|PatMon|Device|{now}||QRY^Q01|{msg_id}|P|2.3\r"
    qrd = f"QRD|{now}|R|I|{msg_id}|||ALL|ALL|ALL|ALL\r"
    raw = (msh + qrd).encode("ascii", errors="replace")
    return b"\x0b" + raw + b"\x1c\r"


def _send_qry(conn: socket.socket, peer: str, msg_id: str) -> bool:
    """QRY yuborish. Muvaffaqiyatli bo'lsa True qaytaradi."""
    try:
        conn.sendall(_build_mllp_qry(msg_id))
        log.info("HL7: QRY^Q01 yuborildi peer=%s id=%s", peer, msg_id)
        return True
    except OSError as e:
        log.debug("HL7: QRY yuborishda xato peer=%s: %s", peer, e)
        return False


def _handle_client(conn: socket.socket, addr: tuple) -> None:
    peer = _normalize_peer_ip(_peer_ip(addr))
    _is_loopback = peer in ("127.0.0.1", "::1")

    max_buf = int(getattr(settings, "HL7_MAX_BUFFER_BYTES", 2 * 1024 * 1024))
    if not _is_loopback:
        record_hl7_tcp_external_accept(peer)
    log.info("HL7: TCP ulanish %s (port %s)", peer, settings.HL7_LISTEN_PORT)

    dev0: "Device | None" = None
    try:
        dev0 = _resolve_device("", peer)
        if dev0 and not _is_loopback:
            record_hl7_tcp_session_with_device()
            payload = apply_device_vitals_dict(dev0, {})
            if payload:
                schedule_vitals_emit([payload])
            log.info("HL7: TCP bilan qurilma onlayn (id=%s, peer=%s)", dev0.pk, peer)

            # Creative K12 uchun: ulanish o'rnatilganda QRY yuborib vitals so'raymiz
            send_qry = getattr(settings, "HL7_SEND_QRY_ON_CONNECT", True)
            if send_qry:
                _send_qry(conn, peer, f"QRY{int(time.time())}")
        else:
            if not _is_loopback:
                record_hl7_tcp_external_no_device()
            log.warning(
                "HL7: TCP peer=%s — tizimda mos qurilma yo'q. "
                "Qurilmalar: «NAT tashqi IP» aynan shu manzil (yoki HL7 MSH-3) bo'lishi kerak; "
                "klinika Internet IP odatda router sozlamasida ko'rinadi.",
                peer,
            )
    except Exception:
        log.exception("HL7: TCP dan keyin qurilma yangilash xato peer=%s", peer)

    buf = bytearray()
    _first_chunk_logged = False
    # Periodic QRY: agar ulanish davomida data kelmasa, har N sekundda qayta so'raymiz
    _qry_interval = int(getattr(settings, "HL7_QRY_INTERVAL_SEC", 30))
    _last_qry_time = time.time()
    _got_data = False

    try:
        conn.settimeout(5.0)  # recv timeout — periodic QRY uchun
        while True:
            try:
                chunk = conn.recv(8192)
            except TimeoutError:
                # recv timeout — data yo'q, periodic QRY yuboramiz
                if dev0 and not _is_loopback and not _got_data:
                    now = time.time()
                    if now - _last_qry_time >= _qry_interval:
                        _last_qry_time = now
                        ok = _send_qry(conn, peer, f"QRY{int(now)}")
                        if not ok:
                            break
                continue
            except OSError:
                break

            if not chunk:
                break

            if not _first_chunk_logged:
                _first_chunk_logged = True
                preview = chunk[:300].decode("utf-8", errors="replace").replace("\r", "\\r").replace("\n", "\\n")
                log.info("HL7: birinchi chunk peer=%s len=%d: %r", peer, len(chunk), preview)
                _got_data = True

            if len(buf) + len(chunk) > max_buf:
                log.warning(
                    "HL7: bufer limiti (%s bayt) oshdi peer=%s — ulanish yopildi",
                    max_buf,
                    peer,
                )
                break
            buf.extend(chunk)
            while True:
                try:
                    i0 = buf.index(0x0B)
                except ValueError:
                    break
                try:
                    i1 = buf.index(b"\x1c\x0d", i0)
                except ValueError:
                    break
                raw = bytes(buf[i0 + 1 : i1])
                del buf[: i1 + 2]
                text = _decode_hl7_bytes(raw)
                try:
                    _process_one_message(text, peer)
                except Exception:
                    log.exception("HL7 qayta ishlash xato peer=%s", peer)
            while _try_consume_unframed_hl7(buf, peer):
                pass
            if _try_consume_segment_only_oru(buf, peer):
                pass
    except OSError:
        pass
    finally:
        try:
            if buf:
                _flush_hl7_buffer_on_close(buf, peer)
        except Exception:
            log.exception("HL7: finally bufer flush peer=%s", peer)
        try:
            conn.close()
        except OSError:
            pass


def _serve_forever(host: str, port: int) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((host, port))
        srv.listen(32)
        log.info("HL7 MLLP tinglash: %s:%s", host, port)
        print(
            f"ClinicMonitoring HL7 MLLP tinglash: {host}:{port}",
            file=sys.stderr,
            flush=True,
        )
        while True:
            c, a = srv.accept()
            t = threading.Thread(
                target=_handle_client,
                args=(c, a),
                daemon=True,
                name=f"hl7-client-{a[0]}",
            )
            t.start()
    except OSError as e:
        log.error("HL7 server xato: %s", e)
        print(f"ClinicMonitoring HL7 xato: {e}", file=sys.stderr, flush=True)
    finally:
        try:
            srv.close()
        except OSError:
            pass


def start_hl7_listener_if_enabled() -> None:
    """django.setup() / AppConfig.ready() da chaqiring — uvicorn socket.io on_startup har doim ishlamasligi mumkin."""
    global _listener_thread
    if not getattr(settings, "HL7_LISTENER_ENABLED", True):
        log.info("HL7 listener o'chirilgan (HL7_LISTENER_ENABLED).")
        return
    host = getattr(settings, "HL7_LISTEN_HOST", "0.0.0.0")
    port = int(getattr(settings, "HL7_LISTEN_PORT", 6006))
    with _lock:
        if _listener_thread is not None and _listener_thread.is_alive():
            return
        _listener_thread = threading.Thread(
            target=_serve_forever,
            args=(host, port),
            daemon=True,
            name="hl7-mllp-listener",
        )
        _listener_thread.start()
