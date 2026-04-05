#!/usr/bin/env bash
# HL7 MLLP (6006/tcp) — ufw faol bo'lsa qoidani qo'shadi. Bulut firewall alohida tekshiring.
set -euo pipefail

if command -v ufw >/dev/null 2>&1; then
  if ufw status 2>/dev/null | grep -qi "Status: active"; then
    ufw allow 6006/tcp comment 'ClinicMonitoring HL7 MLLP' || true
    echo "ufw: 6006/tcp ruxsat qo'shildi (yoki allaqachon bor)."
    ufw status | head -25
    exit 0
  fi
fi

echo "ufw faol emas — DigitalOcean / cloud firewallda 6006/tcp ni qo'lda oching."
echo "HL7 ulanishi nginx orqali emas; Django jarayoni 0.0.0.0:6006 da tinglaydi."
