#!/bin/sh
# DCtuneRstudio — Raspberry Pi OS 32/64 bits, ECU real.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. /etc/default/dctuner-raspberry 2>/dev/null || true
export DCTUNER_PORT=${DCTUNER_PORT:-/dev/ttyUSB0}
export DCTUNER_BAUD=${DCTUNER_BAUD:-115200}
export DCTUNER_PROFILE=${DCTUNER_PROFILE:-speeduino}
export DCTUNER_WEB_PORT=${DCTUNER_WEB_PORT:-8080}
export DCTUNER_HOST=${DCTUNER_HOST:-0.0.0.0}
cd "$ROOT/dctuner_web"
exec python3 servidor.py --host "$DCTUNER_HOST" --port "$DCTUNER_WEB_PORT" --serie

