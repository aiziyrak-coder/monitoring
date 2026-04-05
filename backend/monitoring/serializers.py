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
    bedId = serializers.SerializerMethodField()
    lastSeen = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = (
            "id",
            "ipAddress",
            "macAddress",
            "model",
            "hl7SendingApplication",
            "bedId",
            "status",
            "lastSeen",
        )

    def get_bedId(self, obj: Device):
        return obj.bed_id if obj.bed_id else None

    def get_lastSeen(self, obj: Device):
        return obj.last_seen_ms


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
