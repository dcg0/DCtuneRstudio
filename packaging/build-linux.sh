#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/dist/dc-tuner-studio-linux"
rm -rf "$OUT"
mkdir -p "$OUT"
cp "$ROOT/dc_tuner_studio.py" "$OUT/"
cp "$ROOT/protocols.py" "$OUT/"
cp "$ROOT/ini_loader.py" "$OUT/"
cp "$ROOT/platform_support.py" "$OUT/"
cp "$ROOT/README.md" "$OUT/"
cp "$ROOT/THIRD_PARTY_NOTICES.md" "$OUT/"
mkdir -p "$OUT/docs"
cp "$ROOT/docs/TUNERSTUDIO_COMPATIBILITY.md" "$OUT/docs/"
mkdir -p "$OUT/assets"
cp "$ROOT/assets/dc-tuner-logo.gif" "$ROOT/assets/dc-tuner-cover.gif" "$OUT/assets/"
mkdir -p "$OUT/assets/definitions"
cp "$ROOT/assets/definitions/speeduino.ini" "$ROOT/assets/definitions/SPEEDUINO-LICENSE.txt" "$OUT/assets/definitions/"
cat > "$OUT/run-dc-tuner-studio.sh" <<'RUNNER'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec python3 dc_tuner_studio.py
RUNNER
chmod +x "$OUT/run-dc-tuner-studio.sh"
tar -C "$ROOT/dist" -czf "$ROOT/dist/dc-tuner-studio-linux-portable.tar.gz" "dc-tuner-studio-linux"
printf 'Created %s\n' "$ROOT/dist/dc-tuner-studio-linux-portable.tar.gz"
