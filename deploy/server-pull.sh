#!/usr/bin/env bash
# VPS: mahalliy commit/stashsiz origin/main bilan to'liq tenglash (pull merge xatosini oldini oladi).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
git fetch origin
git checkout main
git reset --hard origin/main
echo "OK: $(git rev-parse --short HEAD) <= origin/main"
