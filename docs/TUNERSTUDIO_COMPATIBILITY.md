# DC TUNER STUDIO — Manual integrado y matriz de compatibilidad

## Propósito

DC TUNER STUDIO toma como referencia el modelo de trabajo de TunerStudio MS: un proyecto de ECU contiene la definición del firmware, ajustes, mapas, dashboards y registros. Esta guía resume funciones documentadas públicamente por EFI Analytics y Speeduino y las convierte en una hoja de ruta propia para DC TUNER STUDIO.

No se copia el manual propietario ni se afirma compatibilidad con un firmware que no haya sido probado. Las funciones de escritura, pruebas de actuadores y flasheo requieren validación de hardware, checksum, backup y recuperación.

## Funciones documentadas que se incorporan al diseño

| Área | En TunerStudio MS / documentación relacionada | Estado en DC TUNER STUDIO |
|---|---|---|
| Dashboards | Dashboards con pestañas, gauges seleccionables, pantalla completa y diseñador visual | MVP: panel en vivo; siguiente fase: dashboards guardables y editor drag-and-drop |
| Canales runtime | Las definiciones de ECU describen canales, expresiones, gauges, paneles y diálogos | Arquitectura preparada; falta cargador de definiciones `.ini` |
| Tablas | Edición offline, tabla 2D/3D, selección y seguimiento de celdas | MVP: superficies 2D/3D y comparación; falta editor de celdas y targeting |
| VE Analyze | Filtros, heatmap, hit counts, authority limits, compensación lambda/delay y propuesta de cambios | Pendiente: motor de análisis con simulador y límites configurables |
| Restore points | Puntos de restauración y comparación gráfica antes de aceptar cambios | Pendiente: historial persistente y restauración por mapa |
| Datalogging | Perfiles de datos, inicio/parada por condiciones, logging de alta velocidad | MVP: captura en segundo plano; pendiente: perfiles y triggers |
| Playback | Reproducción que alimenta dashboards, trazas y tablas como si la ECU estuviera conectada | Pendiente: reproductor sincronizado |
| Loggers | Tooth, trigger, composite, sync y gráficos XY/CVS según la definición | Pendiente: decodificadores por firmware |
| Proyectos ECU | Definición de firmware, tune, logs, opciones de interfaz y puerto | MVP: perfiles de protocolo; pendiente: proyecto persistente e INI |
| Protocolos | MegaSquirt, Speeduino y ELM327 dependen de firmware, definición y transporte concretos | Perfiles read-only implementados; faltan fixtures/hardware por versión |
| Diagnóstico | DTC y comandos dependen de ECU/firmware/definición; no se debe asumir una API universal | Pendiente: adaptadores específicos, no genéricos |

## Guía de uso del MVP

1. Selecciona el perfil **MegaSquirt/Microsquirt**, **Speeduino** o **ELM327**.
2. Usa `SIMULATOR` para probar la interfaz sin vehículo.
3. Para hardware real, instala `pyserial`, selecciona el puerto y verifica la velocidad del perfil.
4. Comienza en modo lectura y confirma que los canales tienen valores razonables.
5. Registra datos y exporta CSV/PDF.
6. Guarda un mapa antes de compararlo o modificarlo.
7. No uses terminal ECU, pruebas de actuadores o escritura hasta tener backup y recuperación comprobados.

## Modelo de seguridad para funciones futuras

Antes de habilitar un botón de escritura o burn, la aplicación deberá mostrar el proyecto, firmware, puerto, checksum, tamaño del payload, copia de seguridad y plan de recuperación. La operación debe permitir cancelar, registrar bytes/respuestas y recuperar el último mapa conocido. Las pruebas de actuadores deberán requerir confirmación reforzada y recomendar ECU desconectada del vehículo cuando corresponda.

## Fuentes públicas consultadas

1. [EFI Analytics — TunerStudio](https://www.efianalytics.com/TunerStudio/)
2. [EFI Analytics — Feature Matrix](https://www.efianalytics.com/TunerStudio/docs/EFI%20Analytics%20ECU%20Definition%20files.pdf)
3. [TunerStudio — Feature Matrix](https://www.tunerstudio.com/index.php/products/tuner-studio/tsarticles/119-tunerstudio-30-feature-matrix)
4. [EFI Analytics — ECU Definition Files](https://www.efianalytics.com/TunerStudio/docs/EFI%20Analytics%20ECU%20Definition%20files.pdf)
5. [MegaLogViewer VE Analyze](https://www.efianalytics.com/MegaLogViewer/veAnalysis.html)
6. [TunerStudio — Log Playback](https://www.tunerstudio.com/index.php/products/tuner-studio/tsarticles/126-log-playback)
7. [TunerStudio — Data Log Profiles](https://www.tunerstudio.com/index.php/products/tuner-studio/tsarticles/94-data-log-profiles)
8. [Speeduino — Connecting to TunerStudio](https://wiki.speeduino.com/en/Connecting_to_TunerStudio/)
9. [Speeduino — Interface Protocol](https://wiki.speeduino.com/en/reference/Interface_Protocol)
10. [Speeduino — Configuring TunerStudio](https://wiki.speeduino.com/en/Configuring_TunerStudio)

Las fuentes anteriores describen el producto y protocolos de referencia. La compatibilidad final de DC TUNER STUDIO se determina por pruebas reproducibles contra cada combinación de firmware, definición y hardware.
