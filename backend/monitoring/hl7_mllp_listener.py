"""Mindray HL7 (MLLP) — port 6006, peer IP yoki MSH-3 bo'yicha Device."""
from __future__ import annotations

import ipaddress
import logging
import socket
import sys
import threading
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import close_old_connections

from monitoring.asgi_support import schedule_vitals_emit
from monitoring.models import Device
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
    """MSH-3, keyin lokal IP, keyin NAT tashqi IP — log yozmaydi."""
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
    return None


def _process_one_message(msg: str, peer: str) -> None:
    dev = _resolve_device(msg, peer)
    vitals = obx_to_vitals_dict(msg)

    if dev:
        if vitals:
            payload = apply_device_vitals_dict(dev, vitals)
            if payload:
                schedule_vitals_emit([payload])
        else:
            # Aksar holatda Mindray OBX kodlari parse qilinmasa ham ulanish «onlayn» bo‘lsin
            apply_device_vitals_dict(dev, {})
            obx_n = sum(
                1
                for seg in msg.replace("\n", "\r").split("\r")
                if seg.strip().startswith("OBX|")
            )
            if obx_n:
                log.warning(
                    "HL7: %s ta OBX bor, lekin vitallar ajratilmadi (peer=%s) — Mindray OBX kodini tekshiring",
                    obx_n,
                    peer,
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
        log.debug(
            "HL7: qurilma topilmadi va OBX yo'q peer=%s MSH-3=%r",
            peer,
            app,
        )


def _handle_client(conn: socket.socket, addr: tuple) -> None:
    peer = _normalize_peer_ip(_peer_ip(addr))
    max_buf = int(getattr(settings, "HL7_MAX_BUFFER_BYTES", 2 * 1024 * 1024))
    log.info("HL7: TCP ulanish %s (port %s)", peer, settings.HL7_LISTEN_PORT)
    # MLLP xabari kelmasa ham: NAT / lokal IP bo‘yicha qurilmani onlayn qilish
    try:
        dev0 = _resolve_device("", peer)
        if dev0:
            apply_device_vitals_dict(dev0, {})
            log.info(
                "HL7: TCP bilan qurilma onlayn (id=%s, peer=%s)",
                dev0.pk,
                peer,
            )
    except Exception:
        log.exception("HL7: TCP dan keyin qurilma yangilash xato peer=%s", peer)
    buf = bytearray()
    try:
        conn.settimeout(300.0)
        while True:
            chunk = conn.recv(8192)
            if not chunk:
                break
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
                try:
                    text = raw.decode("utf-8", errors="replace")
                except Exception:
                    text = raw.decode("latin-1", errors="replace")
                try:
                    _process_one_message(text, peer)
                except Exception:
                    log.exception("HL7 qayta ishlash xato peer=%s", peer)
    except TimeoutError:
        log.debug("HL7 client timeout peer=%s", peer)
    except OSError:
        pass
    finally:
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
