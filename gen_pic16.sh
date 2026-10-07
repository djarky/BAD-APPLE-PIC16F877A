#!/bin/bash
# ============================================================
#  gen_pic16.sh - Genera frame_data.h para PIC16F877A
#  Modo conservador: cabe en ~6KB de flash
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONVERTER="$SCRIPT_DIR/img2pic.py"
OUTPUT="$SCRIPT_DIR/frame_data.h"

# Frames disponibles (ajustar si moviste las carpetas)
FRAMES_1000="../Bad-Apple-On-Arduino-LCD-main/pngs/*.png"
FRAMES_76="../badapple/img2lcdino-main/frames/*.png"

echo "╔══════════════════════════════════════════╗"
echo "║  Generador de frames para PIC16F877A     ║"
echo "║  Flash disponible: ~6 KB                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""

shopt -s nullglob
files_1000=("$SCRIPT_DIR/../Bad-Apple-On-Arduino-LCD-main/pngs/"*.png)
files_76=("$SCRIPT_DIR/../badapple/img2lcdino-main/frames/"*.png)
shopt -u nullglob

HAS_1000=false
HAS_76=false
[ ${#files_1000[@]} -gt 0 ] && HAS_1000=true
[ ${#files_76[@]} -gt 0 ] && HAS_76=true

if ! $HAS_1000 && ! $HAS_76; then
    echo "ERROR: No se encontraron frames PNG."
    echo "Verifica que las carpetas de frames existan."
    exit 1
fi

echo "Frames encontrados:"
$HAS_1000 && echo "  [1] 1000 frames (20x16, sin gaps) - Bad-Apple-On-Arduino-LCD"
$HAS_76   && echo "  [2] 76 frames (24x18, con gaps)   - img2lcdino"
echo ""

read -p "¿Qué frames usar? [1/2]: " CHOICE

case "$CHOICE" in
    1)
        if ! $HAS_1000; then
            echo "No están disponibles los 1000 frames."
            exit 1
        fi
        FRAMES="$SCRIPT_DIR/$FRAMES_1000"
        GAPS="--no-gaps"
        echo ""
        echo "Usando 1000 frames (20x16). Con --pic16, se cortará"
        echo "automáticamente al llegar al límite de flash."
        ;;
    2)
        if ! $HAS_76; then
            echo "No están disponibles los 76 frames."
            exit 1
        fi
        FRAMES="$SCRIPT_DIR/$FRAMES_76"
        GAPS=""
        echo ""
        echo "Usando 76 frames (24x18, con gaps)."
        ;;
    *)
        echo "Opción inválida."
        exit 1
        ;;
esac

echo ""
echo "Configuración de compresión:"
echo "  [1] Lossless (threshold=0) - Menos frames, calidad perfecta"
echo "  [2] Suave    (threshold=3) - Más frames, pérdida casi invisible"
echo "  [3] Agresiva (threshold=5) - Máximo de frames, algo de pérdida"
echo ""
read -p "¿Nivel de compresión? [1/2/3] (default: 2): " COMP

case "$COMP" in
    1) THRESHOLD=0 ;;
    3) THRESHOLD=5 ;;
    *) THRESHOLD=3 ;;
esac

read -p "¿FPS? (default: 6): " FPS_INPUT
FPS=${FPS_INPUT:-6}

echo ""
echo "Generando con: --pic16 --threshold $THRESHOLD --fps $FPS"
echo "─────────────────────────────────────────────"

python3 "$CONVERTER" \
    --frames "$FRAMES" \
    $GAPS \
    --pic16 \
    --threshold "$THRESHOLD" \
    --fps "$FPS" \
    --output "$OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Archivo generado: $OUTPUT"
    echo "   Cópialo junto a badapple_pic.c y compila con CCS C v5."
    echo "   Asegúrate de tener: #define USE_PIC16"
fi
