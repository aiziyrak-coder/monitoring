#!/usr/bin/env python3
"""
Lokal kompyuterdan VPS ga SSH (Paramiko): git pull + migrate + build + systemd + nginx.

HTTPS: sertifikat bu yerda yaratilmaydi — serverda allaqachon sozlangan SSL ishlatiladi.
Boshqa loyihalar: asosan /opt/clinicmonitoring; --skip-nginx-purge bilan faqat konf
nusxalanadi, symlink tozalash o'tkazib yuboriladi.

Muhit o'zgaruvchilari:
  DEPLOY_HOST, DEPLOY_USER (default root), DEPLOY_SSH_KEY, ixtiyoriy DEPLOY_PORT,
  DEPLOY_APP_PATH, DEPLOY_SSH_KEY_PASSPHRASE, DEPLOY_SKIP_NGINX_PURGE=1
  DEPLOY_SSH_PASSWORD — kalit o‘rniga parol (repoga yozmang; faqat vaqtinchalik env).

PowerShell:
  pip install -r deploy/requirements-paramiko.txt
  $env:DEPLOY_HOST="167.71.53.238"; $env:DEPLOY_SSH_KEY="$env:USERPROFILE\\.ssh\\id_ed25519"
  python deploy/paramiko_deploy.py

Parol bilan:
  $env:DEPLOY_SSH_PASSWORD="..."; python deploy/paramiko_deploy.py --host 167.71.53.238 --user root --skip-nginx-purge
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
import time


def _require(v: str | None, name: str) -> str:
    if not v or not str(v).strip():
        print(f"Xato: {name} kerak (env yoki argument).", file=sys.stderr)
        sys.exit(2)
    return str(v).strip()


def _run_remote(client, remote_script: str) -> int:
    stdin, stdout, stderr = client.exec_command("bash -s", get_pty=True)
    stdin.write(remote_script)
    stdin.flush()
    stdin.channel.shutdown_write()

    out_ch = stdout.channel
    err_ch = stderr.channel
    while True:
        if out_ch.recv_ready():
            chunk = out_ch.recv(4096)
            if chunk:
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
        if err_ch.recv_ready():
            chunk = err_ch.recv(4096)
            if chunk:
                sys.stderr.buffer.write(chunk)
                sys.stderr.buffer.flush()
        if out_ch.exit_status_ready():
            break
        time.sleep(0.05)

    return out_ch.recv_exit_status()


def main() -> None:
    p = argparse.ArgumentParser(description="SSH orqali ClinicMonitoring deploy")
    p.add_argument("--host", default=os.environ.get("DEPLOY_HOST"))
    p.add_argument("--user", default=os.environ.get("DEPLOY_USER", "root"))
    p.add_argument("--key", default=os.environ.get("DEPLOY_SSH_KEY"))
    p.add_argument(
        "--password",
        default=os.environ.get("DEPLOY_SSH_PASSWORD"),
        help="SSH parol (yoki DEPLOY_SSH_PASSWORD); kalit talab qilinmaydi",
    )
    p.add_argument("--port", type=int, default=int(os.environ.get("DEPLOY_PORT", "22")))
    p.add_argument("--app", default=os.environ.get("DEPLOY_APP_PATH", "/opt/clinicmonitoring"))
    p.add_argument(
        "--skip-nginx-purge",
        action="store_true",
        default=os.environ.get("DEPLOY_SKIP_NGINX_PURGE", "").lower()
        in ("1", "true", "yes"),
        help="clinicmonitoring uchun eski nginx symlinklarini tozalamaslik",
    )
    p.add_argument(
        "--strict-host-key",
        action="store_true",
        help="Noma'lum host kalitini rad qilish (known_hosts talab)",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    host = _require(args.host, "DEPLOY_HOST / --host")
    user = args.user
    key_path = (args.key or "").strip()
    password = (args.password or "").strip()
    app = args.app.rstrip("/")

    if not password and not key_path:
        print(
            "Xato: DEPLOY_SSH_KEY / --key yoki DEPLOY_SSH_PASSWORD / --password kerak.",
            file=sys.stderr,
        )
        sys.exit(2)

    purge = "export CLINICMON_SKIP_NGINX_PURGE=1\n" if args.skip_nginx_purge else ""
    remote_script = f"""set -euo pipefail
{purge}cd {app}
if [ ! -f deploy/server-pull-restart.sh ]; then
  echo "Xato: {app}/deploy/server-pull-restart.sh topilmadi" >&2
  exit 1
fi
if [ "$(id -u)" -eq 0 ]; then
  bash deploy/server-pull-restart.sh
else
  sudo bash deploy/server-pull-restart.sh
fi
"""

    if args.dry_run:
        print("--- remote ---")
        print(remote_script)
        return

    try:
        import paramiko
    except ImportError:
        print(
            "Paramiko yo'q: pip install -r deploy/requirements-paramiko.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    client = paramiko.SSHClient()
    if args.strict_host_key:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kw: dict = {
        "hostname": host,
        "port": args.port,
        "username": user,
        "timeout": 45,
        "banner_timeout": 45,
        "auth_timeout": 45,
    }

    if password:
        connect_kw["password"] = password
        print(f"Ulanish: {user}@{host}:{args.port} (parol) …")
    else:
        key_file = os.path.expanduser(key_path)
        if not os.path.isfile(key_file):
            print(f"Xato: kalit fayli yo'q: {key_file}", file=sys.stderr)
            sys.exit(2)
        connect_kw["key_filename"] = key_file
        passphrase = os.environ.get("DEPLOY_SSH_KEY_PASSPHRASE")
        if passphrase is None:
            try:
                passphrase = getpass.getpass("SSH kalit passphrase (bo'sh bo'lishi mumkin): ")
            except EOFError:
                passphrase = ""
        if passphrase:
            connect_kw["passphrase"] = passphrase
        print(f"Ulanish: {user}@{host}:{args.port} (kalit) …")
    try:
        client.connect(**connect_kw)
    except Exception as e:
        print(f"SSH xato: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        code = _run_remote(client, remote_script)
    finally:
        client.close()

    if code != 0:
        print(f"Deploy tugadi: exit {code}", file=sys.stderr)
    sys.exit(code)


if __name__ == "__main__":
    main()
