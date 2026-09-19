# DC TUNER STUDIO

**DC TUNER STUDIO** es una interfaz web local para supervisar una ECU MegaSquirt desde un equipo Debian 12 i386 sin pantalla física. La computadora que tiene conectado el USB ejecuta el backend y la laptop o el celular solamente abre un navegador. No se requiere internet durante la operación.

> **Importante:** la interfaz arranca en modo simulación para que puedas comprobar la red y el panel sin enviar nada al vehículo. Activa el modo serie solamente después de verificar el puerto USB, la velocidad y la instalación eléctrica.

## Arquitectura de acceso

El paquete ofrece dos formas de trabajo desde navegador:

| Acceso | Uso | Ventaja | Requisito |
| --- | --- | --- | --- |
| Panel nativo en `:8080` | Medidores, registro, exportación CSV y estado | Es la vía más ligera para una PC antigua | Python 3, Flask y pySerial |
| noVNC en `:6080` | Escritorio virtual completo | Permite ver el entorno gráfico aunque el equipo no tenga pantalla | Xvfb, Openbox, x11vnc, noVNC y websockify |

El panel nativo es la opción recomendada para uso diario. noVNC queda disponible como consola de mantenimiento. Ambas direcciones funcionan únicamente dentro de la red local.

## Estructura

```text
DCtuneRstudio/
├── instalador.sh             # instalación y activación del servicio
├── dctuner.service           # arranque automático de systemd
├── dctuner-run.sh            # Xvfb, noVNC y servidor web
├── conf-red                  # ejemplo de IP fija para cable directo
├── dctuner_web/
│   ├── index.html             # interfaz principal
│   ├── styles.css             # estilos sin frameworks
│   ├── panel.js               # actualización, gráfica y controles
│   └── servidor.py            # API Flask, simulador y transporte serie
├── tests/test_servidor.py     # pruebas del parser y API
└── README.md
```

## Instalación en Debian 12 i386

La instalación necesita privilegios de administrador. Si el equipo está completamente aislado, prepara antes los paquetes Debian en una memoria USB o usa un DVD/repositorio local. Después de instalar, la aplicación no hace conexiones externas.

1. Copia la carpeta completa al equipo ECU. Por ejemplo, desde una memoria USB:

   ```sh
   cp -a /media/usuario/USB/DCtuneRstudio /tmp/
   cd /tmp/DCtuneRstudio
   ```

2. Conecta el cable de red entre la PC ECU y la laptop. Identifica la interfaz con:

   ```sh
   ip -br link
   ```

3. Ejecuta el instalador. Para una instalación con paquetes ya descargados usa `DCTUNER_OFFLINE=1`:

   ```sh
   sudo DCTUNER_OFFLINE=1 sh instalador.sh
   ```

   Si el sistema tiene un repositorio Debian accesible durante la instalación, se puede omitir la variable:

   ```sh
   sudo sh instalador.sh
   ```

4. Si la interfaz no se llama `enp1s0`, repite la instalación indicando el nombre correcto:

   ```sh
   sudo DCTUNER_NET_IFACE=enp3s0 DCTUNER_OFFLINE=1 sh instalador.sh
   ```

El instalador copia la aplicación a `/opt/dctuner`, instala `python3-flask`, `python3-serial`, Xvfb, Openbox, x11vnc, noVNC y websockify, añade el usuario al grupo `dialout`, configura la IP `192.168.50.10/24` y activa `dctuner.service`.

## Acceso desde la laptop o el celular

Configura el adaptador de red del dispositivo cliente con una dirección del mismo rango, por ejemplo `192.168.50.20/24`, sin gateway. Abre:

- **Panel principal:** `http://192.168.50.10:8080/`
- **Consola noVNC:** `http://192.168.50.10:6080/vnc.html`

La ECU se conecta por USB a la PC que ejecuta DC TUNER STUDIO. El cliente web no necesita drivers USB.

## Configurar el puerto de la ECU

Comprueba qué dispositivo creó Linux:

```sh
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true
dmesg | tail -n 30
id
```

Los adaptadores FTDI, CH340 y CP2102 normalmente aparecen como `/dev/ttyUSB0`. Algunos controladores aparecen como `/dev/ttyACM0`. El usuario del servicio debe pertenecer a `dialout`; cierra la sesión y vuelve a entrar si necesitas que se actualice el grupo.

La configuración está en `/etc/default/dctuner`:

```sh
DCTUNER_SERIE=0
DCTUNER_PORT=/dev/ttyUSB0
DCTUNER_BAUD=115200
DCTUNER_WEB_PORT=8080
DCTUNER_VNC_PORT=6080
```

Cambia `DCTUNER_SERIE=0` a `DCTUNER_SERIE=1` cuando el simulador ya funcione. Reinicia:

```sh
sudo systemctl restart dctuner.service
sudo systemctl status dctuner.service --no-pager
```

El backend acepta dos formatos de telemetría genérica para perfiles y adaptadores locales:

```text
1200,86,100,14.7,35,12,13.8,18
RPM=1200,TEMP=86,MAP=100,AFR=14.7,LOAD=35,ADV=12,VOLT=13.8,TPS=18
```

El protocolo exacto de MegaSquirt puede variar entre MS1, MS2, MS3 y MicroSquirt. Por eso el transporte base no adivina comandos ni escribe mapas automáticamente. Para usar una familia concreta se debe añadir su perfil de protocolo, con la tasa de comunicación y el formato de trama confirmados para ese firmware.

## Verificación y solución de problemas

Prueba el backend sin abrir un puerto de red:

```sh
python3 dctuner_web/servidor.py --self-test
```

Comprueba el servicio:

```sh
sudo systemctl is-enabled dctuner.service
sudo systemctl is-active dctuner.service
sudo journalctl -u dctuner.service -n 80 --no-pager
```

Comprueba que escucha en los puertos esperados:

```sh
ss -ltnp | grep -E ':8080|:6080'
curl http://127.0.0.1:8080/api/health
```

Si el panel no abre desde la laptop, verifica el enlace físico, la IP de ambos equipos y que el adaptador cliente no tenga una ruta que reemplace la red `192.168.50.0/24`. Si `:8080` funciona pero `:6080` no, revisa si `/usr/share/novnc` existe y consulta `/run/dctuner/websockify.log`.

## Seguridad y operación

La aplicación escucha en todas las interfaces porque el uso previsto es una red directa. No la publiques en internet ni la conectes a una red compartida sin colocar una protección adicional. La terminal se mantiene bloqueada en simulación y limita los comandos a texto ASCII corto. El borrado de DTC, las pruebas de actuadores y la escritura de mapas deben implementarse mediante un perfil de ECU explícito; no se simulan como si fueran operaciones reales.

Los registros CSV se guardan en `/var/lib/dctuner/logs`. El botón **EXPORTAR CSV** descarga la ventana de telemetría retenida en memoria. Para conservar sesiones completas, inicia **GRABAR** antes de la prueba. La retención de memoria está limitada para conservar recursos en una máquina de 32 bits.

El bloque **Editor local de tabla 16 × 16** permite cargar archivos `.MSQ`, `.BIN`, `.CSV` o JSON desde el navegador, modificar celdas, deshacer y rehacer cambios, comparar otro archivo y guardar una copia. La vista 3D es una visualización de la tabla. El editor no escribe en la ECU: la copia modificada debe validarse con el perfil de firmware correspondiente antes de usarla en el vehículo.

## Desarrollo y pruebas

No hay dependencias JavaScript externas. Esto reduce el consumo y evita que el panel dependa de internet. En una estación de desarrollo con Flask instalado, ejecuta:

```sh
python3 -m unittest discover -s tests -v
python3 dctuner_web/servidor.py --self-test
```

Para iniciar manualmente en simulación:

```sh
python3 dctuner_web/servidor.py --host 0.0.0.0 --port 8080
```

## Resumen de direcciones

| Elemento | Valor |
| --- | --- |
| PC ECU | `192.168.50.10/24` |
| Panel web | `http://192.168.50.10:8080/` |
| Consola noVNC | `http://192.168.50.10:6080/vnc.html` |
| ECU | USB directo a la PC ECU |
| Internet | No necesario después de instalar |
| Logs | `/var/lib/dctuner/logs/` |
| Servicio | `dctuner.service` |

## Referencias

[1]: https://www.debian.org/releases/bookworm/ "Debian 12 Bookworm"

[2]: https://flask.palletsprojects.com/ "Flask Documentation"

[3]: https://pyserial.readthedocs.io/ "pySerial Documentation"

[4]: https://novnc.com/info.html "noVNC Project Information"
