# DC TUNER STUDIO

Aplicación de escritorio offline-first para diagnóstico, telemetría y edición de mapas de motor. Este primer MVP está construido con **Python + Tkinter**, por lo que puede ejecutarse en Windows y Linux sin instalar un framework UI adicional.

> La aplicación no genera datos sintéticos: sin una ECU real conectada, los valores permanecen en blanco. Las operaciones de escritura ECU no están automatizadas en este MVP.

## Funciones incluidas

- Interfaz oscura profesional con identidad textual DC TUNER STUDIO en azul, blanco y rojo neón.
- Panel en vivo con bloques separados para RPM, MAP, TPS, CLT, IAT, AFR, avance, pulso de inyector y voltaje.
- Cada sensor muestra nombre, valor, unidad, color propio, explicación y nota contextual al pasar el ratón.
- Tacómetro circular con escala 0–8000 RPM, aguja, lectura digital y zona roja.
- Velocímetro circular con escala 0–240 km/h, aguja y lectura digital.
- Los dos instrumentos principales ocupan ahora la franja superior del panel para una lectura inmediata durante la conducción o el ajuste.
- Indicador de **CV estimados siempre activo**, recalculado con cada muestra nueva de RPM, MAP y AFR; queda explícitamente marcado como estimación y no como medición de dinamómetro. La cilindrada y la eficiencia volumétrica son editables y quedan visibles junto al resultado; al desconectar conserva la última lectura calculada.
- Transporte de hardware real por puertos USB/serie cuando `pyserial` está instalado.
- Detección de puertos USB reales y descarte de tramas inválidas.
- Transporte serie opcional con líneas CSV: `rpm,map,tps,clt,afr,battery`.
- Carga y guardado de mapas `.MSQ` en JSON compatible con el formato DCTB.
- Carga y guardado de `.BIN` binario de muestra DCTB.
- Visualización de superficie 3D pseudo-isométrica y curvas 2D sin dependencias externas.
- Registro de telemetría con exportación CSV.
- Exportación PDF offline mediante el generador integrado.
- Comparación de mapas celda a celda.
- Tooltips al pasar el ratón por sensores y controles, con notas de interpretación.
- Contexto de celda al mover el cursor sobre el mapa: fila, columna, valor y consejo de ajuste conservador.
- Reconexión y registro básico de errores de comunicación.
- Selector de perfil para **Speeduino**, **MegaSquirt/Microsquirt** y **ELM327**.
- Adaptadores de identificación y normalización de telemetría en modo solo lectura.
- Importación de definiciones TunerStudio-style `.ini` para identificar firma, versión y secciones del firmware.

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

Para usar puertos serie reales:

```bash
python -m pip install -r requirements-optional.txt
```

## Prueba segura

1. Ejecuta la aplicación.
2. Conecta una ECU real y verifica el puerto detectado.
3. Selecciona el perfil de firmware correcto.
4. Pulsa **Conectar** y confirma que las tramas son válidas.
5. Abre el panel en vivo y el registro.
6. Exporta CSV o PDF desde la pestaña de registro.
7. Usa **Duplicar mapa** y **Comparar diferencias** para preparar ajustes offline.

En una conexión serie real selecciona primero el perfil ECU y después el puerto. El
MVP espera una línea de telemetría normalizada con seis campos CSV:
`rpm,map,tps,clt,afr,battery`. La selección no habilita escritura ni flasheo.

Puedes cargar una definición pública desde **Archivo → Cargar definición ECU (.ini)**.
El proyecto incluye una referencia `speeduino.ini` bajo `assets/definitions/` y su
licencia correspondiente. Las librerías propietarias de TunerStudio MS no se
redistribuyen; se implementa un lector compatible de metadatos y se respetan las
licencias de cada proyecto.

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
