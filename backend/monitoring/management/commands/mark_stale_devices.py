from django.core.management.base import BaseCommand

from monitoring.services.device_stale import mark_stale_devices_offline


class Command(BaseCommand):
    help = "last_seen eskirgan qurilmalarni offline qiladi (cron: har 1-2 daqiqa)."

    def handle(self, *args, **options):
        n = mark_stale_devices_offline()
        self.stdout.write(self.style.SUCCESS(f"Yangilandi: {n} qurilma offline"))
