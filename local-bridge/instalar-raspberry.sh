#!/bin/sh
# DCtuneRstudio — Raspberry Pi OS 32/64 bits, ECU real.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACHINE=$(uname -m)
case "$MACHINE" in
  armv6l|armv7l|aarch64) : ;;
  *) echo "AVISO: arquitectura detectada: $MACHINE; se continúa bajo responsabilidad del usuario." >&2 ;;
esac
[ "$(id -u)" -eq 0 ] || { echo "ERROR: ejecuta como root: sudo sh instalar-raspberry.sh" >&2; exit 1; }
command -v apt-get >/dev/null 2>&1 || { echo "ERROR: se requiere Raspberry Pi OS/Debian con apt-get" >&2; exit 1; }

DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-flask python3-serial
install -d -m 0755 /opt/dctuner-raspberry/local-bridge
cp -a "$ROOT/dctuner_web" /opt/dctuner-raspberry/local-bridge/
cp "$ROOT/requirements.txt" /opt/dctuner-raspberry/local-bridge/
install -m 0755 "$ROOT/arrancar-raspberry.sh" /opt/dctuner-raspberry/local-bridge/
install -d -m 0755 /var/lib/dctuner/logs /var/lib/dctuner/maps
cat >/etc/default/dctuner-raspberry <<'EOF'
DCTUNER_PORT=/dev/ttyUSB0
DCTUNER_BAUD=115200
DCTUNER_PROFILE=speeduino
DCTUNER_WEB_PORT=8080
DCTUNER_HOST=0.0.0.0
EOF
if getent group dialout >/dev/null 2>&1 && [ -n "${SUDO_USER:-}" ]; then usermod -a -G dialout "$SUDO_USER" || true; fi
cat >/etc/systemd/system/dctuner-raspberry.service <<'EOF'
[Unit]
Description=DCtuneRstudio Raspberry Pi — ECU real
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
EnvironmentFile=-/etc/default/dctuner-raspberry
ExecStart=/opt/dctuner-raspberry/local-bridge/arrancar-raspberry.sh
Restart=on-failure
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable dctuner-raspberry.service
systemctl restart dctuner-raspberry.service || true
echo "Instalado para Raspberry Pi ($MACHINE). Panel: http://127.0.0.1:8080/"
echo "Estado: systemctl status dctuner-raspberry"

