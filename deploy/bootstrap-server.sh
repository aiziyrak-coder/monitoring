#!/usr/bin/env bash
# Bir marta root sifatida serverda ishga tushiring.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

install -m 644 "$ROOT/deploy/systemd/clinicmonitoring-backend.service" /etc/systemd/system/clinicmonitoring-backend.service

# 0-clinic* < 00-* (ASCII: pos2 '-' < '0') — dublikat server_name da birinchi blok
rm -f /etc/nginx/sites-enabled/clinicmonitoring-ziyrak.conf
rm -f /etc/nginx/sites-enabled/monitoring
rm -f /etc/nginx/sites-enabled/00-clinicmonitoring-django.conf
rm -f /etc/nginx/sites-enabled/000-clinicmonitoring-django.conf
install -m 644 "$ROOT/deploy/nginx/monitoring-active.conf" /etc/nginx/sites-available/0-clinicmonitoring-django.conf
ln -sf /etc/nginx/sites-available/0-clinicmonitoring-django.conf /etc/nginx/sites-enabled/0-clinicmonitoring-django.conf

if [[ ! -f /etc/clinicmonitoring.env ]]; then
  install -m 600 "$ROOT/deploy/clinicmonitoring.env.example" /etc/clinicmonitoring.env
  echo ">>> /etc/clinicmonitoring.env yaratildi. DJANGO_SECRET_KEY ni o'zgartiring!"
fi

systemctl daemon-reload
systemctl enable clinicmonitoring-backend
nginx -t
systemctl reload nginx

echo "Bootstrap yakunlandi."
