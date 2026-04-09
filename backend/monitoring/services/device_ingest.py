"""Qurilma vitallari (REST JSON / HL7 dan keyin) — DB + socket payload."""
from __future__ import annotations

import logging
import time
from typing import Any

from django.db import close_old_connections

from monitoring.models import Device, Patient, VitalHistory
from monitoring.services.news2 import DEFAULT_ALARM_LIMITS, vitals_from_patient_row
from monitoring.ingest_stats import record_vitals_written_to_patient
from monitoring.services.patient_payload import patient_to_wire_dict
from monitoring.services.vitals_alarm import apply_limit_alarms, apply_scheduled_check_window

log = logging.getLogger(__name__)

_HISTORY_INTERVAL_MS = 5000
_HISTORY_MAX_ROWS = 60


def _append_vitals_history(p: Patient, now_ms: int) -> None:
    last_ts = (
        VitalHistory.objects.filter(patient=p)
        .order_by("-timestamp_ms")
        .values_list("timestamp_ms", flat=True)
        .first()
    )
    if last_ts is not None and (now_ms - last_ts) < _HISTORY_INTERVAL_MS:
        return
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
    if len(keep) > _HISTORY_MAX_ROWS:
        VitalHistory.objects.filter(pk__in=keep[_HISTORY_MAX_ROWS:]).delete()


def build_vitals_socket_payload(wire: dict) -> dict[str, Any]:
    out = {
        "id": wire["id"],
        "vitals": wire["vitals"],
        "alarm": wire["alarm"],
        "alarmLimits": wire["alarmLimits"],
        "scheduledCheck": wire.get("scheduledCheck"),
        "deviceBattery": wire["deviceBattery"],
        "isPinned": wire["isPinned"],
        "medications": wire["medications"],
        "labs": wire["labs"],
        "notes": wire["notes"],
    }
    if "lastRealVitalsMs" in wire:
        out["lastRealVitalsMs"] = wire["lastRealVitalsMs"]
    if "history" in wire:
        out["history"] = wire["history"]
    for k in (
        "linkedDeviceId",
        "linkedDeviceLastSeenMs",
        "linkedDeviceLastVitalsAppliedMs",
        "bedId",
    ):
        if k in wire:
            out[k] = wire[k]
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

    if not body:
        # Hech vital yo'q — lekin qurilma onlayn.
        # Agar bemor karavatda bo'lsa va vitals bor bo'lsa — last_real_vitals_ms ni yangilaymiz.
        # Bu frontend uchun vitals "fresh" bo'lsin (10 daqiqa oynasi).
        if dev.bed_id:
            p = Patient.objects.filter(bed_id=dev.bed_id).first()
            if p:
                has_any_vital = (
                    (p.hr or 0) > 0
                    or (p.spo2 or 0) > 0
                    or (p.nibp_sys or 0) > 0
                    or (p.rr or 0) > 0
                )
                if has_any_vital:
                    # TCP heartbeat = qurilma ishlayapti = vitals hozirgi holat
                    p.last_real_vitals_ms = now_ms
                    p.save(update_fields=["last_real_vitals_ms"])
                wire = patient_to_wire_dict(p, omit_history=True, linked_device=dev)
                return build_vitals_socket_payload(wire)
        return None

    if not dev.bed_id:
        log.warning(
            "Vitallar yozilmadi: qurilma %s hech qaysi karavatga biriktirilmagan — Tizim sozlamalari → Qurilmalar",
            dev.pk,
        )
        return None

    p = Patient.objects.filter(bed_id=dev.bed_id).first()
    if not p:
        log.warning(
            "Qurilma karavatga biriktirilgan (bed=%s), lekin shu karavatda bemor yo'q — vitallar yozilmaydi",
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
        record_vitals_written_to_patient()
        Device.objects.filter(pk=dev.pk).update(last_vitals_applied_ms=now_ms)
        dev.last_vitals_applied_ms = now_ms

    limits = p.alarm_limits or {**DEFAULT_ALARM_LIMITS}
    if not p.alarm_limits:
        p.alarm_limits = {**DEFAULT_ALARM_LIMITS}

    v = vitals_from_patient_row(p)
    apply_limit_alarms(p, v, limits)
    apply_scheduled_check_window(p, v, now_ms)
    p.save()

    if wrote_vital:
        _append_vitals_history(p, now_ms)
        hist_rows = list(
            VitalHistory.objects.filter(patient=p).order_by("timestamp_ms")
        )
        wire = patient_to_wire_dict(
            p, history_override=hist_rows, omit_history=False, linked_device=dev
        )
    else:
        wire = patient_to_wire_dict(p, omit_history=True, linked_device=dev)

    return build_vitals_socket_payload(wire)
