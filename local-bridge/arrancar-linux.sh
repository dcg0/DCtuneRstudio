#!/bin/sh
# DCtuneRstudio — Linux 32/64 bits, conexión ECU real.
set -eu
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. /etc/default/dctuner-linux 2>/dev/null || true
export DCTUNER_PORT=${DCTUNER_PORT:-/dev/ttyUSB0}
export DCTUNER_BAUD=${DCTUNER_BAUD:-115200}
export DCTUNER_PROFILE=${DCTUNER_PROFILE:-megasquirt}
export DCTUNER_WEB_PORT=${DCTUNER_WEB_PORT:-8080}
export DCTUNER_HOST=${DCTUNER_HOST:-0.0.0.0}
cd "$BASE/dctuner_web"
exec python3 servidor.py --host "$DCTUNER_HOST" --port "$DCTUNER_WEB_PORT" --serie
