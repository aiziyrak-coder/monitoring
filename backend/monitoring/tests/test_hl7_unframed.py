"""MLLP ramkasiz HL7 (FS+CR yoki ulanish yopilganda bufer)."""
from __future__ import annotations

from django.test import TestCase
from django.utils import timezone

from monitoring.hl7_mllp_listener import (
    _flush_hl7_buffer_on_close,
    _process_one_message,
    _try_consume_segment_only_oru,
    _try_consume_unframed_hl7,
)
from monitoring.models import Bed, Department, Device, Patient, Room
from monitoring.services.hl7_obx import obx_to_vitals_dict


class UnframedHl7Tests(TestCase):
    def setUp(self) -> None:
        dept = Department.objects.create(name="T")
        room = Room.objects.create(name="R1", department=dept)
        self.bed = Bed.objects.create(name="K1", room=room)
        self.dev = Device.objects.create(
            ip_address="203.0.113.50",
            mac_address="00:11:22:33:44:55",
            model="TestMon",
            bed=self.bed,
        )
        self.patient = Patient.objects.create(
            name="HL7Test",
            room="R1",
            bed=self.bed,
            admission_date=timezone.now(),
        )

    def _oru_fs_cr(self) -> str:
        return (
            "MSH|^~\\&|SEND|REC|202401011200||ORU^R01|1|P|2.3\r"
            "PID|1||\r"
            "OBX|1|NM|150022^MDC_ECG_HEART_RATE^MDC||88|||F\r"
            "\x1c\r"
        )

    def test_process_one_message_unframed_body_writes_hr(self) -> None:
        msg = self._oru_fs_cr()
        _process_one_message(msg, "203.0.113.50")
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.hr, 88)
        self.assertIsNotNone(self.patient.last_real_vitals_ms)

    def test_try_consume_unframed_hl7_from_bytearray(self) -> None:
        raw = self._oru_fs_cr().encode("utf-8")
        buf = bytearray(raw)
        did = _try_consume_unframed_hl7(buf, "203.0.113.50")
        self.assertTrue(did)
        self.assertEqual(len(buf), 0)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.hr, 88)

    def test_flush_on_close_without_fs(self) -> None:
        """Bitta yuborish, MSH bor, FS yo'q — yopilishda butun matn."""
        msg = (
            "MSH|^~\\&|SEND|REC|202401011200||ORU^R01|1|P|2.3\r"
            "OBX|1|NM|150022^MDC_ECG_HEART_RATE^MDC||91|||F\r"
        )
        buf = bytearray(msg.encode("utf-8"))
        _flush_hl7_buffer_on_close(buf, "203.0.113.50")
        self.assertEqual(len(buf), 0)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.hr, 91)

    def test_segment_only_oru_crlf_no_fs(self) -> None:
        """Faqat \\r bilan tugaydigan ORU (ochiq oqim)."""
        msg = (
            "MSH|^~\\&|S|R|2024||ORU^R01|1|P|2.3\r"
            "PID|1||\r"
            "OBX|1|NM|150022^HR^MDC||77|||F\r"
        )
        buf = bytearray(msg.encode("utf-8"))
        self.assertTrue(_try_consume_segment_only_oru(buf, "203.0.113.50"))
        self.assertEqual(len(buf), 0)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.hr, 77)


class K12StyleObxTests(TestCase):
    """Comen/K12: OBX-2 da identifikator, qiymat 4-maydonda (OBX-5)."""

    def test_obx_identifier_in_field2_value_in_field4(self) -> None:
        msg = (
            "MSH|^~\\&|SEND|REC|202401011200||ORU^R01|1|P|2.3\r"
            "OBX|1|150022^MDC_ECG_HEART_RATE^MDC||88|||F\r"
        )
        d = obx_to_vitals_dict(msg)
        self.assertEqual(d.get("hr"), 88)

    def test_obx_spo2_vendor_field2(self) -> None:
        msg = (
            "MSH|^~\\&|SEND|REC|202401011200||ORU^R01|1|P|2.3\r"
            "OBX|1|150021^MDC_PULS_OXIM_SAT_O2^MDC||97|||F\r"
        )
        d = obx_to_vitals_dict(msg)
        self.assertEqual(d.get("spo2"), 97)

    def test_obx_russian_spo2_hint_in_obx3(self) -> None:
        """Creative/K12: OBX-3 da rus nom bo‘lishi mumkin."""
        msg = (
            "MSH|^~\\&|SEND|REC|202401011200||ORU^R01|1|P|2.3\r"
            "OBX|1|NM|99^Пульсоксиметрия SpO2^LOCAL||98|||F\r"
        )
        d = obx_to_vitals_dict(msg)
        self.assertEqual(d.get("spo2"), 98)
