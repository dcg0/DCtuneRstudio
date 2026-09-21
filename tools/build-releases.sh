#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUT="$ROOT/releases"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$OUT"
for target in linux-i386 linux-amd64 windows-x86 windows-x64 raspberry-armv7 raspberry-arm64; do
  name="DCtuneRstudio-$target"
  dir="$STAGE/$name"
  mkdir -p "$dir"
  cp -a "$ROOT/local-bridge/." "$dir/"
  cp "$ROOT/README.md" "$ROOT/PLATAFORMAS.md" "$dir/"
  tar -C "$STAGE" -czf "$OUT/$name.tar.gz" "$name"
  (cd "$STAGE" && zip -qr "$OUT/$name.zip" "$name")
done
printf 'Paquetes creados en %s:\n' "$OUT"
ls -lh "$OUT"/*-raspberry-*.tar.gz "$OUT"/*-raspberry-*.zip

