# DC TUNER STUDIO

Aplicación de escritorio offline-first para diagnóstico, telemetría y edición de mapas de motor. Este primer MVP está construido con **Python + Tkinter**, por lo que puede ejecutarse en Windows y Linux sin instalar un framework UI adicional.

> El modo simulador permite explorar el producto sin conectar un vehículo. Las operaciones de escritura ECU no están automatizadas en este MVP.

## Funciones incluidas

- Interfaz oscura profesional con identidad DC azul metálico y rojo neón.
- Panel en vivo con RPM, MAP, TPS, CLT, AFR y voltaje.
- Simulador ECU integrado para demostraciones y pruebas seguras.
- Detección de puertos USB cuando `pyserial` está instalado.
- Transporte serie opcional con líneas CSV: `rpm,map,tps,clt,afr,battery`.
- Carga y guardado de mapas `.MSQ` en JSON compatible con el formato DCTB.
- Carga y guardado de `.BIN` binario de muestra DCTB.
- Visualización de superficie 3D pseudo-isométrica y curvas 2D sin dependencias externas.
- Registro de telemetría con exportación CSV.
- Exportación PDF offline mediante el generador integrado.
- Comparación de mapas celda a celda.
- Reconexión y registro básico de errores de comunicación.
- Selector de perfil para **Speeduino**, **MegaSquirt/Microsquirt** y **ELM327**.
- Adaptadores de identificación y normalización de telemetría en modo solo lectura.

## Inicio rápido

### Linux

```bash
sudo apt install python3-tk
python3 dc_tuner_studio.py
```

### Windows 10/11

Instala Python 3.11+ con Tcl/Tk y ejecuta:

```powershell
python dc_tuner_studio.py
```

No se necesitan dependencias externas para el modo simulador. Para usar puertos serie reales:

```bash
python -m pip install -r requirements-optional.txt
```

## Prueba segura

1. Ejecuta la aplicación.
2. Mantén seleccionado `SIMULATOR`.
3. Pulsa **Conectar**.
4. Abre el panel en vivo y el registro.
5. Exporta CSV o PDF desde la pestaña de registro.
6. Usa **Duplicar mapa** y **Comparar diferencias** para probar el editor.

En una conexión serie real selecciona primero el perfil ECU y después el puerto. El
MVP espera una línea de telemetría normalizada con seis campos CSV:
`rpm,map,tps,clt,afr,battery`. La selección no habilita escritura ni flasheo.

## Empaquetado

Los scripts de `packaging/` preparan una distribución portable. El instalador final debe construirse en el sistema objetivo para incluir el runtime correcto:

```bash
./packaging/build-linux.sh
```

En Windows:

```powershell
.\packaging\build-windows.ps1
```

## Alcance del MVP

Los perfiles Speeduino, MegaSquirt/Microsquirt y ELM327 ya están separados como adaptadores de protocolo, pero la compatibilidad binaria completa y el formato `.MSQ` real requieren fixtures y validación contra hardware y firmware concretos. El MVP usa un formato JSON explícito para mapas y un BIN binario de muestra, evitando fingir compatibilidad con archivos ECU que todavía no han sido validados.

Antes de implementar escritura física se deben añadir: backup automático, validación de checksum, modo solo lectura, confirmación del dispositivo, rollback, cancelación segura y simuladores de ECU.

## Licencia

Código libre para DCG0 / DC TUNER STUDIO. Añadir el texto de licencia elegido por el proyecto antes de la versión 1.0.0.
