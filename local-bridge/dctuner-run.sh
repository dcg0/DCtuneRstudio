#!/bin/sh
# Lanzador usado por systemd. No requiere una pantalla física.
set -eu

. /etc/default/dctuner 2>/dev/null || true
DCTUNER_SERIE=1
DCTUNER_PROFILE=${DCTUNER_PROFILE:-megasquirt}
DCTUNER_PORT=${DCTUNER_PORT:-/dev/ttyUSB0}
DCTUNER_BAUD=${DCTUNER_BAUD:-115200}
DCTUNER_WEB_PORT=${DCTUNER_WEB_PORT:-8080}
DCTUNER_VNC_PORT=${DCTUNER_VNC_PORT:-6080}
export DCTUNER_PROFILE DCTUNER_PORT DCTUNER_BAUD DCTUNER_WEB_PORT DCTUNER_HOST=0.0.0.0

mkdir -p /run/dctuner

# Xvfb/Openbox son opcionales para el panel nativo, pero permiten acceder al
# escritorio remoto por noVNC en equipos sin pantalla.
if command -v Xvfb >/dev/null 2>&1; then
  Xvfb :1 -screen 0 1024x768x24 -nolisten tcp -ac >/run/dctuner/Xvfb.log 2>&1 &
  XVFB_PID=$!
  trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT INT TERM
  export DISPLAY=:1
  if command -v openbox >/dev/null 2>&1; then
    openbox >/run/dctuner/openbox.log 2>&1 &
  fi
  if command -v x11vnc >/dev/null 2>&1; then
    x11vnc -display :1 -localhost -forever -shared -nopw -rfbport 5901 >/run/dctuner/x11vnc.log 2>&1 &
  fi
  if command -v websockify >/dev/null 2>&1 && [ -d /usr/share/novnc ]; then
    websockify --web=/usr/share/novnc "$DCTUNER_VNC_PORT" localhost:5901 >/run/dctuner/websockify.log 2>&1 &
  elif command -v novnc_proxy >/dev/null 2>&1; then
    novnc_proxy --listen "$DCTUNER_VNC_PORT" --vnc localhost:5901 >/run/dctuner/novnc.log 2>&1 &
  else
    echo "AVISO: noVNC/websockify no está disponible; el panel nativo seguirá en $DCTUNER_WEB_PORT" >&2
  fi
fi

cd /opt/dctuner/dctuner_web
exec python3 servidor.py --host 0.0.0.0 --port "$DCTUNER_WEB_PORT" --serie
