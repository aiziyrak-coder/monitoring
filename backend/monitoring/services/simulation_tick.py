"""1 Gs telemetriya simulyatsiyasi va vitals_update translatsiyasi."""
from __future__ import annotations

import random
import time
from typing import Any

from django.conf import settings
from django.db import close_old_connections, transaction

from monitoring.asgi_support import schedule_coro
from monitoring.io_bus import sio
from monitoring.models import Device, Patient, VitalHistory
from monitoring.services.device_ingest import build_vitals_socket_payload
from monitoring.services.news2 import (
    DEFAULT_ALARM_LIMITS,
    calculate_news2,
    vitals_from_patient_row,
)
from monitoring.services.patient_payload import patient_to_wire_dict
from monitoring.services.vitals_alarm import apply_limit_alarms, apply_scheduled_check_window

_tick_counter = 0


def _seed_demo_patient(p: Patient, now_ms: int) -> None:
    p.hr = random.randint(72, 96)
    p.spo2 = random.randint(94, 99)
    p.nibp_sys = random.randint(108, 138)
    p.nibp_dia = random.randint(68, 90)
    p.rr = random.randint(14, 22)
    p.temp = round(random.uniform(36.4, 37.2), 1)
    p.nibp_time_ms = now_ms
    p.last_real_vitals_ms = now_ms


def _build_update_payload(wire: dict, *, with_history: bool) -> dict[str, Any]:
    base = build_vitals_socket_payload(wire)
    if with_history:
        base["history"] = wire["history"]
    return base


def run_simulation_tick() -> None:
    global _tick_counter
    close_old_connections()
    _tick_counter += 1
    is_history_tick = _tick_counter % 5 == 0
    now_ms = int(time.time() * 1000)

    patient_ids = list(Patient.objects.values_list("pk", flat=True))
    if not patient_ids:
        return

    demo = getattr(settings, "DEMO_LIVE_VITALS", False)
    beds_with_device = frozenset(
        Device.objects.exclude(bed_id__isnull=True).values_list("bed_id", flat=True)
    )

    updates: list[dict[str, Any]] = []

    with transaction.atomic():
        for pid in patient_ids:
            p = Patient.objects.select_for_update().get(pk=pid)
            if not demo and p.bed_id and p.bed_id in beds_with_device:
                continue
            if p.last_real_vitals_ms is None:
                if demo:
                    _seed_demo_patient(p, now_ms)
                else:
                    continue
            limits = p.alarm_limits or DEFAULT_ALARM_LIMITS
            if not p.alarm_limits:
                p.alarm_limits = {**DEFAULT_ALARM_LIMITS}

            if p.alarm_level not in (Patient.ALARM_RED, Patient.ALARM_BLUE):
                if random.random() > 0.8:
                    p.hr = max(40, min(180, p.hr + random.randint(-1, 1)))
                if random.random() > 0.9:
                    p.spo2 = max(85, min(100, p.spo2 + random.randint(-1, 1)))
                if random.random() > 0.8:
                    p.nibp_sys = max(80, min(220, p.nibp_sys + random.randint(-2, 2)))
                if random.random() > 0.8:
                    p.nibp_dia = max(40, min(120, p.nibp_dia + random.randint(-1, 1)))
                if random.random() > 0.9:
                    p.rr = max(8, min(40, p.rr + random.randint(-1, 1)))
                if random.random() > 0.95:
                    p.temp = max(35.0, min(41.0, p.temp + random.uniform(-0.1, 0.1)))

            v = vitals_from_patient_row(p)
            p.news2_score = calculate_news2(v)

            if is_history_tick and p.device_battery > 0:
                p.device_battery = max(0.0, p.device_battery - random.random() * 0.1)

            if is_history_tick and p.alarm_level not in (
                Patient.ALARM_RED,
                Patient.ALARM_BLUE,
            ):
                VitalHistory.objects.create(
                    patient=p,
                    timestamp_ms=now_ms,
                    hr=float(p.hr),
                    spo2=float(p.spo2),
                    nibp_sys=float(p.nibp_sys),
                    nibp_dia=float(p.nibp_dia),
                    rr=float(p.rr),
                    temp=float(p.temp),
                )
                keep = list(
                    VitalHistory.objects.filter(patient=p)
                    .order_by("-timestamp_ms")
                    .values_list("pk", flat=True)
                )
                if len(keep) > 60:
                    VitalHistory.objects.filter(pk__in=keep[60:]).delete()

            apply_limit_alarms(p, v, limits)
            apply_scheduled_check_window(p, v, now_ms)
            p.save()

            if is_history_tick:
                hist = list(
                    VitalHistory.objects.filter(patient=p).order_by("timestamp_ms")
                )
                wire = patient_to_wire_dict(p, history_override=hist)
                updates.append(_build_update_payload(wire, with_history=True))
            else:
                wire = patient_to_wire_dict(p, omit_history=True)
                updates.append(_build_update_payload(wire, with_history=False))

    schedule_coro(sio.emit("vitals_update", updates))
