import ipaddress
import socket
import time

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.asgi_support import schedule_vitals_emit
from monitoring.models import Bed, Department, Device, Patient, Room
from monitoring.services.device_ingest import apply_device_vitals_dict
from monitoring.services.device_stale import mark_stale_devices_offline
from monitoring.serializers import (
    BedCreateSerializer,
    BedSerializer,
    DepartmentCreateSerializer,
    DepartmentSerializer,
    DeviceCreateSerializer,
    DeviceSerializer,
    DeviceUpdateSerializer,
    RoomCreateSerializer,
    RoomSerializer,
)
from monitoring.services.patient_payload import all_patients_wire


def _parse_nat_ip(raw) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        ipaddress.ip_address(s)
    except ValueError:
        raise ValueError("NAT tashqi IP noto'g'ri")
    return s


def _local_hl7_tcp_open() -> bool:
    """127.0.0.1:HL7 port — jarayon tinglayaptimi (server ichida tekshiruv)."""
    port = int(settings.HL7_LISTEN_PORT)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


def _ingest_vitals_response(dev: Device, request) -> Response:
    body = request.data if isinstance(request.data, dict) else {}
    payload = apply_device_vitals_dict(dev, body)
    if payload:
        schedule_vitals_emit([payload])
    return Response({"success": True, "message": "Data received"})


class HealthView(APIView):
    def get(self, request):
        hl7_on = bool(settings.HL7_LISTENER_ENABLED)
        return Response(
            {
                "status": "ok",
                "uptime": time.monotonic(),
                "service": "clinic-monitoring-django",
                "hl7": {
                    "enabled": hl7_on,
                    "listenHost": settings.HL7_LISTEN_HOST,
                    "listenPort": settings.HL7_LISTEN_PORT,
                    "localTcpAccepts": _local_hl7_tcp_open() if hl7_on else None,
                },
                "deviceOfflineAfterSec": settings.DEVICE_ONLINE_SILENCE_SEC,
            }
        )


class PatientsListView(APIView):
    def get(self, request):
        return Response(all_patients_wire())


class InfrastructureView(APIView):
    def get(self, request):
        mark_stale_devices_offline()
        return Response(
            {
                "departments": DepartmentSerializer(
                    Department.objects.all(), many=True
                ).data,
                "rooms": RoomSerializer(Room.objects.select_related("department"), many=True).data,
                "beds": BedSerializer(Bed.objects.all(), many=True).data,
                "devices": DeviceSerializer(Device.objects.select_related("bed"), many=True).data,
            }
        )


class DepartmentListCreateView(APIView):
    def post(self, request):
        ser = DepartmentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = Department(name=ser.validated_data["name"])
        d.save()
        return Response(DepartmentSerializer(d).data, status=status.HTTP_201_CREATED)


class DepartmentDetailView(APIView):
    def delete(self, request, pk: str):
        Department.objects.filter(pk=pk).delete()
        return Response({"success": True})


class RoomListCreateView(APIView):
    def post(self, request):
        ser = RoomCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dept = get_object_or_404(Department, pk=ser.validated_data["departmentId"])
        r = Room(name=ser.validated_data["name"], department=dept)
        r.save()
        return Response(RoomSerializer(r).data, status=status.HTTP_201_CREATED)


class RoomDetailView(APIView):
    def delete(self, request, pk: str):
        Room.objects.filter(pk=pk).delete()
        return Response({"success": True})


class BedListCreateView(APIView):
    def post(self, request):
        ser = BedCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        room = get_object_or_404(Room, pk=ser.validated_data["roomId"])
        b = Bed(name=ser.validated_data["name"], room=room)
        b.save()
        return Response(BedSerializer(b).data, status=status.HTTP_201_CREATED)


class BedDetailView(APIView):
    def delete(self, request, pk: str):
        Bed.objects.filter(pk=pk).delete()
        return Response({"success": True})


class DeviceListCreateView(APIView):
    def post(self, request):
        ser = DeviceCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        hl7 = (vd.get("hl7SendingApplication") or "").strip()
        if hl7 and Device.objects.filter(hl7_sending_application=hl7).exists():
            return Response(
                {"detail": "Bu HL7 ID (MSH-3) boshqa qurilmada band"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            nat = _parse_nat_ip(vd.get("hl7NatSourceIp"))
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bed = None
        bid = vd.get("bedId")
        if bid:
            bed = get_object_or_404(Bed, pk=bid)
        dev = Device(
            ip_address=vd["ipAddress"],
            mac_address=vd["macAddress"],
            model=vd["model"],
            bed=bed,
            status="offline",
            hl7_sending_application=hl7,
            hl7_nat_source_ip=nat,
        )
        dev.save()
        return Response(DeviceSerializer(dev).data, status=status.HTTP_201_CREATED)


class DeviceDetailView(APIView):
    def put(self, request, pk: str):
        dev = get_object_or_404(Device, pk=pk)
        ser = DeviceUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if "bedId" in data:
            bid = data["bedId"]
            dev.bed = get_object_or_404(Bed, pk=bid) if bid else None
        if "status" in data:
            dev.status = data["status"]
        if "model" in data:
            dev.model = data["model"]
        if "ipAddress" in data:
            dev.ip_address = data["ipAddress"]
        if "macAddress" in data:
            dev.mac_address = data["macAddress"]
        if "hl7SendingApplication" in data:
            hl7 = (data["hl7SendingApplication"] or "").strip()
            if hl7 and (
                Device.objects.filter(hl7_sending_application=hl7)
                .exclude(pk=dev.pk)
                .exists()
            ):
                return Response(
                    {"detail": "Bu HL7 ID (MSH-3) boshqa qurilmada band"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            dev.hl7_sending_application = hl7
        if "hl7NatSourceIp" in data:
            try:
                dev.hl7_nat_source_ip = _parse_nat_ip(data.get("hl7NatSourceIp"))
            except ValueError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        dev.save()
        return Response(DeviceSerializer(dev).data)

    def delete(self, request, pk: str):
        Device.objects.filter(pk=pk).delete()
        return Response({"success": True})


class DeviceVitalsIngestView(APIView):
    """Qurilma vitallari — ro'yxatdan o'tgan lokal IP bo'yicha."""

    def post(self, request, ip: str):
        dev = Device.objects.filter(ip_address=ip).first()
        if not dev:
            return Response(
                {"error": "Device not registered"}, status=status.HTTP_404_NOT_FOUND
            )
        return _ingest_vitals_response(dev, request)


class DeviceVitalsByIdView(APIView):
    """Gateway / agent: HTTPS orqali vitallar — qurilma ID (dev...) bo'yicha."""

    def post(self, request, pk: str):
        dev = get_object_or_404(Device, pk=pk)
        return _ingest_vitals_response(dev, request)
