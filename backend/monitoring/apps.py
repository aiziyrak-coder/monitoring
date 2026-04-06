import logging
import os
import sys

from django.apps import AppConfig
from django.db.backends.signals import connection_created

_log = logging.getLogger(__name__)


def _sqlite_wal_pragma(sender, connection, **kwargs) -> None:
    """HL7 thread + ASGI parallel yozuvlar uchun SQLite WAL (VPS mahalliy disk)."""
    if connection.vendor != "sqlite":
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        _log.warning("SQLite WAL pragma o'rnatilmadi", exc_info=True)


class MonitoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "monitoring"
    verbose_name = "Klinik monitoring"

    def ready(self):
        connection_created.connect(_sqlite_wal_pragma, dispatch_uid="monitoring_sqlite_wal")
        if "migrate" in sys.argv or "makemigrations" in sys.argv:
            return
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return
        from monitoring.hl7_mllp_listener import start_hl7_listener_if_enabled

        start_hl7_listener_if_enabled()
