from django.contrib import admin

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


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "department")


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "room")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "model", "ip_address", "status", "bed")


class VitalHistoryInline(admin.TabularInline):
    model = VitalHistory
    extra = 0


class MedicationInline(admin.TabularInline):
    model = Medication
    extra = 0


class LabInline(admin.TabularInline):
    model = LabResult
    extra = 0


class NoteInline(admin.TabularInline):
    model = ClinicalNote
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "room", "alarm_level")
    inlines = (MedicationInline, LabInline, NoteInline, VitalHistoryInline)
