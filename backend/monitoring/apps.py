import os
import sys

from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "monitoring"
    verbose_name = "Klinik monitoring"

    def ready(self):
        if "migrate" in sys.argv or "makemigrations" in sys.argv:
            return
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return
        from monitoring.hl7_mllp_listener import start_hl7_listener_if_enabled

        start_hl7_listener_if_enabled()

        # Production (DEBUG=false): faqat qurilma REST / socket — tasodifiy vitallar yo'q
        from django.conf import settings

        if not settings.DEBUG:
            return
        if os.environ.get("SKIP_SIMULATION") == "1":
            return
        from monitoring.simulation_runner import ensure_simulation_started

        ensure_simulation_started()
