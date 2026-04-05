import random
import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import (
    Bed,
    ClinicalNote,
    Department,
    Device,
    LabResult,
    Medication,
    Patient,
    Room,
    VitalHistory,
)
from monitoring.services.news2 import DEFAULT_ALARM_LIMITS, calculate_news2


def _seed_history(p: Patient, now_ms: int) -> None:
    rows = []
    for i in range(60, -1, -1):
        ts = now_ms - i * 5000
        rows.append(
            VitalHistory(
                patient=p,
                timestamp_ms=ts,
                hr=float(p.hr) + random.uniform(-5, 5),
                spo2=float(min(100, max(80, p.spo2 + random.uniform(-2, 2)))),
                nibp_sys=float(p.nibp_sys) + random.uniform(-5, 5),
                nibp_dia=float(p.nibp_dia) + random.uniform(-3, 3),
                rr=float(p.rr) + random.uniform(-2, 2),
                temp=float(p.temp) + random.uniform(-0.2, 0.2),
            )
        )
    VitalHistory.objects.bulk_create(rows)


class Command(BaseCommand):
    help = (
        "SINOV: demo bo'limlar, bemorlar va tarix. Productionda ishlatmang — "
        "clear_monitoring_patients --yes bilan tozalang."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Mavjud ma'lumotlarni o'chirib qayta yaratadi",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "seed_demo — faqat mahalliy sinov. Haqiqiy bemorni qo'lda qabul qiling yoki API orqali kiriting."
            )
        )
        if options["force"]:
            Patient.objects.all().delete()
            Device.objects.all().delete()
            Bed.objects.all().delete()
            Room.objects.all().delete()
            Department.objects.all().delete()

        if Department.objects.filter(pk="d1").exists():
            self.stdout.write(self.style.WARNING("Demo allaqachon mavjud (d1). O'tkazib yuborildi."))
            return

        d1 = Department.objects.create(id="d1", name="Reanimatsiya")
        d2 = Department.objects.create(id="d2", name="Umumiy palatalar")
        r1 = Room.objects.create(id="r1", name="Reanimatsiya-1", department=d1)
        r2 = Room.objects.create(id="r2", name="Reanimatsiya-2", department=d1)
        r3 = Room.objects.create(id="r3", name="Palata-A1", department=d2)
        b1 = Bed.objects.create(id="b1", name="Joy-1", room=r1)
        b2 = Bed.objects.create(id="b2", name="Joy-2", room=r1)
        Bed.objects.create(id="b3", name="Joy-1", room=r2)
        Bed.objects.create(id="b4", name="Joy-1", room=r3)

        Device.objects.create(
            id="dev1",
            ip_address="192.168.1.101",
            mac_address="00:1A:2B:3C:4D:5E",
            model="Mindray uMEC10",
            bed=b1,
            status="online",
            last_seen_ms=int(time.time() * 1000),
        )
        Device.objects.create(
            id="dev2",
            ip_address="192.168.1.102",
            mac_address="00:1A:2B:3C:4D:5F",
            model="Philips IntelliVue",
            bed=b2,
            status="online",
            last_seen_ms=int(time.time() * 1000),
        )

        now = timezone.now()
        now_ms = int(time.time() * 1000)
        day = 86400000

        patients_spec = [
            (
                "p1",
                "A. Karimov",
                "Reanimatsiya-1",
                "O'tkir miokard infarkti",
                "Dr. R. Aliyev",
                "H. Karimova",
                85,
                now - timedelta(days=2),
                72,
                98,
                120,
                80,
                16,
                36.6,
                Patient.ALARM_NONE,
                "",
                True,
                None,
            ),
            (
                "p2",
                "B. Aliyeva",
                "Reanimatsiya-2",
                "Pnevmoniya, nafas yetishmovchiligi",
                "Dr. S. Umarova",
                "G. Tursunova",
                42,
                now - timedelta(days=1),
                110,
                92,
                145,
                90,
                22,
                37.8,
                Patient.ALARM_YELLOW,
                "Taxikardiya, Past SpO2",
                False,
                None,
            ),
            (
                "p3",
                "G. Umarova",
                "Palata-A1",
                "Gipertonik kriz",
                "Dr. M. Qosimov",
                "D. Aliyeva",
                15,
                now - timedelta(days=4),
                65,
                99,
                110,
                70,
                14,
                36.5,
                Patient.ALARM_NONE,
                "",
                False,
                None,
            ),
            (
                "p4",
                "S. Tursunov",
                "Palata-A2",
                "Qandli diabet, ketoatsidoz",
                "Dr. S. Umarova",
                "D. Aliyeva",
                100,
                now - timedelta(days=3),
                85,
                96,
                130,
                85,
                18,
                37.1,
                Patient.ALARM_NONE,
                "",
                False,
                None,
            ),
            (
                "p5",
                "M. Xolmatov",
                "Palata-B2",
                "Surunkali yurak yetishmovchiligi",
                "Dr. M. Qosimov",
                "F. Qosimova",
                75,
                now - timedelta(days=5),
                88,
                94,
                135,
                85,
                20,
                36.9,
                Patient.ALARM_NONE,
                "",
                False,
                "extras_p5",
            ),
            (
                "p6",
                "L. Ibragimova",
                "Reanimatsiya-4",
                "Bosh miya qon aylanishining o'tkir buzilishi",
                "Dr. S. Umarova",
                "G. Tursunova",
                90,
                now - timedelta(hours=8),
                62,
                98,
                160,
                100,
                16,
                37.2,
                Patient.ALARM_YELLOW,
                "Yuqori AQB",
                True,
                None,
            ),
            (
                "p7",
                "O. Murodov",
                "Palata-C1",
                "Oshqozon yarasi qon ketishi",
                "Dr. K. Zokirov",
                "D. Aliyeva",
                30,
                now - timedelta(days=1),
                105,
                97,
                95,
                60,
                20,
                36.4,
                Patient.ALARM_NONE,
                "",
                False,
                "extras_p7",
            ),
            (
                "p8",
                "E. Usmonov",
                "Palata-D1",
                "O'tkir appenditsit (operatsiyadan so'ng)",
                "Dr. K. Zokirov",
                "F. Qosimova",
                55,
                now - timedelta(days=2),
                82,
                98,
                125,
                75,
                16,
                37.5,
                Patient.ALARM_NONE,
                "",
                False,
                None,
            ),
            (
                "p9",
                "Sh. Mahmudova",
                "Palata-D2",
                "Qandli diabet 2-tip",
                "Dr. S. Umarova",
                "G. Tursunova",
                80,
                now - timedelta(days=6),
                74,
                99,
                135,
                85,
                18,
                36.7,
                Patient.ALARM_NONE,
                "",
                False,
                "extras_p9",
            ),
            (
                "p10",
                "F. Ismoilov",
                "Palata-E1",
                "O'tkir xolesistit",
                "Dr. M. Qosimov",
                "D. Aliyeva",
                95,
                now - timedelta(days=1),
                85,
                97,
                130,
                80,
                18,
                38.2,
                Patient.ALARM_YELLOW,
                "Isitma",
                False,
                None,
            ),
        ]

        for spec in patients_spec:
            (
                pid,
                name,
                room,
                diagnosis,
                doctor,
                nurse,
                battery,
                adm,
                hr,
                spo2,
                nsys,
                ndia,
                rr,
                temp,
                alvl,
                amsg,
                pinned,
                extra,
            ) = spec
            p = Patient(
                id=pid,
                name=name,
                room=room,
                diagnosis=diagnosis,
                doctor=doctor,
                assigned_nurse=nurse,
                device_battery=float(battery),
                admission_date=adm,
                hr=hr,
                spo2=spo2,
                nibp_sys=nsys,
                nibp_dia=ndia,
                rr=rr,
                temp=temp,
                nibp_time_ms=now_ms - random.randint(300000, 1800000),
                last_real_vitals_ms=now_ms,
                alarm_level=alvl,
                alarm_message=amsg,
                alarm_limits={**DEFAULT_ALARM_LIMITS},
                scheduled_check={
                    "intervalMs": 60000,
                    "nextCheckTime": now_ms + 60000,
                },
                is_pinned=pinned,
            )
            v = {
                "hr": hr,
                "spo2": spo2,
                "nibpSys": nsys,
                "nibpDia": ndia,
                "rr": rr,
                "temp": temp,
            }
            p.news2_score = calculate_news2(v)
            p.save()
            _seed_history(p, now_ms)

            if extra == "extras_p5":
                Medication.objects.create(
                    patient=p, name="Furosemid", dose="40mg", rate="1 tab/kun"
                )
                LabResult.objects.create(
                    patient=p,
                    name="Kreatinin",
                    value="110",
                    unit="µmol/L",
                    time_ms=now_ms - day,
                    is_abnormal=True,
                )
                ClinicalNote.objects.create(
                    patient=p,
                    text="Bemor holati barqaror, shishlar qaytgan.",
                    author="Dr. M. Qosimov",
                    time_ms=now_ms - 3600000,
                )
            elif extra == "extras_p7":
                Medication.objects.create(
                    patient=p, name="Omeprazol", dose="40mg", rate="v/i tomchilab"
                )
                LabResult.objects.create(
                    patient=p,
                    name="Gemoglobin",
                    value="85",
                    unit="g/L",
                    time_ms=now_ms - 14400000,
                    is_abnormal=True,
                )
                ClinicalNote.objects.create(
                    patient=p,
                    text="Qon ketish to'xtagan, gemodinamika barqaror.",
                    author="Dr. K. Zokirov",
                    time_ms=now_ms - 7200000,
                )
            elif extra == "extras_p9":
                Medication.objects.create(
                    patient=p, name="Insulin", dose="10 TB", rate="teri ostiga"
                )
                LabResult.objects.create(
                    patient=p,
                    name="Glyukoza",
                    value="8.1",
                    unit="mmol/L",
                    time_ms=now_ms - 3600000,
                    is_abnormal=True,
                )
                ClinicalNote.objects.create(
                    patient=p,
                    text="Ertalabki qon shakari biroz baland. Doza korreksiya qilindi.",
                    author="Dr. S. Umarova",
                    time_ms=now_ms - 1800000,
                )

        p1 = Patient.objects.get(pk="p1")
        Medication.objects.create(
            patient=p1, name="Noradrenaline", dose="4mg/50ml", rate="2 ml/soat"
        )
        Medication.objects.create(
            patient=p1, name="Propofol 1%", dose="500mg/50ml", rate="10 ml/soat"
        )
        LabResult.objects.create(
            patient=p1,
            name="Laktat",
            value="2.4",
            unit="mmol/L",
            time_ms=now_ms - 3600000,
            is_abnormal=True,
        )
        LabResult.objects.create(
            patient=p1,
            name="Kaliy (K+)",
            value="4.2",
            unit="mmol/L",
            time_ms=now_ms - 7200000,
            is_abnormal=False,
        )

        p6 = Patient.objects.get(pk="p6")
        Medication.objects.create(
            patient=p6, name="Magniy sulfat", dose="25%", rate="10 ml/soat"
        )
        LabResult.objects.create(
            patient=p6,
            name="Glyukoza",
            value="6.5",
            unit="mmol/L",
            time_ms=now_ms - 7200000,
            is_abnormal=False,
        )

        p8 = Patient.objects.get(pk="p8")
        Medication.objects.create(
            patient=p8, name="Ketonal", dose="2ml", rate="v/m og'riq bo'lganda"
        )
        LabResult.objects.create(
            patient=p8,
            name="Leykotsitlar",
            value="11.2",
            unit="10^9/L",
            time_ms=now_ms - day,
            is_abnormal=True,
        )

        p10 = Patient.objects.get(pk="p10")
        Medication.objects.create(
            patient=p10, name="Paratsetamol", dose="1000mg", rate="v/i tomchilab"
        )
        LabResult.objects.create(
            patient=p10,
            name="Bilirubin",
            value="45",
            unit="µmol/L",
            time_ms=now_ms - 14400000,
            is_abnormal=True,
        )

        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlari yaratildi."))
