#!/usr/bin/env bash
# NET::ERR_CERT_COMMON_NAME_INVALID — sertifikatda clinicmonitoring.ziyrak.org SAN bo'lmasligi.
# Serverda: sudo bash deploy/fix-ssl-both-domains.sh
# (certbot savollariga javob berasiz: email, shartlar)
set -euo pipefail

echo "=== Mavjud sertifikatlar (Certificate Name va yo'llar) ==="
certbot certificates || true

echo ""
echo "=== Certbot: ikkala domen bitta sertifikatda ==="
certbot --nginx \
  -d clinicmonitoring.ziyrak.org \
  -d clinicmonitoringapi.ziyrak.org

echo ""
echo "=== SAN tekshiruv (clinicmonitoring.ziyrak.org bo'lishi kerak) ==="
for dir in /etc/letsencrypt/live/clinicmonitoring.ziyrak.org /etc/letsencrypt/live/clinicmonitoringapi.ziyrak.org; do
  if [[ -f "$dir/fullchain.pem" ]]; then
    echo "--- $dir ---"
    openssl x509 -in "$dir/fullchain.pem" -noout -text | grep -A2 "Subject Alternative Name" || true
  fi
done

nginx -t
systemctl reload nginx
echo "Yakun. https://clinicmonitoring.ziyrak.org ni sinab ko'ring."
