"""MLLP ramkasiz HL7 (FS+CR yoki ulanish yopilganda bufer)."""
from __future__ import annotations

from django.test import TestCase
from django.utils import timezone

from monitoring.hl7_mllp_listener import (
    _flush_hl7_buffer_on_close,
    _process_one_message,
    _try_consume_unframed_hl7,
)
from monitoring.models import Bed, Department, Device, Patient, Room


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
