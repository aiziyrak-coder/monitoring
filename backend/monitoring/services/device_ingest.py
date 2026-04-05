"""Qurilma vitallari (REST JSON / HL7 dan keyin) — DB + socket payload."""
from __future__ import annotations

import logging
import time
from typing import Any

from django.db import close_old_connections

from monitoring.models import Device, Patient
from monitoring.services.news2 import (
    DEFAULT_ALARM_LIMITS,
    calculate_news2,
    vitals_from_patient_row,
)
from monitoring.services.patient_payload import patient_to_wire_dict
from monitoring.services.vitals_alarm import apply_limit_alarms, apply_scheduled_check_window

log = logging.getLogger(__name__)


def build_vitals_socket_payload(wire: dict) -> dict[str, Any]:
    out = {
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
    if "lastRealVitalsMs" in wire:
        out["lastRealVitalsMs"] = wire["lastRealVitalsMs"]
    return out


def apply_device_vitals_dict(dev: Device, body: dict) -> dict[str, Any] | None:
    """
    Qurilma holatini yangilaydi, bog'liq bemorga vitallar yoziladi.
    Qaytadi: socket.io `vitals_update` uchun bitta element yoki None.
    """
    close_old_connections()
    now_ms = int(time.time() * 1000)
    dev.status = "online"
    dev.last_seen_ms = now_ms
    dev.save(update_fields=["status", "last_seen_ms"])

    if not dev.bed_id or not body:
        return None

    p = Patient.objects.filter(bed_id=dev.bed_id).first()
    if not p:
        log.warning(
            "Qurilma joyga biriktirilgan (bed=%s), lekin shu joyda bemor yo'q — vitallar yozilmaydi",
            dev.bed_id,
        )
        return None

    wrote_vital = False
    for src, dst in (
        ("hr", "hr"),
        ("spo2", "spo2"),
        ("nibpSys", "nibp_sys"),
        ("nibpDia", "nibp_dia"),
        ("rr", "rr"),
        ("temp", "temp"),
    ):
        if src in body and body[src] is not None:
            val = body[src]
            if dst == "temp":
                setattr(p, dst, float(val))
            else:
                setattr(p, dst, int(val))
            wrote_vital = True

    if "nibpTime" in body and body["nibpTime"] is not None:
        p.nibp_time_ms = int(body["nibpTime"])
        wrote_vital = True
    elif ("nibpSys" in body or "nibpDia" in body) and body.get("nibpSys") is not None:
        p.nibp_time_ms = now_ms
        wrote_vital = True

    if wrote_vital:
        p.last_real_vitals_ms = now_ms

    limits = p.alarm_limits or {**DEFAULT_ALARM_LIMITS}
    if not p.alarm_limits:
        p.alarm_limits = {**DEFAULT_ALARM_LIMITS}

    v = vitals_from_patient_row(p)
    p.news2_score = calculate_news2(v)
    apply_limit_alarms(p, v, limits)
    apply_scheduled_check_window(p, v, now_ms)
    p.save()

    wire = patient_to_wire_dict(p, omit_history=True)
    return build_vitals_socket_payload(wire)
