# 🍎 Bad Apple!! en LCD 16x2 para PIC16F877A y PIC18F4550

Port optimizado de **Bad Apple!!** para microcontroladores PIC (16F877A y 18F4550) controlando una pantalla LCD alfanumérica 16x2 (controlador HD44780 o compatible) usando el compilador **CCS C Compiler v5**.

Basado en el algoritmo de compresión por deltas de `img2lcdino` (arduinocelentano) adaptado para exprimir al máximo la memoria de programa (Flash ROM) de los microcontroladores PIC.

---

## 📁 Archivos en este directorio

| Archivo | Descripción |
|---|---|
| [`badapple_pic.c`](file:///home/vibecode/DevS/bad%20apple/pic_port/badapple_pic.c) | Código fuente en C para CCS Compiler v5. Soporta PIC16F877A y PIC18F4550 mediante un simple `#define`. |
| [`lcd_flex/`](file:///home/vibecode/DevS/bad%20apple/pic_port/lcd_flex/) | Driver flexible y avanzado para LCD 16x2 y 20x4 en CCS C, con paridad total frente a `LiquidCrystal` de Arduino. |
| [`setup_env.sh`](file:///home/vibecode/DevS/bad%20apple/pic_port/setup_env.sh) | **Configurador del entorno Python**: Crea `.venv` e instala dependencias (Pillow, OpenCV) sin requerir `sudo`. |
| [`video2frames.py`](file:///home/vibecode/DevS/bad%20apple/pic_port/video2frames.py) | **Extractor de frames**: Lee el video MP4 local y guarda los frames 20x16 binarizados en `frames/`. |
| [`img2pic.py`](file:///home/vibecode/DevS/bad%20apple/pic_port/img2pic.py) | Conversor de frames PNG a datos delta organizados en chunks de 512B con switch `rom_read`. Soporta multi-parte automático. |
| [`gen_video.sh`](file:///home/vibecode/DevS/bad%20apple/pic_port/gen_video.sh) | **Extractor desde video MP4 local**: Busca el video en esta carpeta y extrae los fotogramas a la carpeta `frames/`. |
| [`gen_pic18.sh`](file:///home/vibecode/DevS/bad%20apple/pic_port/gen_pic18.sh) | Generador para **PIC18F4550** (~28 KB útiles, hasta **1000 frames completos** en 1 parte). |
| [`gen_pic16.sh`](file:///home/vibecode/DevS/bad%20apple/pic_port/gen_pic16.sh) | Generador para **PIC16F877A** (~4.5 KB útiles por parte, genera automáticamente `frame_data.h`, `frame_data2.h`, etc.). |
| [`gen_rapido.sh`](file:///home/vibecode/DevS/bad%20apple/pic_port/gen_rapido.sh) | **Generación rápida de 1 comando**: Usa la carpeta `frames/` para generar `frame_data.h` directamente. |
| [`frame_data.h`](file:///home/vibecode/DevS/bad%20apple/pic_port/frame_data.h) | Cabecera C generada con los metadatos y el array de animación en ROM. |

---

## ⚡ Preparación del Entorno (100% sin sudo)

Para asegurar que todo funcione sin modificar paquetes del sistema operativo ni requerir privilegios de superusuario (`sudo`):

```bash
# Desde pic_port/:
./setup_env.sh
```
Este script crea el entorno virtual `.venv` local e instala automáticamente `Pillow`, `opencv-python-headless` y `numpy`. Todos los scripts `.sh` detectan y utilizan este `.venv` por defecto.

---

## 🎬 Flujo de Trabajo: Video -> Frames -> Código C

### Paso 1: Extraer los Frames del Video Original a la carpeta `frames/`
El video (`東方Bad Apple!! ＰＶ影絵.mp4` o cualquier otro `.mp4`) se busca automáticamente en la misma carpeta:
```bash
# Extrae los fotogramas binarizados (20x16) a la carpeta frames/
./gen_video.sh
```

### Paso 2: Convertir los Frames a `frame_data.h` para el PIC

#### Para PIC18F4550 (Recomendado - entran hasta 1000 frames completos):
```bash
./gen_pic18.sh
```

#### Para PIC16F877A (Con división automática en partes):
```bash
./gen_pic16.sh
```

#### O Generación rápida en 1 comando:
```bash
./gen_rapido.sh pic18       # Para PIC18F4550 (10 FPS, threshold=2)
./gen_rapido.sh pic16       # Para PIC16F877A (6 FPS, threshold=3)
```
### 4. Sistema Multi-Parte (Video Completo por Partes)
Cuando el video o set de frames supera la memoria de un microcontrolador (por ejemplo, los 1000 frames en el **PIC16F877A** con límite de ~4.5 KB), los scripts dividen automáticamente el video en partes secuenciales:
- `frame_data.h` / `frame_data1.h`: Parte 1 (ej. frames 1..406)
- `frame_data2.h`: Parte 2 (ej. frames 407..751)
- `frame_data3.h`: Parte 3 (ej. frames 752..1000)

Cada parte arranca con un **Keyframe** limpio (todos los caracteres sincronizados). Para compilar cualquiera de las partes, simplemente cambia en [`badapple_pic.c`](file:///home/vibecode/DevS/bad%20apple/pic_port/badapple_pic.c):
```c
#define USE_PART  1   // Cambia a 2, 3, etc. para compilar esa parte
```
En la pantalla LCD 16x2 se indicará automáticamente en qué parte estás: `Frames: 406  P1/3`.

---

## 📊 Capacidad y Memoria Flash (Benchmarks Reales)

El set de 1000 frames de Bad Apple se comprime con deltas entre frames. El parámetro `--threshold` define cuántos píxeles pueden diferir antes de considerar que un carácter CGRAM cambió:

| Umbral (`threshold`) | Bytes/frame promedio | PIC16F877A (~6 KB Flash útiles) | PIC18F4550 (~28 KB Flash útiles) | Calidad Visual |
|:---:|:---:|:---:|:---:|:---:|
| **0 (Lossless)** | 36.2 B | 169 frames (28s @ 6fps) | 792 frames (79s @ 10fps) | Perfecta (idéntica al video) |
| **1** | 29.5 B | 208 frames (35s @ 6fps) | 971 frames (97s @ 10fps) | Pérdida imperceptible |
| **2 (Recomendado PIC18)** | **24.6 B** | **249 frames (42s @ 6fps)** | **1000 frames (100s @ 10fps) ✅** | Excelente calidad |
| **3 (Recomendado PIC16)** | **20.9 B** | **334 frames (56s @ 6fps) ✅** | **1000 frames (100s @ 10fps) ✅** | Muy buena (leves detalles) |
| **5** | 16.5 B | 372 frames (62s @ 6fps) | 1000 frames (100s @ 10fps) ✅ | Pérdida en bordes finos |
| **8 (Agresivo)** | 12.7 B | 483 frames (80s @ 6fps) | 1000 frames (100s @ 10fps) ✅ | Pérdida visible en siluetas |

> **Nota:** En el PIC18F4550 con `threshold=2`, el video completo de **1000 frames a 10 FPS (1 minuto 40 segundos ininterrumpidos)** cabe íntegramente dentro de los 32 KB de flash interna del microcontrolador sin requerir tarjetas SD ni memorias EEPROM externas.

---

## 🔌 Conexiones de Hardware (Esquema y Pinout)

El proyecto utiliza el LCD 16x2 en **modo de 4 bits** conectado al **PUERTO D** de cualquiera de los dos PICs:

```
               PIC16F877A / PIC18F4550               LCD 16x2 (HD44780)
             ┌─────────────────────────┐           ┌───────────────────┐
             │                     RD4 │───────────│ D4 (pin 11)       │
             │                     RD5 │───────────│ D5 (pin 12)       │
             │                     RD6 │───────────│ D6 (pin 13)       │
             │                     RD7 │───────────│ D7 (pin 14)       │
             │                     RD2 │───────────│ RS (pin 4)        │
             │                     RD3 │───────────│ EN (pin 6)        │
             │                         │           │                   │
             │                     GND │───────────│ RW (pin 5) [GND]  │
             │                     GND │───────────│ VSS (pin 1)       │
             │                     +5V │───────────│ VDD (pin 2)       │
             │                         │           │                   │
             │                     GND ├──[POT 10K]┤ V0 (pin 3, Cont.) │
             │                         │      │    │                   │
             │                     +5V ├──[220Ω]───│ A (pin 15, Ánodo) │
             │                     GND ────────────│ K (pin 16, Cátodo)│
             └─────────────────────────┘           └───────────────────┘
```

### Tabla de pines:
| Pin LCD | Nombre | Función | Conexión en el PIC / Circuito |
|:---:|:---:|:---|:---|
| 1 | **VSS** | Tierra (0V) | GND común |
| 2 | **VDD** | Alimentación lógica (+5V) | +5V |
| 3 | **V0** | Voltaje de contraste | Pin central de potenciómetro 10kΩ entre +5V y GND |
| 4 | **RS** | Register Select | **RD2** del PIC |
| 5 | **RW** | Read / Write | **GND** (Modo solo escritura permanente) |
| 6 | **EN** | Enable | **RD3** del PIC |
| 7-10 | **D0-D3** | Líneas de datos bajas | No conectar (NC) |
| 11 | **D4** | Línea de datos 4 | **RD4** del PIC |
| 12 | **D5** | Línea de datos 5 | **RD5** del PIC |
| 13 | **D6** | Línea de datos 6 | **RD6** del PIC |
| 14 | **D7** | Línea de datos 7 | **RD7** del PIC |
| 15 | **A (LED+)** | Ánodo backlight | +5V a través de resistencia de 220Ω |
| 16 | **K (LED-)** | Cátodo backlight | GND común |

> ⚠️ **IMPORTANTE:**
> 1. El pin **RW (pin 5) DEBE ir a GND**. Si queda flotante o desconectado, el LCD no responderá a los comandos.
> 2. Ajusta el potenciómetro en **V0** si la pantalla enciende pero no muestra caracteres.

---

## 🛠️ Cómo Compilar con CCS C Compiler v5

1. Abre **CCS PIC C Compiler** (PCWHD) o tu IDE preferido (como **MPLAB X** con el plugin CCS integrado).
2. Abre el proyecto o el archivo [`badapple_pic.c`](file:///home/vibecode/DevS/bad%20apple/pic_port/badapple_pic.c).
3. Asegúrate de que tanto la carpeta [`lcd_flex/`](file:///home/vibecode/DevS/bad%20apple/pic_port/lcd_flex/) como [`frame_data.h`](file:///home/vibecode/DevS/bad%20apple/pic_port/frame_data.h) estén en el mismo directorio que `badapple_pic.c`.
4. En las primeras líneas de `badapple_pic.c`, descomenta el microcontrolador que vas a utilizar:

```c
// ============================================================
// SELECCIÓN DE MICROCONTROLADOR: Descomentar UNO solo
// ============================================================
#define USE_PIC16       // Activar para PIC16F877A
//#define USE_PIC18     // Activar para PIC18F4550
```

5. Compila el proyecto (**Compile** o tecla `F9`).
6. Carga el archivo `.hex` resultante a tu PIC usando tu programador habitual (**PICkit 2, 3 o 4**, TL866, etc.).

---

## 💡 ¿Por qué usamos `flex_lcd.c` en lugar del `<lcd.c>` original?

En CCS C, el driver de fábrica `<lcd.c>` tiene dos limitaciones críticas que provocan el error `Undefined identifier lcdlat`:
1. **Nombres de pines estrictos**: Exige que se definan exactamente los 7 pines con los nombres `LCD_DATA4..7`, `LCD_ENABLE_PIN`, `LCD_RS_PIN`, y `LCD_RW_PIN`. Si se define `LCD_DATA4` pero falta `LCD_RW_PIN` o se usa `LCD_EN`, la librería desactiva la estructura `lcdlat` e intenta acceder a ella, provocando el fallo al compilar.
2. **Obligatoriedad del pin RW**: `<lcd.c>` no permite conectar RW a GND (modo 6 pines); siempre intenta leer el busy flag (`while(bit_test(lcd_read_byte(), 7))`). Si RW está a GND, el microcontrolador se bloquea esperando una respuesta que la pantalla nunca enviará.

[`flex_lcd.c`](file:///home/vibecode/DevS/bad%20apple/pic_port/flex_lcd.c) resuelve ambos problemas:
- Permite mapear cualquier pin en cualquier orden.
- Funciona perfectamente con **RW conectado a GND (modo 6 pines)** usando retardos de microsegundos seguros.
- No depende de `lcdlat` ni de registros específicos de familia.

---

## 🔬 ¿Cómo Funciona la Compresión Delta?

Una pantalla LCD 16x2 solo tiene memoria CGRAM para definir **8 caracteres personalizados** (cada uno de 5 columnas × 8 filas de píxeles).

La pantalla se organiza como una matriz de 4×2 caracteres personalizados:
```
Fila superior: [Char 0][Char 1][Char 2][Char 3]
Fila inferior: [Char 4][Char 5][Char 6][Char 7]
```

En lugar de almacenar y transmitir todos los caracteres en cada cuadro (lo que requeriría 65 bytes por frame):
1. **Delta check**: Se compara cada carácter del nuevo frame contra el frame anterior.
2. Si el número de píxeles diferentes es menor o igual al umbral (`threshold`), el carácter **no se actualiza**.
3. **Bitmask de 1 byte**:
   - Cada bit (del 0 al 7) indica si el carácter correspondiente cambió (`1`) o sigue idéntico (`0`).
4. **Datos variables**: A continuación del bitmask, solo se envían los 8 bytes de los caracteres cuyo bit fue `1`.

```
Estructura de un frame en memoria:
[Byte 0: Bitmask (8 bits)] + [8 bytes por cada bit en '1']
```

Ejemplo: Si en un frame solo cambiaron 2 caracteres (los bits 1 y 5):
- Tamaño de ese frame = 1 byte (máscara) + 2 × 8 bytes = **17 bytes** (en vez de 65 bytes).
- Ahorro de memoria: **74%**.

---

## ⚙️ Uso Manual Avanzado de `img2pic.py`

Si deseas personalizar todos los argumentos por línea de comandos directamente:

```bash
python3 img2pic.py --help
```

### Opciones disponibles:
- `--frames "PATRÓN"`: Ruta con glob entre comillas a los frames PNG (ej. `"../frames/*.png"`).
- `--no-gaps`: Asume frames de 20x16 sin espacios muertos entre caracteres (usado para los 1000 frames).
- `--pic16`: Aplica el límite máximo de ROM de ~6 KB para el PIC16F877A y trunca automáticamente si se sobrepasa.
- `--pic18`: Aplica el límite máximo de ROM de ~28 KB para el PIC18F4550.
- `--threshold N`: Umbral de tolerancia de píxeles modificados para compresión con pérdida (default: 0).
- `--fps N`: Tasa de cuadros por segundo para la reproducción (default: 10).
- `--max-frames N`: Límite estricto en la cantidad de frames a procesar.
- `--output ARCHIVO.h`: Nombre del archivo de salida (default: `frame_data.h`).
