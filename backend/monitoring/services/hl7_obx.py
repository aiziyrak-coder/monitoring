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
    "150275": "hr",
    "150200": "spo2",
    "149530": "spo2",
    "151562": "nibpSys",
    "151563": "nibpDia",
    "151554": "nibpSys",
    "151555": "nibpDia",
}

# OID matnida qidirish (uzunroq birinchi — noto‘g‘ri moslash kamayadi)
_OBS_SUBSTRING_FIELD: tuple[tuple[str, str], ...] = (
    ("ПУЛЬСОКСИМ", "spo2"),
    ("ПУЛЬСОКС", "spo2"),
    ("PULS_OXIM_SAT_O2", "spo2"),
    ("MDC_PULS_OXIM_SAT_O2", "spo2"),
    ("SAT_O2", "spo2"),
    ("SPO2", "spo2"),
    ("OXYGEN_SAT", "spo2"),
    ("MDC_ECG_HEART_RATE", "hr"),
    ("ECG_HEART_RATE", "hr"),
    ("HEART_RATE", "hr"),
    ("HR^", "hr"),
    ("^HR^", "hr"),
    ("MDC_PRESS_CUFF_SYS", "nibpSys"),
    ("MDC_PRESS_CUFF_DIA", "nibpDia"),
    ("PRESSCUFF_SYS", "nibpSys"),
    ("PRESSCUFF_DIA", "nibpDia"),
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

# Standart: OBX|set|TYPE|OBX-3|sub|value...
# Ba'zi yuboruvchilar: OBX|TYPE|OBX-3|value... (set/sub yo'q yoki boshqacha)
_KNOWN_OBX_VALUE_TYPES: frozenset[str] = frozenset(
    {
        "NM",
        "SN",
        "ST",
        "TX",
        "FT",
        "CE",
        "CWE",
        "CF",
        "DT",
        "TM",
        "TS",
        "SI",
        "ED",
        "NA",
        "NUL",
        "RP",
    }
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
    u = name_upper.strip()
    # Qisqa OBX-3 (masalan Mindray: HR, SpO2)
    if u in ("HR", "PR", "PULSE", "PULSERATE"):
        return "hr"
    if u in ("SPO2", "SPO₂", "SPO2%", "SPO2 %", "SAO2", "SAO₂"):
        return "spo2"
    if u in ("RR", "RESP", "RESPRATE", "RESP_RATE"):
        return "rr"
    if u in ("TEMP", "BT", "BODY_TEMP"):
        return "temp"
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
        or "ПУЛЬСОКС" in name_upper
    ):
        return "spo2"
    if "RESP" in name_upper or "ЧДД" in name_upper or "ДЫХАН" in name_upper:
        return "rr"
    if "TEMP" in name_upper or "ТЕМПЕР" in name_upper or "HARORAT" in name_upper:
        return "temp"
    if "NIBP" in name_upper or "BLOOD PRESS" in name_upper or "АД" in name_upper or "ДАВЛЕН" in name_upper:
        return "nibp_combined"
    return None


def _obx3_components(key_raw: str) -> list[str]:
    """OBX-3 komponentlari (birinchi bo'sh bo'lishi mumkin: ^150022^MDC)."""
    if not key_raw:
        return []
    return [p.strip() for p in key_raw.split("^") if p and p.strip()]


def _field_from_observation(key_raw: str, name_u: str) -> str | None:
    """Avvalo aniq kod (har bir komponent), keyin butun qator bo'yicha qidiruv."""
    for comp in _obx3_components(key_raw):
        hit = _CODE_TO_FIELD.get(comp)
        if hit:
            return hit
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


def _obx_value_strings(parts: list[str], value_start: int) -> list[str]:
    """OBX qiymat maydonlari — ketma-ket bo'sh bo'lmagan qatorlar."""
    out: list[str] = []
    for idx in range(value_start, min(len(parts), 18)):
        s = parts[idx].strip()
        if s:
            out.append(s)
    return out


def _obx_value_strings_flexible(parts: list[str], primary_start: int) -> list[str]:
    """K12/Comen: qiymat 4-, 5- yoki 6-maydonda bo'lishi mumkin (OBX-2 siljishi)."""
    for start in (primary_start, 4, 5, 3, 6, 7):
        vs = _obx_value_strings(parts, start)
        if vs:
            return vs
    return []


def _looks_like_obx_identifier(field: str) -> bool:
    s = field.strip()
    if not s:
        return False
    if s.upper() in _KNOWN_OBX_VALUE_TYPES:
        return False
    return "^" in s or any(c.isdigit() for c in s)


def _refine_obx_key_value_start(
    parts: list[str], value_type: str, key_raw: str, value_start: int
) -> tuple[str, str, int]:
    """
    OBX|1|150022^MDC_ECG...||72 — standart parserda kalit OBX-3 (bo'sh), qiymat 5 (yo'q);
    haqiqiy kalit 2-maydonda, qiymat 4-maydonda.
    """
    p2 = (parts[2] if len(parts) > 2 else "").strip()
    p2u = p2.upper()
    key_stripped = (key_raw or "").strip()
    if not key_stripped and _looks_like_obx_identifier(p2):
        return ("NM", p2, 4)
    if key_stripped and value_start == 5 and not _obx_value_strings(parts, 5):
        if _obx_value_strings(parts, 4):
            return (value_type, key_raw, 4)
    return (value_type, key_raw, value_start)


def _obx_layout(parts: list[str]) -> tuple[str, str, int]:
    """
    Qaytaradi: (value_type, obx3_key_raw, value_fields_boshlanadigan_indeks).
    Standart: type=parts[2], key=parts[3], values from 5.
    Siljigan: type=parts[1], key=parts[2], values from 3 (TYPE set o‘rnida).
    """
    while len(parts) < 10:
        parts.append("")
    p2 = (parts[2] if len(parts) > 2 else "").strip().upper()
    p1 = (parts[1] if len(parts) > 1 else "").strip().upper()
    if p2 in _KNOWN_OBX_VALUE_TYPES:
        return (p2, (parts[3] if len(parts) > 3 else ""), 5)
    if p1 in _KNOWN_OBX_VALUE_TYPES:
        return (p1, (parts[2] if len(parts) > 2 else ""), 3)
    # Notanish tur — NM deb qabul qilamiz (OBX-2 bo'sh yoki vendor maxsus)
    return ("NM", (parts[3] if len(parts) > 3 else ""), 5)


def _parse_sn_numeric(value_str: str) -> float | None:
    """SN (structured numeric) yoki ^ / & bilan ajratilgan birinchi son."""
    for chunk in re.split(r"[\^&~]", value_str):
        n = _parse_num(chunk)
        if n is not None:
            return n
    return None


def _hl7_unescape_value(s: str) -> str:
    for seq, sp in (
        ("\\.br\\", " "),
        ("\\T\\", " "),
        ("\\.sp\\", " "),
        ("\\R\\", " "),
    ):
        s = s.replace(seq, sp)
    return s.strip()


def _parse_num(value_str: str) -> float | None:
    s = _hl7_unescape_value(value_str).split("^")[0].split("&")[0].strip()
    if not s or s in (".", "-"):
        return None
    s = re.sub(r"^[<>≤≥+]\s*", "", s)
    s = s.replace(",", ".")
    m = re.match(r"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _first_numeric_from_obx_value(value_str: str, value_type: str) -> float | None:
    """
    OBX-5 ichida ~ takrorlari, CE (72^bpm), yoki bir nechta ^ qatlamlari.
    """
    if not value_str or not value_str.strip():
        return None
    raw = _hl7_unescape_value(value_str)
    if value_type == "SN":
        n = _parse_sn_numeric(raw)
        if n is not None:
            return n
    for rep in raw.split("~"):
        rep = rep.strip()
        if not rep:
            continue
        for chunk in re.split(r"[\^&]", rep):
            chunk = chunk.strip()
            if not chunk:
                continue
            if value_type == "SN":
                n = _parse_sn_numeric(chunk)
            else:
                n = _parse_num(chunk)
            if n is not None:
                return n
    if value_type == "SN":
        return _parse_sn_numeric(raw)
    return _parse_num(raw)


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
        if not line.upper().startswith("OBX|"):
            continue
        parts = line.split("|")
        value_type, key_raw, value_start = _obx_layout(parts)
        while len(parts) < 18:
            parts.append("")
        value_type, key_raw, value_start = _refine_obx_key_value_start(
            parts, value_type, key_raw, value_start
        )
        comps = _obx3_components(key_raw)
        code = comps[0] if comps else (key_raw.split("^")[0].strip() if key_raw else "")
        name_u = (comps[1] if len(comps) > 1 else (key_raw.split("^")[1] if "^" in key_raw else "")).upper()
        value_strings = _obx_value_strings_flexible(parts, value_start)
        blob_u = (key_raw or "").upper()

        if _nibp_observation(blob_u):
            got_slash_nibp = False
            for vs in value_strings:
                sys_dia = _try_split_nibp(vs)
                if sys_dia[0] is not None or sys_dia[1] is not None:
                    if sys_dia[0] is not None:
                        out["nibpSys"] = sys_dia[0]
                    if sys_dia[1] is not None:
                        out["nibpDia"] = sys_dia[1]
                    got_slash_nibp = True
                    break
            if got_slash_nibp:
                continue

        num: float | None = None
        for vs in value_strings:
            num = _first_numeric_from_obx_value(vs, value_type)
            if num is not None:
                break
        if num is None:
            continue

        field = _CODE_TO_FIELD.get(code)
        if not field and len(comps) > 1:
            for c in comps[1:]:
                field = _CODE_TO_FIELD.get(c)
                if field:
                    break
        if not field:
            field = _field_from_observation(key_raw, name_u)
        if field == "nibp_combined":
            for vs in value_strings:
                sys_dia = _try_split_nibp(vs)
                if sys_dia[0] is not None:
                    out["nibpSys"] = sys_dia[0]
                if sys_dia[1] is not None:
                    out["nibpDia"] = sys_dia[1]
                if sys_dia[0] is not None or sys_dia[1] is not None:
                    break
            continue
        if not field:
            continue

        if field == "temp":
            out["temp"] = float(num)
        else:
            out[field] = int(num)

    return out
