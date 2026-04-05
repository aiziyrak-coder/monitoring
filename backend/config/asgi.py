"""
Django ASGI + Socket.IO (WebSocket nginx orqali ishlaydi).

Production: uvicorn (run_dev.py). Simulyatsiya threadi emit uchun loop saqlanadi.
"""
import asyncio
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.asgi import get_asgi_application

import socketio

from monitoring.asgi_support import set_event_loop
from monitoring.hl7_mllp_listener import start_hl7_listener_if_enabled
from monitoring.io_bus import sio
from monitoring.socket_events import register_socket_handlers

register_socket_handlers(sio)

django_asgi_app = get_asgi_application()


async def _on_startup():
    set_event_loop(asyncio.get_running_loop())
    start_hl7_listener_if_enabled()


application = socketio.ASGIApp(
    sio,
    django_asgi_app,
    on_startup=_on_startup,
)
