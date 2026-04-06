"""Signal chegaralari yordamchilari (oldingi server bilan mos qoidalar)."""


DEFAULT_ALARM_LIMITS: dict = {
    "hr": {"low": 50, "high": 120},
    "spo2": {"low": 90, "high": 100},
    "nibpSys": {"low": 90, "high": 160},
    "nibpDia": {"low": 50, "high": 100},
    "rr": {"low": 8, "high": 30},
    "temp": {"low": 35.5, "high": 38.5},
}


def merge_alarm_limits(base: dict, patch: dict) -> dict:
    out = {**base}
    for key, val in patch.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **val}
        else:
            out[key] = val
    return out


def vitals_from_patient_row(p) -> dict:
    return {
        "hr": p.hr,
        "spo2": p.spo2,
        "nibpSys": p.nibp_sys,
        "nibpDia": p.nibp_dia,
        "rr": p.rr,
        "temp": float(p.temp),
    }
