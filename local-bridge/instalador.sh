#!/bin/sh
# DCtuneRstudio - instalador offline-friendly para Debian 12 amd64 (64-bit).
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALL_DIR=/opt/dctuner
SERVICE_DIR=/etc/systemd/system
DEFAULTS_FILE=/etc/default/dctuner
NET_DIR=/etc/network/interfaces.d
NET_FILE="$NET_DIR/dctuner"
OFFLINE=${DCTUNER_OFFLINE:-0}
NET_IFACE=${DCTUNER_NET_IFACE:-}

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: ejecuta este instalador como root: sudo sh instalador.sh" >&2
  exit 1
fi

printf '%s\n' "DCtuneRstudio — instalación local para Debian 12 amd64 (64-bit)"
printf '%s\n' "No se enviarán datos fuera de tu red local."

if [ ! -f /etc/debian_version ]; then
  echo "AVISO: no se detectó Debian; el instalador continuará bajo tu responsabilidad."
fi

if command -v dpkg >/dev/null 2>&1 && [ "$(dpkg --print-architecture)" != "amd64" ]; then
  echo "AVISO: arquitectura detectada: $(dpkg --print-architecture). Este instalador está preparado para amd64 (64-bit)."
fi

install_packages() {
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "ERROR: apt-get no está disponible. Instala las dependencias manualmente." >&2
    exit 1
  fi
  if [ "$OFFLINE" = "0" ]; then
    echo "[1/7] Actualizando índices de paquetes..."
    apt-get update
  else
    echo "[1/7] Modo offline: se usarán paquetes ya disponibles en caché."
  fi
  echo "[2/7] Instalando dependencias mínimas..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-flask python3-serial \
    xvfb openbox x11vnc novnc websockify iproute2 ca-certificates
}

install_packages

echo "[3/7] Copiando DCtuneRstudio a $INSTALL_DIR..."
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -a "$SCRIPT_DIR/dctuner_web" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/dctuner-run.sh" "$INSTALL_DIR/"
chmod 0755 "$INSTALL_DIR/dctuner-run.sh" "$INSTALL_DIR/dctuner_web/servidor.py"
mkdir -p /var/lib/dctuner/logs /var/lib/dctuner/maps

cat > "$DEFAULTS_FILE" <<'EOF'
# DCtuneRstudio. Solo ECU real; no existe modo demo.
DCTUNER_SERIE=1
DCTUNER_PROFILE=megasquirt
DCTUNER_PORT=/dev/ttyUSB0
DCTUNER_BAUD=115200
DCTUNER_WEB_PORT=8080
DCTUNER_HOST=0.0.0.0
DCTUNER_VNC_PORT=6080
EOF
chmod 0644 "$DEFAULTS_FILE"

echo "[4/7] Instalando el servicio systemd..."
install -m 0644 "$SCRIPT_DIR/dctuner.service" "$SERVICE_DIR/dctuner.service"

if [ -z "$NET_IFACE" ]; then
  NET_IFACE=$(ip -o link show | awk -F': ' '$2 != "lo" {print $2; exit}' | cut -d@ -f1 || true)
fi
NET_IFACE=${NET_IFACE:-enp1s0}

echo "[5/7] Preparando red fija en interfaz $NET_IFACE..."
mkdir -p "$NET_DIR"
cat > "$NET_FILE" <<EOF
# DCtuneRstudio — conexión directa PC ↔ laptop.
# Edita el nombre de interfaz si tu Debian usa otro dispositivo.
auto $NET_IFACE
iface $NET_IFACE inet static
    address 192.168.50.10
    netmask 255.255.255.0
    # Sin gateway: esta red no necesita internet.
EOF
chmod 0644 "$NET_FILE"

# El servicio serie usa el grupo dialout; no se modifica la sesión actual.
echo "[6/7] Configurando permisos USB y directorios..."
if getent group dialout >/dev/null 2>&1; then
  usermod -a -G dialout "${SUDO_USER:-root}" 2>/dev/null || true
fi
chown -R root:root "$INSTALL_DIR" /var/lib/dctuner
chmod 0755 /var/lib/dctuner /var/lib/dctuner/logs /var/lib/dctuner/maps

systemctl daemon-reload
enable_output=$(systemctl enable dctuner.service 2>&1 || true)
start_output=$(systemctl restart dctuner.service 2>&1 || true)

echo "[7/7] Verificando instalación..."
printf '%s\n' "$enable_output" "$start_output"
if systemctl is-active --quiet dctuner.service; then
  echo "OK: dctuner.service está activo."
else
  echo "AVISO: el servicio no quedó activo. Revisa: sudo journalctl -u dctuner.service -n 80 --no-pager"
fi

cat <<EOF

Instalación terminada.

Panel web nativo: http://192.168.50.10:8080/
Consola noVNC:     http://192.168.50.10:6080/vnc.html
Estado:            sudo systemctl status dctuner.service
Logs:              sudo journalctl -u dctuner.service -f

El arranque exige una ECU real. Para conectar:
  sudo nano /etc/default/dctuner
  Para Speeduino usa DCTUNER_PROFILE=speeduino y 115200 8N1
  Ajusta DCTUNER_PORT y ejecuta: sudo systemctl restart dctuner.service
  Si no hay ECU, el panel mostrará ECU DESCONECTADA y no inventará telemetría.

Si el cable directo no activa la IP al instante, aplica la configuración con:
  sudo ifdown $NET_IFACE 2>/dev/null || true
  sudo ifup $NET_IFACE
EOF
