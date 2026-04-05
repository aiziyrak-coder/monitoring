"""Qurilma onlayn holatini last_seen bo'yicha sinxronlash."""
from __future__ import annotations

import time

from django.conf import settings
from django.db import close_old_connections
from django.db.models import Q

from monitoring.models import Device


def mark_stale_devices_offline() -> int:
    """
    last_seen DEVICE_ONLINE_SILENCE_SEC dan eski bo'lgan qurilmalarni offline qiladi.
    Qaytaradi: yangilangan qatorlar soni.
    """
    close_old_connections()
    threshold_ms = int(time.time() * 1000) - settings.DEVICE_ONLINE_SILENCE_SEC * 1000
    n = Device.objects.filter(status="online").filter(
        Q(last_seen_ms__isnull=True) | Q(last_seen_ms__lt=threshold_ms)
    ).update(status="offline")
    return n
