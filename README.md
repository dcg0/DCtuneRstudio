# DCtuneRstudio


<p align="center">
  <a href="https://github.com/dcg0/DCtuneRstudio/actions/workflows/security.yml"><img src="https://github.com/dcg0/DCtuneRstudio/actions/workflows/security.yml/badge.svg" alt="Security checks"></a>
  <a href="https://github.com/dcg0/DCtuneRstudio/security"><img src="https://img.shields.io/badge/security-policy-available-176b46" alt="Security policy available"></a>
</p>

![DCtuneRstudio](client/public/splash.png)

> Estudio web local para calibración, telemetría y análisis de registros de MegaSquirt y Speeduino en Linux y Windows de 32/64 bits.

Interfaz web de escritorio para calibración, telemetría y análisis de logs de **MegaSquirt** y **Speeduino**. La entrega funciona con **ECU real únicamente**: el modo offline en Debian 12 conecta USB/serie y el sitio online sirve como interfaz de configuración/documentación, pero nunca inventa ni simula datos de motor.

## Qué incluye

- Panel en vivo con **tacómetro circular**, **velocímetro circular**, AFR y temperatura CLT.
- Conexión ECU real únicamente por USB/serie; sin modo demo ni datos inventados.
- Editor visual de tablas de ajuste con copia local, edición por celda y exportación.
- Visor web de logs inspirado en los flujos de MegaLogViewer: CSV/LOG/TXT, filtros, gráfica y reproducción.
- VE Analyze con sugerencia por celdas usando muestras del log y AFR objetivo 14.7.
- Selector y documentación de perfiles MegaSquirt y Speeduino.
- Guía de uso interactiva para instalar, conectar, probar, cargar mapas y analizar registros.
- Mini agente local **Lucy**, sin llamadas externas, que responde preguntas sobre la configuración de la aplicación, USB/serie, mapas, logs, AFR, RPM, velocidad y seguridad.
- Diagnóstico preparado para habilitarse con conexión local.
- Interfaz oscura, responsive y optimizada para escritorio.

## Importante sobre hardware

La web funciona como interfaz y analizador de archivos reales. Los navegadores no acceden directamente al puerto USB: el servicio Flask local incluido en `dcg0/DCtuneRstudio` abre la ECU y sirve el panel en Debian 12. La operación offline no necesita internet; el modo online permite consultar la configuración, pero no tiene acceso al USB local ni muestra telemetría inventada.

### Indicador de conexión

La cabecera y el panel lateral muestran en tiempo real uno de tres estados: **ECU conectada**, **ECU desconectada** o **error de conexión**. El navegador consulta `/api/status` cada 500 ms; cuando una ECU conectada deja de responder aparece una alerta visible y una notificación, y cuando vuelve a responder se notifica la recuperación de la telemetría.

### Lucy, asistente local

El chat integrado se llama **Lucy** y usa `client/public/lucy.jpg` como avatar local, sin depender de internet. Su base de conocimiento cubre instalación Debian 12, puertos USB/TTY, permisos `dialout`, baudrate 8N1, protocolos Speeduino y MegaSquirt, archivos INI/MSQ/BIN, RPM, VSS, AFR, MAP, CLT, voltaje, tablas VE/Spark, CSV/LOG, VE Analyze, respaldos, DTC, actuadores, errores del servicio y seguridad de pruebas. Las respuestas son informativas y no habilitan por sí solas escritura peligrosa en la ECU.

El puente local admite `/dev/ttyUSB*`, `/dev/ttyACM*` y puertos `COM*`; Speeduino usa su perfil binario y MegaSquirt conserva el transporte genérico hasta seleccionar la variante exacta de firmware.

## Matriz de protocolos

| Familia | Perfil de transporte | Lectura en el puente local |
| --- | --- | --- |
| Speeduino | USB/serie Debian, 115200 8N1, petición `A`, 120 bytes little-endian | RPM, MAP, temperatura, AFR, avance, TPS y voltaje |
| MegaSquirt-II / MS2-Extra | USB/serie, 115200; realtime con `a`, CAN ID y table index | Parser genérico y transporte; requiere `.ini` para offsets binarios |
| MegaSquirt-III / MicroSquirt | Firmware Default, protocolo definido por `.ini`, posible CAN | Requiere seleccionar la definición exacta antes de leer/escribir tablas |

No se mezclan offsets de Speeduino con MegaSquirt y no se habilitan escrituras automáticas sin una definición de firmware confirmada.

## Desarrollo

Requisitos: Node.js 22 o superior y pnpm.

```bash
pnpm install
pnpm dev
```

La aplicación se sirve en `http://localhost:3000`.

## Compilación de producción

```bash
pnpm check
pnpm build
```

El build genera los archivos estáticos de Vite y el servidor de producción del template WebDev.

## Uso rápido

1. Conecta la ECU, identifica el puerto COM/TTY y abre **Panel en vivo**; sin respuesta los medidores permanecen en cero.
2. En **Guía de uso**, sigue los seis pasos de preparación.
3. En **Ajuste de mapas**, carga o edita una copia de tu tabla; guarda una revisión antes de cambiar valores.
4. En **Logs y VE Analyze**, abre un CSV, aplica filtros y revisa las señales.
5. Ejecuta VE Analyze y revisa la sugerencia antes de aplicarla a la tabla local.
6. Pregunta a **Lucy** si necesitas ayuda con Speeduino, MegaSquirt, conexión, AFR, RPM, velocidad o seguridad.

## Publicación

El proyecto utiliza el scaffold `web-static` de Manus WebDev. Para la entrega offline, la imagen de portada se incluye localmente en `client/public/splash.png` y no depende de Manus Storage ni de internet. La copia JPEG optimizada mantiene la imagen proporcionada y queda por debajo del límite de publicación de medios.

## Estado del proyecto

Esta versión está preparada para Linux 32/64 bits y Windows 32/64 bits. El hardware real permanece separado en el servicio local para evitar exponer puertos serie, credenciales o comandos de ECU en internet. Consulta [PLATAFORMAS.md](PLATAFORMAS.md) para los cuatro arranques.

## Estructura del repositorio

```text
client/                 interfaz React publicada y modo online
local-bridge/           servidor Flask, serie, Speeduino y lanzadores Linux/Windows
PLATAFORMAS.md         matriz de Linux/Windows 32/64 bits y requisitos
local-bridge/tests/     pruebas del parser y de la API local
client/public/splash.png portada incluida para uso offline
```

Para instalar el puente Debian 12, entra en `local-bridge/` y ejecuta `sudo sh instalador.sh`. Para Linux 32/64 bits usa `sudo sh instalar-linux.sh`; para Windows 32/64 bits instala Python de la misma arquitectura, `pip install -r requirements.txt` y ejecuta `arrancar-windows.bat`. Los cuatro paquetes listos están en `releases/`. Después abre el panel local en `http://127.0.0.1:8080/`. Para trabajar online, usa la publicación WebDev del sitio; el modo online no tiene acceso al USB de la PC.


## Descargas

Los paquetes listos se encuentran en la carpeta [`releases/`](https://github.com/dcg0/DCtuneRstudio/tree/main/releases). Estos archivos son paquetes de aplicación para cada sistema; **no son APK de Android**. Windows y Linux no usan formato APK.

| Plataforma | Paquete | Enlace |
|---|---|---|
| Linux 32 bits | ZIP | [Descargar](releases/DCtuneRstudio-linux-i386.zip) |
| Linux 64 bits | ZIP | [Descargar](releases/DCtuneRstudio-linux-amd64.zip) |
| Windows 32 bits | ZIP | [Descargar](releases/DCtuneRstudio-windows-x86.zip) |
| Windows 64 bits | ZIP | [Descargar](releases/DCtuneRstudio-windows-x64.zip) |
| Raspberry Pi ARMv7 / 32 bits | TAR.GZ | [Descargar](releases/DCtuneRstudio-raspberry-armv7.tar.gz) |
| Raspberry Pi ARM64 / 64 bits | TAR.GZ | [Descargar](releases/DCtuneRstudio-raspberry-arm64.tar.gz) |

Los ZIP/TAR contienen el puente Flask, la interfaz local, los lanzadores y el instalador correspondiente. En Windows se necesita Python de la misma arquitectura: Python x86 para Windows de 32 bits y Python x64 para Windows de 64 bits. En Linux y Raspberry Pi se necesita Python 3, Flask, pySerial y permisos para el puerto serie.

### Raspberry Pi

En Raspberry Pi OS de 32 o 64 bits, conecta la ECU por USB, extrae el paquete correspondiente y ejecuta:

```bash
cd DCtuneRstudio-raspberry-armv7/local-bridge  # usa arm64 si corresponde
sudo sh instalar-raspberry.sh
```

Después de reiniciar la sesión para aplicar el grupo `dialout`, el panel estará en `http://127.0.0.1:8080/` y podrá abrirse desde otro equipo con la IP de la Raspberry Pi. El servicio se llama `dctuner-raspberry`.

### Compilación y empaquetado

El frontend web se comprueba y compila con `pnpm check && pnpm build`. Los paquetes multiplataforma del puente se generan con:

```bash
bash tools/build-releases.sh
```

El paquete no incluye un binario Python nativo: usa el intérprete instalado en cada sistema, lo que permite funcionar en x86, x86_64, ARMv7 y ARM64 sin mezclar arquitecturas. La telemetría real solo puede validarse conectando físicamente una ECU y un adaptador USB compatible.


## Versión web

La interfaz web se publica automáticamente con GitHub Pages después de activar Pages con **GitHub Actions** en la configuración del repositorio. El enlace esperado es:

[DCtuneRstudio Web](https://dcg0.github.io/DCtuneRstudio/)

Esta versión web sirve para consultar la interfaz, guías y análisis local de archivos. Para leer una ECU por USB/serie se debe ejecutar el puente local en Windows, Linux o Raspberry Pi; un navegador alojado en internet no puede acceder directamente al puerto USB de tu computadora.

## Variante roja DCtuneRstudio

Esta copia usa la aplicación multiplataforma terminada y conserva la identidad visual roja: portada, icono, nombre y textos de interfaz. La lógica de comunicación ECU, Speeduino, MegaSquirt, registros y análisis permanece igual.
