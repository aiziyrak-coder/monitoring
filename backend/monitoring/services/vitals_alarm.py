"""Chegara va rejali tekshiruv — simulyatsiya va qurilma ingest uchun umumiy."""
from __future__ import annotations

from monitoring.models import Patient


def apply_limit_alarms(p: Patient, v: dict, limits: dict) -> None:
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


def apply_scheduled_check_window(p: Patient, v: dict, now_ms: int) -> None:
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
