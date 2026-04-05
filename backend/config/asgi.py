"""
Django ASGI + Socket.IO (WebSocket nginx orqali ishlaydi).

Waitress WSGI WebSocket qo‘llab-quvvatlamaydi — production: uvicorn (run_dev.py).
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.asgi import get_asgi_application

import socketio

from monitoring.io_bus import sio
from monitoring.socket_events import register_socket_handlers

register_socket_handlers(sio)

django_asgi_app = get_asgi_application()

application = socketio.ASGIApp(sio, django_asgi_app)
