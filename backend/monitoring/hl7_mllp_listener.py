"""Mindray HL7 (MLLP) — port 6006, peer IP yoki MSH-3 bo'yicha Device."""
from __future__ import annotations

import logging
import socket
import threading
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import close_old_connections

from monitoring.asgi_support import schedule_coro
from monitoring.io_bus import sio
from monitoring.models import Device
from monitoring.services.device_ingest import apply_device_vitals_dict
from monitoring.services.hl7_obx import extract_msh_sending_application, obx_to_vitals_dict

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

_thread_started = False
_lock = threading.Lock()


def _peer_ip(addr: tuple) -> str:
    ip = addr[0]
    if isinstance(ip, str) and ip.startswith("::ffff:"):
        return ip[7:]
    return ip


def _find_device(msg: str, peer: str) -> Device | None:
    close_old_connections()
    app = extract_msh_sending_application(msg)
    if app:
        q = Device.objects.filter(hl7_sending_application=app).exclude(
            hl7_sending_application=""
        )
        dev = q.first()
        if dev:
            return dev
    return Device.objects.filter(ip_address=peer).first()


def _process_one_message(msg: str, peer: str) -> None:
    vitals = obx_to_vitals_dict(msg)
    if not vitals:
        log.debug("HL7: OBX dan vital topilmadi (peer=%s)", peer)
        return
    dev = _find_device(msg, peer)
    if not dev:
        log.warning("HL7: Device topilmadi peer=%s", peer)
        return
    payload = apply_device_vitals_dict(dev, vitals)
    if payload:
        schedule_coro(sio.emit("vitals_update", [payload]))


def _handle_client(conn: socket.socket, addr: tuple) -> None:
    peer = _peer_ip(addr)
    buf = bytearray()
    try:
        conn.settimeout(300.0)
        while True:
            chunk = conn.recv(8192)
            if not chunk:
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
    finally:
        try:
            srv.close()
        except OSError:
            pass


def start_hl7_listener_if_enabled() -> None:
    global _thread_started
    if not getattr(settings, "HL7_LISTENER_ENABLED", True):
        log.info("HL7 listener o'chirilgan (HL7_LISTENER_ENABLED).")
        return
    host = getattr(settings, "HL7_LISTEN_HOST", "0.0.0.0")
    port = int(getattr(settings, "HL7_LISTEN_PORT", 6006))
    with _lock:
        if _thread_started:
            return
        _thread_started = True
    th = threading.Thread(
        target=_serve_forever,
        args=(host, port),
        daemon=True,
        name="hl7-mllp-listener",
    )
    th.start()
