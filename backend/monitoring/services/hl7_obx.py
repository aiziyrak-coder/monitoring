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
}


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
    if "ЧСС" in name_upper or "ПУЛЬС" in name_upper:
        return "hr"
    if "SPO2" in name_upper or "OXYGEN" in name_upper or "САТУР" in name_upper:
        return "spo2"
    if "RESP" in name_upper or "ЧДД" in name_upper or "ДЫХАН" in name_upper:
        return "rr"
    if "TEMP" in name_upper or "ТЕМПЕР" in name_upper or "HARORAT" in name_upper:
        return "temp"
    if "NIBP" in name_upper or "BLOOD PRESS" in name_upper or "АД" in name_upper or "ДАВЛЕН" in name_upper:
        return "nibp_combined"
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
        if len(parts) < 6:
            continue
        key_raw = parts[3] or ""
        code = key_raw.split("^")[0].strip() if key_raw else ""
        name_u = (key_raw.split("^")[1] if "^" in key_raw else "").upper()
        value_str = parts[5] if len(parts) > 5 else ""

        sys_dia = _try_split_nibp(value_str)
        if sys_dia[0] is not None or sys_dia[1] is not None:
            if sys_dia[0] is not None:
                out["nibpSys"] = sys_dia[0]
            if sys_dia[1] is not None:
                out["nibpDia"] = sys_dia[1]
            continue

        num = _parse_num(value_str)
        if num is None:
            continue

        field = _CODE_TO_FIELD.get(code)
        if not field and key_raw:
            for loinc, fld in _CODE_TO_FIELD.items():
                if loinc and loinc in key_raw:
                    field = fld
                    break
        if not field:
            field = _name_hint(name_u)
        if field == "nibp_combined":
            continue
        if not field:
            continue

        if field == "temp":
            out["temp"] = float(num)
        else:
            out[field] = int(num)

    return out
