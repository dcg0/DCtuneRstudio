# Guía de configuración Speeduino mediante `speeduino.ini`

Esta guía explica cómo está organizada la definición pública de Speeduino incluida en el paquete portable de **DC TUNER STUDIO** y cómo localizar los canales que la aplicación debe leer.

> **Importante:** el archivo `.ini` describe el protocolo y la memoria del firmware; no es una lista CSV ni un archivo de configuración genérico. Los valores solo son válidos cuando proceden de una ECU Speeduino compatible con la firma y versión indicadas. Sin hardware real, la aplicación no muestra datos.

## Ubicación dentro del paquete portable

Después de extraer `dc-tuner-studio-linux-portable.tar.gz`, el archivo se encuentra en:

```text
dc-tuner-studio-linux/
└── assets/
    └── definitions/
        └── speeduino.ini
```

La copia incluida identifica el firmware como:

```ini
[MegaTune]
   queryCommand   = "Q"
   signature      = "speeduino 202504-dev"
   versionInfo    = "S"

[TunerStudio]
   iniSpecVersion = 3.64
```

No se debe cambiar `signature` para ocultar una incompatibilidad. Si la ECU tiene otra versión o un firmware distinto, se necesita la definición `.ini` correspondiente.

## 1. Parámetros de comunicación y páginas

La sección `[Constants]` define el tamaño de páginas, endianness y comandos de lectura/escritura. En esta versión Speeduino usa little-endian:

```ini
[Constants]
   endianness     = little
   nPages         = 15
   pageSize       = 128, 288, 288, 128, 288, 128, 240, 384, 192, 192, 288, 192, 128, 288, 256

   pageIdentifier  = "$tsCanId\x01", "$tsCanId\x02", ...
   pageReadCommand = "p%2i%2o%2c", "p%2i%2o%2c", ...
   pageValueWrite  = "M%2i%2o%2c%v", "M%2i%2o%2c%v", ...
   crc32CheckCommand = "d%2i", "d%2i", ...
```

Los marcadores tienen significado protocolario: `%i` representa la página, `%o` el offset, `%c` la cantidad de bytes y `%v` el valor. No deben sustituirse por valores inventados ni enviarse directamente sin implementar el sobre de comunicación, el checksum y la confirmación de respuesta.

Los parámetros relevantes de sincronización son:

```ini
   delayAfterPortOpen = 1000
   blockReadTimeout   = 2000
   blockingFactor     = 251
   pageActivationDelay = 10
```

El `baudrate` no se define en esta sección del archivo; lo aporta el perfil de conexión del firmware/adaptador. El perfil actual de Speeduino del proyecto usa **115200 baud**, pero la ECU real debe confirmar esa configuración.

## 2. Lectura del bloque de canales runtime

La sección `[OutputChannels]` indica cómo convertir bytes de la respuesta de la ECU en variables con nombre, tipo, offset, unidad, escala y traducción:

```ini
[OutputChannels]
   ochGetCommand = "r\$tsCanId\x30%2o%2c"
   ochBlockSize  = 139

   map            = scalar, U16,  4,  "kpa", 1.000, 0.000
   iatRaw         = scalar, U08,  6,  "°C",  1.000, 0.000
   coolantRaw     = scalar, U08,  7,  "°C",  1.000, 0.000
   batteryVoltage = scalar, U08,  9,  "V",   0.100, 0.000
   afr            = scalar, U08, 10,  "O2",  0.100, 0.000
   rpm            = scalar, U16, 14,  "rpm", 1.000, 0.000
   advance        = scalar, S08, 24,  "deg", 1.000, 0.000
   tps            = scalar, U08, 25,  "%",   0.500, 0.000
   pulseWidth     = scalar, U16, 76,  "ms",  0.001, 0.000
   vss            = scalar, U16, 104, "km/h",1.000, 0.000
```

La interpretación es:

| Campo | Ejemplo | Significado |
|---|---|---|
| Nombre | `rpm` | Nombre que usa la interfaz. |
| Tipo | `U16` | Entero sin signo de 16 bits. `S08` es entero con signo de 8 bits. |
| Offset | `14` | Posición dentro del bloque runtime. |
| Unidad | `rpm` | Unidad que se debe mostrar. |
| Escala | `1.000` | Multiplicador aplicado al valor bruto. |
| Traducción | `0.000` | Corrección aplicada al valor bruto. |

La regla general documentada en el propio INI es:

```text
valor_mostrado = valor_bruto / escala - traducción
```

Por ejemplo, si Speeduino devuelve el byte `139` para `batteryVoltage`, con escala `0.100`, la interfaz debe mostrar `13.9 V`. Para `afr`, un byte `147` representa `14.7`.

## 3. Canales derivados

Algunos canales no vienen directamente como bytes; se calculan a partir de otros canales:

```ini
#if CELSIUS
   coolant = { coolantRaw - 40 }
   iat     = { iatRaw - 40 }
#else
   coolant = { (coolantRaw - 40) * 1.8 + 32 }
   iat     = { (iatRaw - 40) * 1.8 + 32 }
#endif

   throttle = { tps }, "%"
   lambda   = { afr / stoich }
   vssMPH   = { vss / 1.60934 }
```

En la interfaz, un canal derivado solo debe calcularse después de validar todos sus canales de entrada. Si falta `afr`, no se debe calcular `lambda`; si falta `vss`, no se debe mostrar velocidad convertida.

## 4. Gauges

La sección `[GaugeConfigurations]` define el nombre del canal, título, unidad, escala y zonas de advertencia. Ejemplos del archivo Speeduino:

```ini
tachometer     = rpm,           "Engine Speed",       "RPM",  0,  {rpmhigh}, 300, 600, {rpmwarn}, {rpmdang}, 0, 0
mapGauge       = map,           "Engine MAP",         "kPa",  0,  {maphigh},   0,  20, {mapwarn}, {mapdang}, 0, 0
batteryVoltage = batteryVoltage,"Battery Voltage",    "volts",0, 25,          8,  9, 15, 16, 2, 2
vssGauge       = vss,           "Vehicle Speed (kph)","km/h", 0, 250,         5, 10, 180, 200, 0, 0
afrGauge       = afr,           "Air:Fuel Ratio",     "",     7, 25,          ..., 2, 2
cltGauge       = coolant,       "Coolant Temp",       "C",  -40, 120,         -15, 0, 95, 105, 0, 0
iatGauge       = iat,           "Inlet Air Temp",     "C",  -40, 120,         -15, 0, 95, 100, 0, 0
```

El tacómetro y el velocímetro de DC TUNER STUDIO deben tomar sus valores de `rpm` y `vss`, respectivamente. No deben usar un contador local ni estimar velocidad a partir de RPM.

## 5. Tablas de ajuste

La sección `[TableEditor]` enlaza cada tabla con sus ejes y datos:

```ini
table = veTable1Tbl, veTable1Map, "VE Table", 2
   xBins  = rpmBins,       rpm
   yBins  = fuelLoadBins,  fuelLoad
   xyLabels = "RPM", "Fuel Load: "
   zBins  = veTable

table = sparkTbl, sparkMap, "Ignition Advance Table", 3
   xBins  = rpmBins2, rpm
   yBins  = mapBins1, ignLoad
   xyLabels = "RPM", "Ignition Load: "
   zBins  = advTable1
```

Las líneas originales son `xBins`, `yBins` y `zBins`; deben conservarse exactamente con esos nombres.

Las tablas principales incluidas son:

| Tabla | Eje X | Eje Y | Datos |
|---|---|---|---|
| VE Table | RPM | Fuel Load | `veTable` |
| Ignition Advance Table | RPM | Ignition Load | `advTable1` |
| AFR Table | RPM | Fuel Load | `afrTable` |
| Lambda Table | RPM | Fuel Load | `lambdaTable` |
| Boost Duty / Target | RPM | Throttle | `boostTable` |
| VVT control Table | RPM | VVT Load | `vvtTable` |

Para editar una tabla de forma real hay que leer primero sus ejes, el bloque de memoria indicado por `Constants`, el `pageReadCommand` correspondiente y el CRC. No es correcto tratarla como una matriz local independiente de la ECU.

## 6. Comandos de control

`[ControllerCommands]` contiene comandos de prueba de actuadores y reinicio, por ejemplo:

```ini
cmdStopTestMode   = "E\x01\x00"
cmdEnableTestMode = "E\x01\x01"
cmdstm32reboot    = "E\x32\x00"
```

Estos comandos son potencialmente peligrosos. La versión actual de DC TUNER STUDIO los muestra como definición, pero **no los envía**. Antes de habilitarlos hacen falta identificación de firmware, permisos explícitos, confirmación, timeout, respuesta válida, registro de bytes y recuperación.

## 7. Qué soporta actualmente DC TUNER STUDIO

El paquete portable incluye el archivo real y el lector seguro de secciones y metadatos. El perfil Speeduino conoce el nombre del protocolo y el baudrate, y el transporte serie solo acepta tramas normalizadas válidas.

La implementación actual todavía no interpreta automáticamente todo el lenguaje TunerStudio: expresiones `#if`, macros `#define`, fórmulas, tipos binarios, sobres Speeduino, CRC, páginas y tablas no se convierten completamente a widgets y canales runtime. Por eso el `.ini` incluido sirve como referencia de compatibilidad y validación, no como promesa de que todas las funciones de TunerStudio MS ya están implementadas.

Para avanzar a compatibilidad completa, el siguiente paso técnico es implementar un decodificador binario Speeduino que use `ochGetCommand`, `ochBlockSize`, offsets, tipos, escalas, expresiones derivadas y validación de CRC. Solo después se deben habilitar lectura de mapas y escritura protegida.
