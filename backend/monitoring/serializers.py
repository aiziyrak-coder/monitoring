import time

from django.conf import settings
from rest_framework import serializers

from monitoring.models import Bed, Department, Device, Room


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name")


class RoomSerializer(serializers.ModelSerializer):
    departmentId = serializers.CharField(source="department_id", read_only=True)

    class Meta:
        model = Room
        fields = ("id", "name", "departmentId")


class BedSerializer(serializers.ModelSerializer):
    roomId = serializers.CharField(source="room_id", read_only=True)

    class Meta:
        model = Bed
        fields = ("id", "name", "roomId")


class DeviceSerializer(serializers.ModelSerializer):
    ipAddress = serializers.CharField(source="ip_address")
    macAddress = serializers.CharField(source="mac_address")
    hl7SendingApplication = serializers.CharField(
        source="hl7_sending_application", read_only=True
    )
    hl7NatSourceIp = serializers.IPAddressField(
        source="hl7_nat_source_ip", allow_null=True, read_only=True
    )
    bedId = serializers.SerializerMethodField()
    lastSeen = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = (
            "id",
            "ipAddress",
            "macAddress",
            "model",
            "hl7SendingApplication",
            "hl7NatSourceIp",
            "bedId",
            "status",
            "lastSeen",
        )

    def get_bedId(self, obj: Device):
        return obj.bed_id if obj.bed_id else None

    def get_lastSeen(self, obj: Device):
        return obj.last_seen_ms

    def get_status(self, obj: Device) -> str:
        if obj.last_seen_ms is None:
            return "offline"
        now_ms = int(time.time() * 1000)
        if now_ms - obj.last_seen_ms > settings.DEVICE_ONLINE_SILENCE_SEC * 1000:
            return "offline"
        return "online"


class DepartmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("name",)


class RoomCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    departmentId = serializers.CharField()


class BedCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    roomId = serializers.CharField()


class DeviceCreateSerializer(serializers.Serializer):
    ipAddress = serializers.CharField()
    macAddress = serializers.CharField()
    model = serializers.CharField()
    bedId = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    hl7SendingApplication = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    hl7NatSourceIp = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=""
    )


class DeviceUpdateSerializer(serializers.Serializer):
    bedId = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    status = serializers.ChoiceField(
        choices=("online", "offline"), required=False
    )
    model = serializers.CharField(required=False, allow_blank=True)
    ipAddress = serializers.CharField(required=False)
    macAddress = serializers.CharField(required=False, allow_blank=True)
    hl7SendingApplication = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    hl7NatSourceIp = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=""
    )
