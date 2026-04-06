"""ORM → frontend (socket / REST) JSON."""
from __future__ import annotations

from django.db.models import Prefetch

from monitoring.models import Patient, VitalHistory


def _history_queryset():
    return VitalHistory.objects.order_by("timestamp_ms")


def patients_queryset_for_wire():
    return (
        Patient.objects.all()
        .prefetch_related(
            "medications",
            "labs",
            "notes",
            Prefetch("history_rows", queryset=_history_queryset()),
        )
        .order_by("name")
    )


def patient_to_wire_dict(
    p: Patient,
    *,
    history_override: list | None = None,
    omit_history: bool = False,
) -> dict:
    vitals = {
        "hr": p.hr,
        "spo2": p.spo2,
        "nibpSys": p.nibp_sys,
        "nibpDia": p.nibp_dia,
        "rr": p.rr,
        "temp": float(p.temp),
    }
    if p.nibp_time_ms is not None:
        vitals["nibpTime"] = p.nibp_time_ms

    admission_ms = int(p.admission_date.timestamp() * 1000)

    meds = [
        {
            "id": m.id,
            "name": m.name,
            "dose": m.dose,
            "rate": m.rate or None,
        }
        for m in p.medications.all()
    ]
    labs = [
        {
            "id": lab.id,
            "name": lab.name,
            "value": lab.value,
            "unit": lab.unit,
            "time": lab.time_ms,
            "isAbnormal": lab.is_abnormal,
        }
        for lab in p.labs.all()
    ]
    notes = [
        {
            "id": n.id,
            "text": n.text,
            "author": n.author,
            "time": n.time_ms,
        }
        for n in p.notes.all()
    ]

    if omit_history:
        history: list = []
    elif history_override is not None:
        rows = history_override
        history = [
            {
                "timestamp": h.timestamp_ms,
                "hr": h.hr,
                "spo2": h.spo2,
                "nibpSys": h.nibp_sys,
                "nibpDia": h.nibp_dia,
                "rr": h.rr,
                "temp": h.temp,
            }
            for h in rows
        ]
    else:
        rows = p.history_rows.all()
        history = [
            {
                "timestamp": h.timestamp_ms,
                "hr": h.hr,
                "spo2": h.spo2,
                "nibpSys": h.nibp_sys,
                "nibpDia": h.nibp_dia,
                "rr": h.rr,
                "temp": h.temp,
            }
            for h in rows
        ]

    limits = p.alarm_limits or {}
    if not limits:
        from monitoring.services.news2 import DEFAULT_ALARM_LIMITS

        limits = {**DEFAULT_ALARM_LIMITS}

    if p.alarm_level == Patient.ALARM_NONE:
        alarm = {"level": "none"}
    else:
        alarm = {
            "level": p.alarm_level,
            "message": p.alarm_message or "",
            "patientId": p.id,
        }

    out = {
        "id": p.id,
        "name": p.name,
        "room": p.room,
        "diagnosis": p.diagnosis,
        "doctor": p.doctor,
        "assignedNurse": p.assigned_nurse,
        "deviceBattery": float(p.device_battery),
        "admissionDate": admission_ms,
        "lastRealVitalsMs": p.last_real_vitals_ms,
        "vitals": vitals,
        "alarm": alarm,
        "alarmLimits": limits,
        "scheduledCheck": p.scheduled_check,
        "isPinned": p.is_pinned,
        "medications": meds,
        "labs": labs,
        "notes": notes,
    }
    if not omit_history:
        out["history"] = history
    return out


def all_patients_wire():
    return [patient_to_wire_dict(p) for p in patients_queryset_for_wire()]
