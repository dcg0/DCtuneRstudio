# Variantes de plataforma

DCtuneRstudio es una aplicación web local con un puente Python/Flask y pySerial. Por eso la interfaz no necesita una compilación distinta para CPU x86: la diferencia real está en el intérprete Python, el controlador USB/serie y el instalador de cada sistema.

| Variante | Puente | Puerto ECU | Instalación/arranque | Estado |
|---|---|---|---|---|
| Debian/Ubuntu Linux 32-bit | Python 3 x86 + Flask + pySerial | `/dev/ttyUSB0`, `/dev/ttyACM0` | `sudo sh local-bridge/instalar-linux.sh` | Preparada |
| Debian/Ubuntu Linux 64-bit | Python 3 amd64 + Flask + pySerial | `/dev/ttyUSB0`, `/dev/ttyACM0` | `sudo sh local-bridge/instalar-linux.sh` | Preparada |
| Windows 32-bit | Python x86 + Flask + pySerial | `COM1`–`COM99` | `arrancar-windows.bat` | Preparada |
| Windows 64-bit | Python x64 + Flask + pySerial | `COM1`–`COM99` | `arrancar-windows.bat` o `arrancar-windows.ps1` | Preparada |

## Requisitos comunes

La ECU debe estar conectada físicamente y su controlador USB instalado. El sistema no usa simulador: si el puerto no existe o la ECU no responde, el panel muestra **ECU DESCONECTADA** y mantiene las medidas en cero. Se recomienda confirmar el baudrate, la familia de firmware y el archivo `.ini` antes de leer o modificar mapas.

## Linux 32/64 bits

El instalador detecta `getconf LONG_BIT`, instala Python, Flask y pySerial, crea `dctuner-linux.service`, configura el puerto por defecto `/dev/ttyUSB0` y agrega el usuario al grupo `dialout`. Ajusta `/etc/default/dctuner-linux`:

```ini
DCTUNER_PORT=/dev/ttyUSB0
DCTUNER_BAUD=115200
DCTUNER_PROFILE=speeduino
DCTUNER_WEB_PORT=8080
```

Para comprobar el adaptador:

```sh
uname -m
getconf LONG_BIT
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
sudo usermod -aG dialout "$USER"
sudo systemctl restart dctuner-linux
```

## Windows 32/64 bits

Instala Python de la misma arquitectura que Windows, abre PowerShell o CMD en `local-bridge`, instala dependencias y define el COM:

```bat
py -3 -m pip install -r requirements.txt
set DCTUNER_PORT=COM3
set DCTUNER_PROFILE=speeduino
arrancar-windows.bat
```

Para PowerShell:

```powershell
py -3 -m pip install -r .\requirements.txt
$env:DCTUNER_PORT = "COM3"
$env:DCTUNER_PROFILE = "speeduino"
.\arrancar-windows.ps1
```

El panel queda en `http://127.0.0.1:8080/`. Para descubrir el COM, revisa Administrador de dispositivos → Puertos (COM y LPT). Si Python x86 no está instalado en Windows 32-bit, debe instalarse el instalador x86; no sirve copiar un Python x64.

## Protocolos

Speeduino usa el perfil binario primario documentado, normalmente 115200 8N1 y petición `A`. MegaSquirt no se trata como una sola ECU: MS1, MS2, MS3 y MicroSquirt pueden cambiar comandos, offsets, CAN ID, tabla y definición `.ini`. El transporte está preparado para COM/TTY, pero la interpretación completa y cualquier escritura requieren la definición exacta del firmware.

## Qué falta para certificar hardware

La compatibilidad de arquitectura está preparada y probada por código, pero una certificación de telemetría necesita una prueba física en cada combinación: Linux 32-bit, Linux 64-bit, Windows 32-bit y Windows 64-bit, con el adaptador USB real y una ECU Speeduino/MegaSquirt. También hay que confirmar permisos/driver, COM o TTY, baudrate, firmware, trama recibida y lectura de RPM/MAP/AFR/temperatura/voltaje antes de habilitar operaciones de ajuste.


## Raspberry Pi

| Variante | Arquitectura | Arranque | Estado |
|---|---|---|---|
| Raspberry Pi OS 32 bits | ARMv6/ARMv7 | `sudo sh local-bridge/instalar-raspberry.sh` | Preparada |
| Raspberry Pi OS 64 bits | ARM64/aarch64 | `sudo sh local-bridge/instalar-raspberry.sh` | Preparada |

El instalador usa los paquetes de Raspberry Pi OS/Debian, crea el servicio `dctuner-raspberry`, configura `/dev/ttyUSB0` como puerto inicial y selecciona Speeduino como perfil inicial. Cambia `DCTUNER_PORT`, `DCTUNER_BAUD` y `DCTUNER_PROFILE` en `/etc/default/dctuner-raspberry` si tu instalación usa otro puerto o MegaSquirt.

```bash
sudo systemctl status dctuner-raspberry
curl http://127.0.0.1:8080/api/health
```

La variante ARM es un paquete de código Python/Flask y no requiere compilar un ejecutable nativo. La arquitectura depende del Python instalado por Raspberry Pi OS.
