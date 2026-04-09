"""DEMO_VITALS_ENABLED=1 bo'lsa demo bemorda vitallarni yengil o'zgartiradi (taqdimot)."""
from __future__ import annotations

import logging
import random
import threading
import time

from django.conf import settings
from django.db import close_old_connections

from monitoring.asgi_support import schedule_vitals_emit
from monitoring.demo_constants import DEMO_PATIENT_IDS
from monitoring.models import Patient
from monitoring.services.device_ingest import build_vitals_socket_payload
from monitoring.services.patient_payload import patient_to_wire_dict

log = logging.getLogger(__name__)
_lock = threading.Lock()
_thread: threading.Thread | None = None


def _clamp_i(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def _clamp_f(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def _tick_once() -> None:
    close_old_connections()
    if not getattr(settings, "DEMO_VITALS_ENABLED", False):
        return
    now_ms = int(time.time() * 1000)
    interval = max(2.0, float(getattr(settings, "DEMO_VITALS_INTERVAL_SEC", 5.0)))
    tick = int(now_ms / 1000 / interval)
    payloads: list[dict] = []

    for pid in DEMO_PATIENT_IDS:
        p = Patient.objects.filter(pk=pid).first()
        if not p:
            continue
        rng = random.Random(hash((pid, tick)))

        p.hr = _clamp_i(int(round(p.hr + rng.gauss(0, 1.05))), 62, 90)
        p.spo2 = _clamp_i(
            int(round(p.spo2 + rng.gauss(0, 0.35))), 96, 99
        )
        p.nibp_sys = _clamp_i(int(round(p.nibp_sys + rng.gauss(0, 1.2))), 108, 132)
        p.nibp_dia = _clamp_i(int(round(p.nibp_dia + rng.gauss(0, 0.85))), 68, 84)
        p.rr = _clamp_i(int(round(p.rr + rng.gauss(0, 0.55))), 13, 20)
        p.temp = round(
            _clamp_f(p.temp + rng.gauss(0, 0.045), 36.3, 37.0),
            1,
        )
        p.nibp_time_ms = now_ms
        p.last_real_vitals_ms = now_ms
        p.alarm_level = Patient.ALARM_NONE
        p.alarm_message = ""
        p.device_battery = _clamp_f(
            p.device_battery + rng.uniform(-0.4, 0.3), 72.0, 99.0
        )

        p.save(
            update_fields=[
                "hr",
                "spo2",
                "nibp_sys",
                "nibp_dia",
                "rr",
                "temp",
                "nibp_time_ms",
                "last_real_vitals_ms",
                "alarm_level",
                "alarm_message",
                "device_battery",
            ]
        )
        wire = patient_to_wire_dict(p, omit_history=True)
        payloads.append(build_vitals_socket_payload(wire))

    if payloads:
        schedule_vitals_emit(payloads)


def _loop() -> None:
    interval = max(2.0, float(getattr(settings, "DEMO_VITALS_INTERVAL_SEC", 5.0)))
    log.info("Demo vitallar: ishchi yoqildi (har %.1f s, IDlar: %s)", interval, DEMO_PATIENT_IDS)
    while True:
        try:
            _tick_once()
            time.sleep(interval)
        except Exception:
            log.exception("Demo vitallar tick xato")


def start_demo_vitals_worker() -> None:
    if not getattr(settings, "DEMO_VITALS_ENABLED", False):
        return
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _thread = threading.Thread(
            target=_loop,
            daemon=True,
            name="demo-vitals-worker",
        )
        _thread.start()
