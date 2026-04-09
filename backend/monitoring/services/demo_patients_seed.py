"""8 ta stabil demo bemorni yaratish (4 reanimatsiya, 4 palata)."""
from __future__ import annotations

import math
import random
import time

from django.utils import timezone

from monitoring.models import Patient, VitalHistory
from monitoring.services.news2 import DEFAULT_ALARM_LIMITS

# Taqdimot: kritik signal yo'q, chegaralar standart
_SPECS: list[dict] = [
    {
        "id": "demo-p-01",
        "name": "A. Qodirova",
        "room": "Reanimatsiya - R1",
        "diagnosis": "Postoperatsion kuzatuv, holat barqaror",
        "doctor": "Dr. Karimov",
        "assigned_nurse": "Hamshira Tursunova",
        "hr": 72,
        "spo2": 98,
        "nibp_sys": 118,
        "nibp_dia": 76,
        "rr": 16,
        "temp": 36.6,
        "battery": 92.0,
    },
    {
        "id": "demo-p-02",
        "name": "B. Toshmatov",
        "room": "Reanimatsiya - R2",
        "diagnosis": "Nafas yetishmovchiligi — yengil, stabil",
        "doctor": "Dr. Nazarov",
        "assigned_nurse": "Hamshira Azimova",
        "hr": 78,
        "spo2": 97,
        "nibp_sys": 122,
        "nibp_dia": 78,
        "rr": 18,
        "temp": 36.7,
        "battery": 88.0,
    },
    {
        "id": "demo-p-03",
        "name": "D. Ahmadova",
        "room": "Reanimatsiya - R3",
        "diagnosis": "DM tip 2, kompensatsiya yaxshi",
        "doctor": "Dr. Saidov",
        "assigned_nurse": "Hamshira Ergasheva",
        "hr": 68,
        "spo2": 99,
        "nibp_sys": 115,
        "nibp_dia": 74,
        "rr": 15,
        "temp": 36.5,
        "battery": 95.0,
    },
    {
        "id": "demo-p-04",
        "name": "M. Umarov",
        "room": "Reanimatsiya - R4",
        "diagnosis": "Yurak urishi ritmi barqaror",
        "doctor": "Dr. Rahimov",
        "assigned_nurse": "Hamshira Hasanova",
        "hr": 82,
        "spo2": 96,
        "nibp_sys": 128,
        "nibp_dia": 82,
        "rr": 17,
        "temp": 36.8,
        "battery": 79.0,
    },
    {
        "id": "demo-p-05",
        "name": "F. Rahimova",
        "room": "Palata - 301",
        "diagnosis": "Yengil bronxit, holat yaxshi",
        "doctor": "Dr. Mirzayeva",
        "assigned_nurse": "Hamshira Olimova",
        "hr": 74,
        "spo2": 98,
        "nibp_sys": 120,
        "nibp_dia": 78,
        "rr": 16,
        "temp": 36.6,
        "battery": 91.0,
    },
    {
        "id": "demo-p-06",
        "name": "G. Saidova",
        "room": "Palata - 302",
        "diagnosis": "Gipertoniya, AD nazorat ostida",
        "doctor": "Dr. Yusupov",
        "assigned_nurse": "Hamshira Karimova",
        "hr": 76,
        "spo2": 97,
        "nibp_sys": 117,
        "nibp_dia": 75,
        "rr": 15,
        "temp": 36.7,
        "battery": 86.0,
    },
    {
        "id": "demo-p-07",
        "name": "H. Norimova",
        "room": "Palata - 303",
        "diagnosis": "Operatsiyadan keyin tiklanish",
        "doctor": "Dr. Tursunov",
        "assigned_nurse": "Hamshira Rustamova",
        "hr": 70,
        "spo2": 99,
        "nibp_sys": 119,
        "nibp_dia": 77,
        "rr": 14,
        "temp": 36.5,
        "battery": 94.0,
    },
    {
        "id": "demo-p-08",
        "name": "J. Melieva",
        "room": "Palata - 304",
        "diagnosis": "Kuzatuv, laboratoriya normada",
        "doctor": "Dr. Polatov",
        "assigned_nurse": "Hamshira Shodieva",
        "hr": 79,
        "spo2": 98,
        "nibp_sys": 121,
        "nibp_dia": 79,
        "rr": 16,
        "temp": 36.6,
        "battery": 83.0,
    },
]

# ~5 daqiqa: 20 nuqta, 15 s qadam — monitor «shovqin» ga yaqin, sinус emas
_HISTORY_SAMPLES = 20
_HISTORY_STEP_MS = 15_000


def _build_realistic_history_rows(spec: dict, now_ms: int) -> list[VitalHistory]:
    """
    Har bemorga barqaror, lekin takrorlanmaydigan tarix: OU uslubidagi YUCh,
    juda sekin SpO2, AQB qiyin-qismat o‘lchov.
    """
    pid = spec["id"]
    rng = random.Random(hash((pid, "vital_hist_v3")))
    base_hr = float(spec["hr"])
    base_spo2 = float(spec["spo2"])
    base_sys = float(spec["nibp_sys"])
    base_dia = float(spec["nibp_dia"])
    base_rr = float(spec["rr"])
    base_temp = float(spec["temp"])

    hr_f = base_hr + rng.uniform(-2.0, 2.0)
    spo2_f = base_spo2 + rng.uniform(-0.45, 0.45)
    rr_f = base_rr + rng.uniform(-0.4, 0.4)
    temp_f = base_temp + rng.uniform(-0.07, 0.07)
    cur_sys, cur_dia = base_sys, base_dia
    nibp_countdown = 0

    rows: list[VitalHistory] = []
    n = _HISTORY_SAMPLES
    for i in range(n):
        ts = now_ms - (n - 1 - i) * _HISTORY_STEP_MS

        # Nafas bilan zaif bog‘liqlik — katta sin emas, faqat mayda tebranish
        micro = 0.28 * math.sin(i * 0.38 + rng.uniform(0, 1.2))
        hr_f += rng.gauss(0, 1.15) + 0.25 * (base_hr - hr_f) + micro * rng.uniform(0.5, 1.0)
        hr_f = max(base_hr - 12.0, min(base_hr + 14.0, hr_f))

        spo2_f += rng.gauss(0, 0.11)
        if rng.random() < 0.14:
            spo2_f -= rng.uniform(0.15, 0.55)
        spo2_f += 0.1 * (base_spo2 - spo2_f)
        spo2_f = max(93.8, min(99.9, spo2_f))

        rr_f += rng.gauss(0, 0.22) + 0.035 * (hr_f - base_hr)
        rr_f = max(base_rr - 2.2, min(base_rr + 2.2, rr_f))

        temp_f += rng.gauss(0, 0.016) + 0.06 * (base_temp - temp_f)
        temp_f = max(base_temp - 0.22, min(base_temp + 0.2, temp_f))

        nibp_countdown -= 1
        if nibp_countdown <= 0:
            cur_sys = float(base_sys + rng.randint(-5, 5))
            cur_dia = float(base_dia + rng.randint(-4, 4))
            if cur_dia >= cur_sys - 15:
                cur_dia = cur_sys - 18 - rng.uniform(0, 6)
            nibp_countdown = rng.randint(5, 11)

        rows.append(
            VitalHistory(
                patient_id=pid,
                timestamp_ms=ts,
                hr=round(hr_f, 1),
                spo2=round(spo2_f, 1),
                nibp_sys=round(cur_sys, 1),
                nibp_dia=round(cur_dia, 1),
                rr=round(rr_f, 1),
                temp=round(temp_f, 2),
            )
        )
    return rows


def seed_demo_patients(*, refresh_history: bool = True) -> int:
    """
    8 ta bemorni yaratadi yoki yangilaydi.
    Qaytaradi: yozilgan/yangilangan bemorlar soni.
    """
    now_ms = int(time.time() * 1000)
    count = 0
    for spec in _SPECS:
        pid = spec["id"]
        defaults = {
            "name": spec["name"],
            "room": spec["room"],
            "diagnosis": spec["diagnosis"],
            "doctor": spec["doctor"],
            "assigned_nurse": spec["assigned_nurse"],
            "device_battery": spec["battery"],
            "admission_date": timezone.now(),
            "hr": spec["hr"],
            "spo2": spec["spo2"],
            "nibp_sys": spec["nibp_sys"],
            "nibp_dia": spec["nibp_dia"],
            "rr": spec["rr"],
            "temp": spec["temp"],
            "nibp_time_ms": now_ms,
            "last_real_vitals_ms": now_ms,
            "alarm_level": Patient.ALARM_NONE,
            "alarm_message": "",
            "alarm_limits": {**DEFAULT_ALARM_LIMITS},
            "scheduled_check": None,
            "is_pinned": False,
            "bed": None,
        }
        Patient.objects.update_or_create(id=pid, defaults=defaults)
        count += 1

        if refresh_history:
            VitalHistory.objects.filter(patient_id=pid).delete()
            rows = _build_realistic_history_rows(spec, now_ms)
            VitalHistory.objects.bulk_create(rows)

    return count
