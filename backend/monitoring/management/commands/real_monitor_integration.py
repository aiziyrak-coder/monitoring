"""Real HL7 monitor (masalan Creative K12) va yangi bemor kartasi - serverda tekshiruv ro'yxati."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Bulutga HL7 yuboradigan monitor + real bemor kartasi (mock emas) uchun qadamlarni chiqaradi."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                "\n=== Real monitor -> 9-bemor (yoki istalgan) karta - HL7 ===\n"
            )
        )
        txt = r"""
1) Tuzilma: bo'lim, palata, karavat (joy) yarating.

2) Qurilmalar: Yangi qurilma
   - Karavat: aynan shu bemorni yotqizadigan joy.
   - IP: monitorning LOKAL manzili (masalan 192.168.88.104) - REST/LAN uchun.
   - NAT tashqi IP: MUHIM - monitor serveringizga (VPS) TCP ochganda, server
     ko'radigan manzil odatda 192.168... EMAS, balki klinikaning Internet (router)
     tashqi IPsi. Bir xil router orqali bir nechta monitor bo'lsa, har biriga
     HL7 MSH-3 (monitor xabaridagi yuboruvchi ID) ni tizimda kiriting va
     monitorda ham bir xil qiling.

3) Bemorlar: Bemor qabul - xuddi shu karavatni tanlang, ism/shifokor va hokazo.
   Mock demo (demo-p-01...) alohida; real bemorga DEMO_VITALS_ENABLED ta'sir qilmaydi.

4) Monitor menyusi: Server IP = VPS, port 6006, HL7 yoqilgan (Creative K12).

5) Tekshiruv: GET /api/health - ingest (HL7 xabarlar, vitallar ajratilgan, bemorga yozilgan).
   Muammo bo'lsa: journalctl -u clinicmonitoring-backend -n 80 - "OBX bor, lekin vitallar
   ajratilmadi" deganda birinchi OBX qatori logda ko'rinadi.

6) Sensorlar: monitor ekranda sensor ulanmagan deganda, serverga ham qiymat kelmaydi -
   bu normal; ECG/SpO2 sensorlarini ulang.
"""
        self.stdout.write(txt)
