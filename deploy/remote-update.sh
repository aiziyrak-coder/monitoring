#!/usr/bin/env bash
# Serverda ishlaydi: backend + frontend build, systemd, nginx reload.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

export NODE_ENV=production

if [[ -f /etc/clinicmonitoring.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source /etc/clinicmonitoring.env
  set +a
fi

# --- Backend ---
cd "$APP_DIR/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

# Eski loyiha qoldig‘i (masalan monitoring_department.clinic_id) — SQLite qayta
if [[ -f db.sqlite3 ]] && command -v sqlite3 >/dev/null 2>&1; then
  if sqlite3 db.sqlite3 "PRAGMA table_info(monitoring_department);" 2>/dev/null | grep -q '|clinic_id|'; then
    echo "Eski SQLite sxemasi aniqlandi — db.sqlite3 olib tashlanmoqda"
    rm -f db.sqlite3
  fi
fi

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"
export SKIP_SIMULATION=1
.venv/bin/python manage.py migrate --noinput

if ! .venv/bin/python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from monitoring.models import Patient
import sys
sys.exit(0 if Patient.objects.exists() else 1)
"; then
  .venv/bin/python manage.py seed_demo
fi

# Eski API (boshqa dastur) — port 8000 va nginx yo'nalishi uchun
systemctl stop clinic-monitoring-api 2>/dev/null || true
systemctl disable clinic-monitoring-api 2>/dev/null || true
if command -v docker >/dev/null 2>&1; then
  docker stop clinic-monitoring-api 2>/dev/null || true
fi

if [[ -f /etc/systemd/system/clinicmonitoring-backend.service ]]; then
  systemctl daemon-reload
  systemctl enable clinicmonitoring-backend
  systemctl restart clinicmonitoring-backend
else
  echo "Ogohlantirish: systemd unit yo'q. Serverda bir marta: bash $APP_DIR/deploy/bootstrap-server.sh"
fi

# --- Frontend ---
cd "$APP_DIR/frontend"
if [[ ! -f package-lock.json ]]; then
  echo "package-lock.json yo'q" >&2
  exit 1
fi
npm ci
VITE_API_ORIGIN="${VITE_API_ORIGIN:-https://clinicmonitoringapi.ziyrak.org}" npm run build

install -d /var/www/clinicmonitoring
rm -rf /var/www/clinicmonitoring/*
cp -r dist/. /var/www/clinicmonitoring/
chown -R www-data:www-data /var/www/clinicmonitoring

# Nginx: boshqa dasturlarning shu domenlar uchun vhostlarini olib tashlash
bash "$APP_DIR/deploy/purge-nginx-clinicmonitoring-conflicts.sh"

install -m 644 "$APP_DIR/deploy/nginx/monitoring-active.conf" /etc/nginx/sites-available/0-clinicmonitoring-django.conf
ln -sf /etc/nginx/sites-available/0-clinicmonitoring-django.conf /etc/nginx/sites-enabled/0-clinicmonitoring-django.conf

if systemctl is-active --quiet nginx 2>/dev/null; then
  nginx -t
  systemctl reload nginx
fi

echo "Deploy yakunlandi."
