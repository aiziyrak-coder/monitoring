#!/usr/bin/env python3
"""
Bir martalik VPS deploy (parol faqat muhit o'zgaruvchisida: CLINIC_DEPLOY_PASSWORD).
Repoga parol yozilmaydi.
"""
from __future__ import annotations

import io
import os
import sys
import textwrap

import paramiko


def _configure_stdio() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() in ("utf-8", "utf8"):
        return
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
    except Exception:
        pass

HOST = os.environ.get("CLINIC_DEPLOY_HOST", "167.71.53.238")
USER = os.environ.get("CLINIC_DEPLOY_USER", "root")
PASSWORD = os.environ.get("CLINIC_DEPLOY_PASSWORD", "")

REMOTE_SCRIPT = textwrap.dedent(
    r"""
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive

    if ! command -v git >/dev/null 2>&1; then
      apt-get update -qq
      apt-get install -y -qq git curl ca-certificates
    fi

    # Node 20.x (Vite 6 uchun)
    if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 18 ] 2>/dev/null; then
      curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
      apt-get install -y -qq nodejs
    fi

    apt-get update -qq
    apt-get install -y -qq nginx python3 python3-venv python3-pip certbot python3-certbot-nginx

    mkdir -p /opt
    if [ ! -d /opt/clinicmonitoring/.git ]; then
      rm -rf /opt/clinicmonitoring
      git clone https://github.com/aiziyrak-coder/Monitoring.git /opt/clinicmonitoring
    fi
    cd /opt/clinicmonitoring
    git remote set-url origin https://github.com/aiziyrak-coder/Monitoring.git
    git fetch origin
    git checkout main
    git reset --hard origin/main

    chmod +x deploy/bootstrap-server.sh deploy/remote-update.sh deploy/purge-nginx-clinicmonitoring-conflicts.sh deploy/server-pull.sh 2>/dev/null || true

    if [ ! -f /etc/clinicmonitoring.env ]; then
      install -m 600 /opt/clinicmonitoring/deploy/clinicmonitoring.env.example /etc/clinicmonitoring.env
      SECRET=$(openssl rand -hex 32)
      sed -i "s|DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=${SECRET}|" /etc/clinicmonitoring.env
    fi

    bash /opt/clinicmonitoring/deploy/bootstrap-server.sh

    bash /opt/clinicmonitoring/deploy/remote-update.sh

    certbot --nginx \
      -d clinicmonitoring.ziyrak.org -d clinicmonitoringapi.ziyrak.org \
      --non-interactive --agree-tos --redirect \
      -m admin@ziyrak.org 2>&1 || echo "certbot: DNS yoki limit — keyinroq qo'lda ishga tushiring"

    echo "=== STATUS ==="
    sleep 2
    systemctl is-active clinicmonitoring-backend || true
    systemctl is-active nginx || true
    curl -sS -o /dev/null -w "loopback api health HTTP %{http_code}\n" http://127.0.0.1:8010/api/health || true
    """
).strip()


def main() -> int:
    _configure_stdio()
    if not PASSWORD:
        print("CLINIC_DEPLOY_PASSWORD muhit o'zgaruvchisi bo'sh.", file=sys.stderr)
        return 2

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            HOST,
            username=USER,
            password=PASSWORD,
            timeout=60,
            allow_agent=False,
            look_for_keys=False,
        )
    except Exception as e:
        print(f"SSH ulanish xato: {e}", file=sys.stderr)
        return 1

    try:
        stdin, stdout, stderr = client.exec_command(
            "bash -s",
            get_pty=False,
            timeout=900,
        )
        stdin.write(REMOTE_SCRIPT + "\n")
        stdin.channel.shutdown_write()
        for line in iter(stdout.readline, ""):
            sys.stdout.write(line)
        for line in iter(stderr.readline, ""):
            sys.stderr.write(line)
        code = stdout.channel.recv_exit_status()
        return code if code is not None else 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
