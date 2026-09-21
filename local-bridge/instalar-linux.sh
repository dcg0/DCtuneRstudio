#!/bin/sh
# DCtuneRstudio — instalador Linux 32/64 bits, solo ECU real.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ARCH=$(getconf LONG_BIT 2>/dev/null || echo desconocida)
MACHINE=$(uname -m)
if [ "$ARCH" != "32" ] && [ "$ARCH" != "64" ]; then
  echo "ERROR: no se pudo detectar una arquitectura Linux 32/64 bits" >&2
  exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: ejecuta como root: sudo sh instalar-linux.sh" >&2
  exit 1
fi
if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: este instalador requiere Debian/Ubuntu con apt-get" >&2
  exit 1
fi

echo "DCtuneRstudio — Linux $ARCH-bit ($MACHINE), ECU real"
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-flask python3-serial
install -d -m 0755 /opt/dctuner-linux/local-bridge
cp -a "$ROOT/dctuner_web" /opt/dctuner-linux/local-bridge/
cp "$ROOT/requirements.txt" /opt/dctuner-linux/local-bridge/
install -m 0755 "$ROOT/arrancar-linux.sh" /opt/dctuner-linux/local-bridge/
install -d -m 0755 /var/lib/dctuner/logs /var/lib/dctuner/maps
cat >/etc/default/dctuner-linux <<'EOF'
DCTUNER_PORT=/dev/ttyUSB0
DCTUNER_BAUD=115200
DCTUNER_PROFILE=megasquirt
DCTUNER_WEB_PORT=8080
DCTUNER_HOST=0.0.0.0
EOF
if getent group dialout >/dev/null 2>&1 && [ -n "${SUDO_USER:-}" ]; then usermod -a -G dialout "$SUDO_USER" || true; fi
cat >/etc/systemd/system/dctuner-linux.service <<'EOF'
[Unit]
Description=DCtuneRstudio Linux — ECU real
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
EnvironmentFile=-/etc/default/dctuner-linux
ExecStart=/opt/dctuner-linux/local-bridge/arrancar-linux.sh
Restart=on-failure
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable dctuner-linux.service
systemctl restart dctuner-linux.service || true
echo "Instalado para Linux $ARCH-bit. Estado: systemctl status dctuner-linux"
echo "Panel: http://127.0.0.1:8080/"
