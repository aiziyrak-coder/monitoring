"""
Django + Socket.IO (ASGI / uvicorn). WebSocket uchun Waitress o‘rniga shu server.

Ishlatish: python run_dev.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    print(
        f"ClinicMonitoring backend (uvicorn ASGI): http://127.0.0.1:{port} "
        f"(REST /api, Socket.IO /socket.io, WebSocket)"
    )
    uvicorn.run(
        "config.asgi:application",
        host=host,
        port=port,
        workers=1,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
