"""
Creative K12 (yoki boshqa HL7 monitor) ni karavatga biriktirish — mock emas, real oqim.

Serverda HL7 ulanishda ko‘rinadigan manzil odatda 192.168... emas, router tashqi IPsi.
Shuning uchun --nat-ip muhim (yoki har bir monitor uchun HL7 MSH-3).

Misol:
  python manage.py link_hl7_monitor_to_bed --bed-name JOY-5 \\
    --local-ip 192.168.88.104 --mac 02:01:08:C1:83:4B \\
    --nat-ip 91.x.y.z --model \"Creative Medical K12\"

Bemor: Tizimda «Bemor qabul» orqali xuddi shu JOY-5 tanlangan bo‘lsin.
"""
from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from monitoring.models import Bed, Device, Patient
from monitoring.services.news2 import DEFAULT_ALARM_LIMITS


class Command(BaseCommand):
    help = "HL7 monitorni karavatga biriktiradi (masalan JOY-5 + Creative K12)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--bed-name",
            default="JOY-5",
            help="Karavat nomi (qisman mos: icontains), default JOY-5",
        )
        parser.add_argument(
            "--bed-id",
            default="",
            help="Agar aniq ID bo‘lsa, nom o‘rniga",
        )
        parser.add_argument(
            "--local-ip",
            default="192.168.88.104",
            help="Monitorning lokal IP (tizimda unique, REST/LAN)",
        )
        parser.add_argument(
            "--mac",
            default="02:01:08:C1:83:4B",
            help="MAC manzil",
        )
        parser.add_argument(
            "--model",
            default="Creative Medical K12",
            help="Monitor modeli",
        )
        parser.add_argument(
            "--nat-ip",
            default="",
            help="HL7 TCP da server ko‘radigan peer (klinika tashqi IP). Bo‘sh bo‘lsa — logda HL7 peer qidiring.",
        )
        parser.add_argument(
            "--hl7-msh3",
            default="",
            dest="hl7_msh3",
            help="MSH-3 yuboruvchi ID (bir nechta monitor bitta NAT dan bo‘lsa majburiy)",
        )
        parser.add_argument(
            "--ensure-patient",
            action="store_true",
            help="Shu karavatda bemor bo‘lmasa, bitta real bemor yaratadi (oddiy holat)",
        )
        parser.add_argument(
            "--patient-name",
            default="Reanimatsiya bemoriga nom",
            help="--ensure-patient uchun ism",
        )

    def handle(self, *args, **options) -> None:
        bed_id = (options.get("bed_id") or "").strip()
        bed_name = (options.get("bed_name") or "").strip()
        local_ip = (options["local_ip"] or "").strip()
        mac = (options["mac"] or "").strip()
        model = (options["model"] or "").strip()
        nat_ip = (options.get("nat_ip") or "").strip() or (
            os.environ.get("CLINIC_HL7_NAT_IP") or ""
        ).strip()
        hl7_msh3 = (options.get("hl7_msh3") or "").strip()

        if bed_id:
            bed = Bed.objects.filter(pk=bed_id).first()
            if not bed:
                raise CommandError(f"Karavat topilmadi: id={bed_id}")
        else:
            bed = (
                Bed.objects.filter(name__icontains=bed_name).order_by("name").first()
            )
            if not bed:
                raise CommandError(
                    f"«{bed_name}» nomli karavat yo‘q. Tuzilma → reanimatsiya xonasida JOY-5 yarating, "
                    f"yoki --bed-id b… bilan qayta urinib ko‘ring."
                )

        dept = bed.room.department.name
        room_name = bed.room.name
        room_line = f"{dept} - {room_name} - {bed.name}"

        existing = Device.objects.filter(ip_address=local_ip).first()
        if existing:
            dev = existing
            self.stdout.write(self.style.WARNING(f"Mavjud qurilma yangilanadi: {dev.pk}"))
        else:
            dev = Device(ip_address=local_ip, mac_address=mac, model=model)

        dev.mac_address = mac
        dev.model = model
        dev.bed = bed
        dev.hl7_sending_application = hl7_msh3
        if nat_ip:
            dev.hl7_nat_source_ip = nat_ip
        elif not hl7_msh3:
            self.stdout.write(
                self.style.WARNING(
                    "NAT tashqi IP kiritilmagan va HL7 MSH-3 ham bo‘sh — bulutdan HL7 kelganda "
                    "qurilma topilmasligi mumkin. VPS: journalctl -u clinicmonitoring-backend -n 50 | grep HL7\n"
                    "Yoki --nat-ip va/yoki --hl7-msh3 bilan qayta ishga tushiring."
                )
            )

        dev.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Qurilma saqlandi: id={dev.pk}, IP={dev.ip_address}, karavat={bed.name} ({bed.pk}), "
                f"xona={room_line}"
            )
        )

        if options.get("ensure_patient"):
            if Patient.objects.filter(bed=bed).exists():
                self.stdout.write("Karavatda allaqachon bemor bor — yangi yaratilmadi.")
            else:
                p = Patient(
                    name=options["patient_name"],
                    room=room_line,
                    bed=bed,
                    admission_date=timezone.now(),
                    diagnosis="HL7 (Creative K12) kuzatuv",
                    alarm_limits={**DEFAULT_ALARM_LIMITS},
                )
                p.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Real bemor yaratildi: id={p.id}, ism={p.name} — kartada HL7 kelganda vitallar ko‘rinadi."
                    )
                )

        self.stdout.write(
            "\nEslatma: monitorda SpO2/ECG sensorlari ulangan bo‘lsin; «датчик не подключен» bo‘lsa serverga raqam kelmaydi.\n"
            "8 ta demo bemor (demo-p-01…08) alohida; ularga faqat DEMO_VITALS_ENABLED ta’sir qiladi.\n"
        )
