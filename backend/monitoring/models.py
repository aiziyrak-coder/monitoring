import time
import uuid

from django.db import models
from django.utils import timezone


def gen_infra_id(prefix: str) -> str:
    return f"{prefix}{int(time.time() * 1000)}"


class Department(models.Model):
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = gen_infra_id("d")
        super().save(*args, **kwargs)


class Room(models.Model):
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="rooms"
    )

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = gen_infra_id("r")
        super().save(*args, **kwargs)


class Bed(models.Model):
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="beds")

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = gen_infra_id("b")
        super().save(*args, **kwargs)


class Device(models.Model):
    STATUS = (("online", "online"), ("offline", "offline"))

    id = models.CharField(max_length=64, primary_key=True, editable=False)
    ip_address = models.GenericIPAddressField(unique=True)
    mac_address = models.CharField(max_length=32)
    model = models.CharField(max_length=255)
    bed = models.ForeignKey(
        Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices"
    )
    status = models.CharField(max_length=16, choices=STATUS, default="offline")
    last_seen_ms = models.BigIntegerField(null=True, blank=True)
    # HL7 MSH-3 (Sending Application) — bir nechta monitor bitta NAT orqida bo'lsa
    hl7_sending_application = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["model"]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = gen_infra_id("dev")
        super().save(*args, **kwargs)


class Patient(models.Model):
    ALARM_NONE = "none"
    ALARM_BLUE = "blue"
    ALARM_YELLOW = "yellow"
    ALARM_RED = "red"
    ALARM_PURPLE = "purple"
    ALARM_LEVELS = (
        (ALARM_NONE, "none"),
        (ALARM_BLUE, "blue"),
        (ALARM_YELLOW, "yellow"),
        (ALARM_RED, "red"),
        (ALARM_PURPLE, "purple"),
    )

    id = models.CharField(max_length=36, primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    room = models.CharField(max_length=255)
    diagnosis = models.TextField(blank=True, default="")
    doctor = models.CharField(max_length=255, blank=True, default="")
    assigned_nurse = models.CharField(max_length=255, blank=True, default="")
    device_battery = models.FloatField(default=100.0)
    admission_date = models.DateTimeField(default=timezone.now)

    hr = models.PositiveIntegerField(default=75)
    spo2 = models.PositiveIntegerField(default=98)
    nibp_sys = models.PositiveIntegerField(default=120)
    nibp_dia = models.PositiveIntegerField(default=80)
    rr = models.PositiveIntegerField(default=16)
    temp = models.FloatField(default=36.6)
    nibp_time_ms = models.BigIntegerField(null=True, blank=True)

    alarm_level = models.CharField(
        max_length=16, choices=ALARM_LEVELS, default=ALARM_NONE
    )
    alarm_message = models.TextField(blank=True, default="")
    alarm_limits = models.JSONField(default=dict)
    scheduled_check = models.JSONField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)
    news2_score = models.PositiveSmallIntegerField(default=0)

    bed = models.ForeignKey(
        Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name="patients"
    )

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"p{uuid.uuid4().hex[:10]}"
        super().save(*args, **kwargs)


class Medication(models.Model):
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="medications"
    )
    name = models.CharField(max_length=255)
    dose = models.CharField(max_length=255, blank=True, default="")
    rate = models.CharField(max_length=255, blank=True, default="")

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"m{uuid.uuid4().hex[:12]}"
        super().save(*args, **kwargs)


class LabResult(models.Model):
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="labs")
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=64)
    unit = models.CharField(max_length=64, blank=True, default="")
    time_ms = models.BigIntegerField()
    is_abnormal = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"l{uuid.uuid4().hex[:12]}"
        super().save(*args, **kwargs)


class ClinicalNote(models.Model):
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="notes")
    text = models.TextField()
    author = models.CharField(max_length=255)
    time_ms = models.BigIntegerField()

    class Meta:
        ordering = ["-time_ms"]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"n{uuid.uuid4().hex[:12]}"
        super().save(*args, **kwargs)


class VitalHistory(models.Model):
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="history_rows"
    )
    timestamp_ms = models.BigIntegerField(db_index=True)
    hr = models.FloatField()
    spo2 = models.FloatField()
    nibp_sys = models.FloatField()
    nibp_dia = models.FloatField()
    rr = models.FloatField()
    temp = models.FloatField()

    class Meta:
        ordering = ["timestamp_ms"]
        indexes = [
            models.Index(fields=["patient", "timestamp_ms"]),
        ]
