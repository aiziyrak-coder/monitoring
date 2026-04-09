#!/usr/bin/env bash
# HTTPS / certbot: "Could not automatically find a matching server block" —
# sertifikat LE da bor, lekin certbot nginx konfigni o'zgartira olmagan.
# Yechim: repodagi monitoring nginx konfigini joylash + ssl yo'llar allaqachon to'g'ri.
#
# Serverda: sudo bash deploy/fix-ssl-both-domains.sh
# (APP boshqa bo'lsa: CLINICMON_APP=/yo'l/to/repo)
set -euo pipefail

APP="${CLINICMON_APP:-/opt/clinicmonitoring}"
CONF_SRC="$APP/deploy/nginx/monitoring-active.conf"
CONF_DST="/etc/nginx/sites-available/0-clinicmonitoring-django.conf"
ENABLED="/etc/nginx/sites-enabled/0-clinicmonitoring-django.conf"

echo "=== 1. Let's Encrypt sertifikatlari ==="
certbot certificates 2>/dev/null || true

echo ""
echo "=== 2. SAN (clinicmonitoring.ziyrak.org bo'lishi kerak) ==="
for pem in \
  /etc/letsencrypt/live/clinicmonitoring.ziyrak.org/fullchain.pem \
  /etc/letsencrypt/live/clinicmonitoringapi.ziyrak.org/fullchain.pem; do
  if [[ -f "$pem" ]]; then
    echo "--- $pem ---"
    openssl x509 -in "$pem" -noout -text 2>/dev/null | grep -A2 "Subject Alternative Name" || true
  fi
done

echo ""
echo "=== 3. sites-enabled (clinicmonitoring bloki bo'lishi kerak) ==="
ls -la /etc/nginx/sites-enabled/ 2>/dev/null || true

echo ""
echo "=== 4. Nginx konfigni repodan joylash (certbot topa olmaganda shu zarur) ==="
if [[ ! -f "$CONF_SRC" ]]; then
  echo "XATO: $CONF_SRC topilmadi. git pull qiling yoki CLINICMON_APP ni to'g'rilang." >&2
  exit 1
fi
install -m 644 "$CONF_SRC" "$CONF_DST"
ln -sf "$CONF_DST" "$ENABLED"
echo "OK: $ENABLED -> $CONF_DST"

echo ""
echo "=== 5. Tekshiruv va reload ==="
nginx -t
systemctl reload nginx

echo ""
echo "Tayyor. Brauzerda https://clinicmonitoring.ziyrak.org ni oching."
echo "Eslatma: certbot 'Could not install' xabari — sertifikat fayllari LE da saqlangan bo'lsa,"
echo "nginx to'g'ri konf bilan shu fayllarni o'qiydi; qayta certbot shart emas."
echo "Repodan boshqa joyda bo'lsa (apostrofsiz yo'l):"
echo "  sudo CLINICMON_APP=/opt/boshqa-repo bash /opt/boshqa-repo/deploy/fix-ssl-both-domains.sh"
