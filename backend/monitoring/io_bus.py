"""Socket.IO server — ASGI (uvicorn) uchun AsyncServer."""
import socketio

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
