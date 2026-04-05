#!/usr/bin/env bash
# clinicmonitoring*.ziyrak.org uchun boshqa nginx vhostlari bilan to'qnashuvni bartaraf etadi.
# Faqat sites-enabled dagi symlinklarni olib tashlaydi (sites-available va boshqa saytlar fayllari saqlanadi).
set -euo pipefail

ENABLED=/etc/nginx/sites-enabled
OUR="0-clinicmonitoring-django.conf"

[[ -d "$ENABLED" ]] || exit 0

for n in \
  clinicmonitoring-ziyrak.conf \
  clinicmonitoring-ziyrak \
  monitoring \
  monitoring.conf \
  clinicmonitoring.bak.conf \
  clinicmonitoring.conf \
  clinicmonitoring-ziyrak.bak.conf \
  ; do
  rm -f "$ENABLED/$n"
done

shopt -s nullglob
for f in "$ENABLED"/*clinicmonitoring*; do
  [[ "$(basename "$f")" == "$OUR" ]] && continue
  [[ -L "$f" ]] || continue
  echo "purge-nginx: eski symlink: $f"
  rm -f "$f"
done
shopt -u nullglob

for f in "$ENABLED"/*; do
  [[ -L "$f" ]] || continue
  [[ "$(basename "$f")" == "$OUR" ]] && continue
  tgt=$(readlink -f "$f")
  [[ -f "$tgt" ]] || continue
  if grep -qF 'clinicmonitoring.ziyrak.org' "$tgt" 2>/dev/null \
    || grep -qF 'clinicmonitoringapi.ziyrak.org' "$tgt" 2>/dev/null; then
    echo "purge-nginx: shu domenlar boshqa faylda — symlink o'chirilmoqda: $f"
    rm -f "$f"
  fi
done
