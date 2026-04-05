"""1 Gs telemetriya simulyatsiyasi va vitals_update translatsiyasi."""
from __future__ import annotations

import random
import time
from typing import Any

from django.db import close_old_connections, transaction

from monitoring.asgi_support import schedule_coro
from monitoring.io_bus import sio
from monitoring.models import Patient, VitalHistory
from monitoring.services.news2 import (
    DEFAULT_ALARM_LIMITS,
    calculate_news2,
    vitals_from_patient_row,
)
from monitoring.services.patient_payload import patient_to_wire_dict

_tick_counter = 0


def _apply_limit_alarms(p: Patient, v: dict, limits: dict) -> None:
    if p.alarm_level in (Patient.ALARM_RED, Patient.ALARM_BLUE):
        return
    l = limits
    msgs: list[str] = []
    if v["hr"] < l["hr"]["low"]:
        msgs.append("Past HR")
    if v["hr"] > l["hr"]["high"]:
        msgs.append("Yuqori HR")
    if v["spo2"] < l["spo2"]["low"]:
        msgs.append("Past SpO2")
    if v["spo2"] > l["spo2"]["high"]:
        msgs.append("Yuqori SpO2")
    if v["nibpSys"] > l["nibpSys"]["high"] or v["nibpDia"] > l["nibpDia"]["high"]:
        msgs.append("Yuqori Qon Bosimi")
    if v["nibpSys"] < l["nibpSys"]["low"] or v["nibpDia"] < l["nibpDia"]["low"]:
        msgs.append("Past Qon Bosimi")
    if v["rr"] < l["rr"]["low"] or v["rr"] > l["rr"]["high"]:
        msgs.append("Nafas chastotasi chegaradan tashqari")
    if v["temp"] < l["temp"]["low"] or v["temp"] > l["temp"]["high"]:
        msgs.append("Harorat chegaradan tashqari")

    if msgs:
        p.alarm_level = Patient.ALARM_YELLOW
        p.alarm_message = ", ".join(msgs)
    elif p.alarm_level == Patient.ALARM_YELLOW:
        p.alarm_level = Patient.ALARM_NONE
        p.alarm_message = ""


def _scheduled_check(p: Patient, v: dict, now_ms: int) -> None:
    sc = p.scheduled_check
    if not sc or not isinstance(sc, dict):
        return
    next_t = sc.get("nextCheckTime")
    interval = sc.get("intervalMs", 0)
    if next_t is None or now_ms < int(next_t):
        return

    hr, spo2 = v["hr"], v["spo2"]
    nibp_sys, nibp_dia = v["nibpSys"], v["nibpDia"]
    rr, temp = v["rr"], v["temp"]
    deviated = (
        hr < 60
        or hr > 100
        or spo2 < 95
        or nibp_sys < 90
        or nibp_sys > 140
        or nibp_dia < 60
        or nibp_dia > 90
        or rr < 12
        or rr > 20
        or temp < 36.0
        or temp > 37.5
    )
    if deviated:
        p.alarm_level = Patient.ALARM_PURPLE
        p.alarm_message = "Rejali tekshiruv: Og'ish"

    sc["nextCheckTime"] = now_ms + int(interval)
    p.scheduled_check = sc


def _build_update_payload(wire: dict, *, with_history: bool) -> dict[str, Any]:
    base = {
        "id": wire["id"],
        "vitals": wire["vitals"],
        "alarm": wire["alarm"],
        "alarmLimits": wire["alarmLimits"],
        "scheduledCheck": wire.get("scheduledCheck"),
        "deviceBattery": wire["deviceBattery"],
        "news2Score": wire["news2Score"],
        "isPinned": wire["isPinned"],
        "medications": wire["medications"],
        "labs": wire["labs"],
        "notes": wire["notes"],
    }
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

    updates: list[dict[str, Any]] = []

    with transaction.atomic():
        for pid in patient_ids:
            p = Patient.objects.select_for_update().get(pk=pid)
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

            _apply_limit_alarms(p, v, limits)
            _scheduled_check(p, v, now_ms)
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
