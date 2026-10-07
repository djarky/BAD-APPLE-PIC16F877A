#!/bin/bash
# ============================================================
#  gen_pic18.sh - Genera frame_data.h para PIC18F4550
#  Modo máximo: hasta ~28KB de flash para datos
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONVERTER="$SCRIPT_DIR/img2pic.py"
OUTPUT="$SCRIPT_DIR/frame_data.h"

FRAMES_1000="../Bad-Apple-On-Arduino-LCD-main/pngs/*.png"
FRAMES_76="../badapple/img2lcdino-main/frames/*.png"

echo "╔══════════════════════════════════════════╗"
echo "║  Generador de frames para PIC18F4550     ║"
echo "║  Flash disponible: ~28 KB                ║"
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
    exit 1
fi

echo "Frames encontrados:"
$HAS_1000 && echo "  [1] 1000 frames (20x16, sin gaps) - Bad-Apple-On-Arduino-LCD"
$HAS_76   && echo "  [2] 76 frames (24x18, con gaps)   - img2lcdino"
echo ""

read -p "¿Qué frames usar? [1/2]: " CHOICE

case "$CHOICE" in
    1)
        if ! $HAS_1000; then echo "No disponibles."; exit 1; fi
        FRAMES="$SCRIPT_DIR/$FRAMES_1000"
        GAPS="--no-gaps"
        echo ""
        echo "Usando 1000 frames. Con threshold=2, los 1000 caben completos."
        ;;
    2)
        if ! $HAS_76; then echo "No disponibles."; exit 1; fi
        FRAMES="$SCRIPT_DIR/$FRAMES_76"
        GAPS=""
        echo ""
        echo "Usando 76 frames (todos caben sin problema)."
        ;;
    *)
        echo "Opción inválida."; exit 1
        ;;
esac

echo ""
echo "Configuración de compresión:"
echo "  [1] Lossless   (threshold=0) - Calidad perfecta (~792 frames max)"
echo "  [2] Suave      (threshold=2) - 1000 frames, pérdida mínima ← RECOMENDADO"
echo "  [3] Agresiva   (threshold=5) - 1000 frames, más espacio libre"
echo ""
read -p "¿Nivel de compresión? [1/2/3] (default: 2): " COMP

case "$COMP" in
    1) THRESHOLD=0 ;;
    3) THRESHOLD=5 ;;
    *) THRESHOLD=2 ;;
esac

read -p "¿FPS? (default: 10): " FPS_INPUT
FPS=${FPS_INPUT:-10}

echo ""
echo "Generando con: --pic18 --threshold $THRESHOLD --fps $FPS"
echo "─────────────────────────────────────────────"

python3 "$CONVERTER" \
    --frames "$FRAMES" \
    $GAPS \
    --pic18 \
    --threshold "$THRESHOLD" \
    --fps "$FPS" \
    --output "$OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Archivo generado: $OUTPUT"
    echo "   Cópialo junto a badapple_pic.c y compila con CCS C v5."
    echo "   Asegúrate de tener: #define USE_PIC18"
fi
