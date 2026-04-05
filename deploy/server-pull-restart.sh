#!/usr/bin/env bash
# Serverda (VPS): origin/main ni tortish + migrate/build/nginx + backend restart + health tekshiruvi.
# Ishlatish: sudo bash deploy/server-pull-restart.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

git fetch origin
git checkout main
git reset --hard origin/main
echo ">>> Kod: $(git rev-parse --short HEAD) (origin/main)"

exec bash "$ROOT/deploy/remote-update.sh"
