from __future__ import annotations

import ipaddress
import socket
import time

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
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
from monitoring.ingest_stats import snapshot as ingest_snapshot
from monitoring.services.patient_payload import all_patients_wire, patient_to_wire_dict


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


def _device_ingest_token_denied(request: Request) -> Response | None:
    """DEVICE_INGEST_TOKEN o'rnatilgan bo'lsa, REST vital endpointlari himoyalanadi (HL7 tegilmaydi)."""
    expected = getattr(settings, "DEVICE_INGEST_TOKEN", "") or ""
    if not str(expected).strip():
        return None
    want = str(expected).strip()
    hdr = (request.headers.get("X-Device-Ingest-Token") or "").strip()
    if not hdr:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            hdr = auth[7:].strip()
    if hdr != want:
        return Response(
            {"detail": "Device vitals: not authenticated (token)."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return None


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
                "ingest": ingest_snapshot(),
            }
        )


class PatientsListView(APIView):
    def get(self, request):
        return Response(all_patients_wire())


class PatientDetailView(APIView):
    """Bitta bemor (socket o‘tkazib yuborsa — REST bilan sinxron)."""

    def get(self, request, pk: str):
        p = Patient.objects.filter(pk=pk).first()
        if not p:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(patient_to_wire_dict(p))


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
        denied = _device_ingest_token_denied(request)
        if denied is not None:
            return denied
        dev = Device.objects.filter(ip_address=ip).first()
        if not dev:
            return Response(
                {"error": "Device not registered"}, status=status.HTTP_404_NOT_FOUND
            )
        return _ingest_vitals_response(dev, request)


class DeviceVitalsByIdView(APIView):
    """Gateway / agent: HTTPS orqali vitallar — qurilma ID (dev...) bo'yicha."""

    def post(self, request, pk: str):
        denied = _device_ingest_token_denied(request)
        if denied is not None:
            return denied
        dev = get_object_or_404(Device, pk=pk)
        return _ingest_vitals_response(dev, request)


class PatientVitalsIngestView(APIView):
    """
    Hamshira/shifokor qo'lda vitals kiritish uchun endpoint.
    Patient ID bo'yicha ishlaydi — device bog'lanmagan bo'lsa ham.
    POST /api/patients/<pk>/vitals
    Body: { hr, spo2, nibpSys, nibpDia, rr, temp }
    """

    def post(self, request, pk: str):
        import logging
        import time as _time
        from monitoring.services.news2 import DEFAULT_ALARM_LIMITS, vitals_from_patient_row
        from monitoring.services.vitals_alarm import apply_limit_alarms, apply_scheduled_check_window
        from monitoring.services.device_ingest import _append_vitals_history, build_vitals_socket_payload
        from monitoring.services.patient_payload import patient_to_wire_dict
        from monitoring.models import VitalHistory

        log = logging.getLogger(__name__)
        p = get_object_or_404(Patient, pk=pk)
        body = request.data if isinstance(request.data, dict) else {}

        now_ms = int(_time.time() * 1000)
        wrote = False

        for src, dst in (
            ("hr", "hr"), ("spo2", "spo2"),
            ("nibpSys", "nibp_sys"), ("nibpDia", "nibp_dia"),
            ("rr", "rr"), ("temp", "temp"),
        ):
            if src in body and body[src] is not None:
                val = body[src]
                setattr(p, dst, float(val) if dst == "temp" else int(float(val)))
                wrote = True

        if ("nibpSys" in body or "nibpDia" in body) and body.get("nibpSys") is not None:
            p.nibp_time_ms = now_ms

        if not wrote:
            return Response({"success": False, "message": "Hech qanday qiymat kiritilmadi"}, status=400)

        p.last_real_vitals_ms = now_ms
        limits = p.alarm_limits or {**DEFAULT_ALARM_LIMITS}
        if not p.alarm_limits:
            p.alarm_limits = {**DEFAULT_ALARM_LIMITS}

        v = vitals_from_patient_row(p)
        apply_limit_alarms(p, v, limits)
        apply_scheduled_check_window(p, v, now_ms)
        p.save()

        _append_vitals_history(p, now_ms)
        hist_rows = list(VitalHistory.objects.filter(patient=p).order_by("timestamp_ms"))

        # Linked device topish
        dev = Device.objects.filter(bed_id=p.bed_id).first() if p.bed_id else None
        wire = patient_to_wire_dict(p, history_override=hist_rows, omit_history=False, linked_device=dev)
        payload = build_vitals_socket_payload(wire)
        schedule_vitals_emit([payload])

        log.info("PatientVitalsIngest: patient=%s hr=%s spo2=%s (qo'lda kiritildi)", pk, body.get("hr"), body.get("spo2"))
        return Response({"success": True, "message": "Vitals saqlandi"})
