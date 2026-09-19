#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ "$(uname -m)" != "x86_64" ]; then
  echo "This build targets Linux x86_64 only; found $(uname -m)." >&2
  exit 1
fi
python3 -m PyInstaller \
  --noconfirm --clean --onefile --windowed \
  --name DC-Tuner-Studio-Linux-x86_64 \
  --add-data "assets:assets" \
  --add-data "docs:docs" \
  --add-data "THIRD_PARTY_NOTICES.md:." \
  --hidden-import serial \
  --hidden-import serial.tools.list_ports \
  dc_tuner_studio.py
printf 'Created %s\n' "$ROOT/dist/DC-Tuner-Studio-Linux-x86_64"
