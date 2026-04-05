"""HL7 matnidan OBX qatorlari orqali vitallar (Mindray va boshqa ORU^R01)."""
from __future__ import annotations

import re
from typing import Any

_CODE_TO_FIELD: dict[str, str] = {
    "8867-4": "hr",
    "14784217-9": "hr",
    "8884-9": "hr",
    "131328-4": "hr",
    "2708-6": "spo2",
    "2710-2": "spo2",
    "59408-5": "spo2",
    "20564-1": "spo2",
    "8310-5": "temp",
    "9279-1": "rr",
    "8480-6": "nibpSys",
    "8462-4": "nibpDia",
    # Mindray / 99MNDRY va boshqa vendorlar
    "150021": "spo2",
    "150022": "hr",
    "150037": "rr",
    "150039": "temp",
    "150301": "nibpSys",
    "150302": "nibpDia",
    "150303": "nibpSys",
    "150344": "hr",
    "150345": "spo2",
    "150456": "hr",
}

# OID matnida qidirish (uzunroq birinchi — noto‘g‘ri moslash kamayadi)
_OBS_SUBSTRING_FIELD: tuple[tuple[str, str], ...] = (
    ("PULS_OXIM_SAT_O2", "spo2"),
    ("MDC_PULS_OXIM_SAT_O2", "spo2"),
    ("SAT_O2", "spo2"),
    ("SPO2", "spo2"),
    ("OXYGEN_SAT", "spo2"),
    ("MDC_ECG_HEART_RATE", "hr"),
    ("ECG_HEART_RATE", "hr"),
    ("HEART_RATE", "hr"),
    ("MDC_PRESS_CUFF_SYS", "nibpSys"),
    ("MDC_PRESS_CUFF_DIA", "nibpDia"),
    ("PRESS_CUFF_SYS", "nibpSys"),
    ("PRESS_CUFF_DIA", "nibpDia"),
    ("CUFF_SYS", "nibpSys"),
    ("CUFF_DIA", "nibpDia"),
    ("MDC_RESP_RATE", "rr"),
    ("RESP_RATE", "rr"),
    ("RESPIRATORY_RATE", "rr"),
    ("MDC_TEMP", "temp"),
    ("BODY_TEMP", "temp"),
    ("NIBP_SYS", "nibpSys"),
    ("NIBP_DIA", "nibpDia"),
    ("NONINV_BP", "nibp_combined"),
    ("BLOOD_PRESSURE", "nibp_combined"),
)


def _norm_segments(hl7_text: str) -> list[str]:
    return [s.strip() for s in hl7_text.replace("\n", "\r").split("\r") if s.strip()]


def extract_msh_sending_application(hl7_text: str) -> str | None:
    """MSH-3 Sending Application — pipe-splitda indeks 2 (MSH, encoding chars, keyin app)."""
    for line in _norm_segments(hl7_text):
        if line.startswith("MSH|"):
            parts = line.split("|")
            if len(parts) > 2 and parts[2].strip():
                return parts[2].strip()
    return None


def _name_hint(name_upper: str) -> str | None:
    if "HEART" in name_upper and "RATE" in name_upper:
        return "hr"
    if "PULSE" in name_upper or name_upper.startswith("PR"):
        return "hr"
    # Mindray / rus interfeysi
    if "ЧСС" in name_upper or "ПУЛЬС" in name_upper or "ЧП" in name_upper:
        return "hr"
    if (
        "SPO2" in name_upper
        or "SPO₂" in name_upper
        or "OXYGEN" in name_upper
        or "САТУР" in name_upper
        or "НАСЫЩ" in name_upper
    ):
        return "spo2"
    if "RESP" in name_upper or "ЧДД" in name_upper or "ДЫХАН" in name_upper:
        return "rr"
    if "TEMP" in name_upper or "ТЕМПЕР" in name_upper or "HARORAT" in name_upper:
        return "temp"
    if "NIBP" in name_upper or "BLOOD PRESS" in name_upper or "АД" in name_upper or "ДАВЛЕН" in name_upper:
        return "nibp_combined"
    return None


def _observation_blob_upper(parts: list[str]) -> str:
    """OBX-3 butun qatori va barcha komponentlar (qidiruv uchun)."""
    raw = parts[3] if len(parts) > 3 else ""
    return raw.upper()


def _field_from_observation(key_raw: str, name_u: str) -> str | None:
    blob = (key_raw or "").upper()
    if not blob and name_u:
        blob = name_u
    for code, fld in _CODE_TO_FIELD.items():
        if code and code in blob:
            return fld
    for needle, fld in _OBS_SUBSTRING_FIELD:
        if needle in blob:
            return fld
    return _name_hint(name_u) or _name_hint(blob)


def _nibp_observation(blob_u: str) -> bool:
    return any(
        x in blob_u
        for x in (
            "8480-6",
            "8462-4",
            "NIBP",
            "BLOOD PRESS",
            "CUFF_SYS",
            "CUFF_DIA",
            "PRESS_CUFF",
            "NONINV",
            "АД",
            "ДАВЛЕН",
        )
    )


def _obx_value_str(parts: list[str]) -> str:
    """OBX-5; ba'zi yuboruvchilarda bo'sh bo'lsa 6–7 qatorlarni tekshiramiz."""
    if len(parts) > 5 and parts[5].strip():
        return parts[5]
    if len(parts) > 6 and parts[6].strip():
        return parts[6]
    return parts[5] if len(parts) > 5 else ""


def _parse_sn_numeric(value_str: str) -> float | None:
    """SN (structured numeric) yoki ^ bilan ajratilgan birinchi son."""
    for chunk in value_str.split("^"):
        n = _parse_num(chunk)
        if n is not None:
            return n
    return None


def _parse_num(value_str: str) -> float | None:
    s = value_str.strip().split("^")[0].strip()
    if not s or s in (".", "-"):
        return None
    s = re.sub(r"^[<>≤≥]\s*", "", s)
    m = re.match(r"^-?\d+(?:[.,]\d+)?", s.replace(",", "."))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _try_split_nibp(value_str: str) -> tuple[int | None, int | None]:
    s = value_str.split("^")[0].strip()
    if "/" not in s:
        return None, None
    a, b = s.split("/", 1)
    na, nb = _parse_num(a), _parse_num(b)
    return (int(na) if na is not None else None, int(nb) if nb is not None else None)


def obx_to_vitals_dict(hl7_text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in _norm_segments(hl7_text):
        if not line.startswith("OBX|"):
            continue
        parts = line.split("|")
        while len(parts) < 8:
            parts.append("")
        key_raw = parts[3] or ""
        code = key_raw.split("^")[0].strip() if key_raw else ""
        name_u = (key_raw.split("^")[1] if "^" in key_raw else "").upper()
        value_str = _obx_value_str(parts)
        value_type = (parts[2] or "").strip().upper()
        blob_u = _observation_blob_upper(parts)

        if _nibp_observation(blob_u):
            sys_dia = _try_split_nibp(value_str)
            if sys_dia[0] is not None or sys_dia[1] is not None:
                if sys_dia[0] is not None:
                    out["nibpSys"] = sys_dia[0]
                if sys_dia[1] is not None:
                    out["nibpDia"] = sys_dia[1]
                continue

        num: float | None
        if value_type == "SN":
            num = _parse_sn_numeric(value_str)
        else:
            num = _parse_num(value_str)
        if num is None:
            continue

        field = _CODE_TO_FIELD.get(code)
        if not field:
            field = _field_from_observation(key_raw, name_u)
        if field == "nibp_combined":
            sys_dia = _try_split_nibp(value_str)
            if sys_dia[0] is not None:
                out["nibpSys"] = sys_dia[0]
            if sys_dia[1] is not None:
                out["nibpDia"] = sys_dia[1]
            continue
        if not field:
            continue

        if field == "temp":
            out["temp"] = float(num)
        else:
            out[field] = int(num)

    return out
