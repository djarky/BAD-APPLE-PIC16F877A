#!/bin/bash
# ============================================================
#  gen_rapido.sh - Generación rápida sin preguntas
#  Usa valores por defecto razonables para cada PIC
# ============================================================
#
#  Uso:
#    ./gen_rapido.sh pic16          # PIC16F877A, 6fps, threshold=3
#    ./gen_rapido.sh pic18          # PIC18F4550, 10fps, threshold=2
#    ./gen_rapido.sh pic16 8 5      # PIC16, 8fps, threshold=5
#    ./gen_rapido.sh pic18 12 0     # PIC18, 12fps, lossless
#
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONVERTER="$SCRIPT_DIR/img2pic.py"
OUTPUT="$SCRIPT_DIR/frame_data.h"

shopt -s nullglob
files_1000=("$SCRIPT_DIR/../Bad-Apple-On-Arduino-LCD-main/pngs/"*.png)
files_76=("$SCRIPT_DIR/../badapple/img2lcdino-main/frames/"*.png)
shopt -u nullglob

if [ ${#files_1000[@]} -gt 0 ]; then
    FRAMES="$SCRIPT_DIR/../Bad-Apple-On-Arduino-LCD-main/pngs/*.png"
    GAPS="--no-gaps"
    echo "Usando 1000 frames (20x16)"
elif [ ${#files_76[@]} -gt 0 ]; then
    FRAMES="$SCRIPT_DIR/../badapple/img2lcdino-main/frames/*.png"
    GAPS=""
    echo "Usando 76 frames (24x18)"
else
    echo "ERROR: No se encontraron frames PNG."
    exit 1
fi

# Parámetros
PIC="${1:-pic18}"
case "$PIC" in
    pic16|PIC16|16)
        PIC_FLAG="--pic16"
        DEFAULT_FPS=6
        DEFAULT_THRESHOLD=3
        echo "Target: PIC16F877A (~6KB)"
        ;;
    pic18|PIC18|18)
        PIC_FLAG="--pic18"
        DEFAULT_FPS=10
        DEFAULT_THRESHOLD=2
        echo "Target: PIC18F4550 (~28KB)"
        ;;
    *)
        echo "Uso: $0 [pic16|pic18] [fps] [threshold]"
        echo ""
        echo "Ejemplos:"
        echo "  $0 pic16          # PIC16, 6fps, threshold=3"
        echo "  $0 pic18          # PIC18, 10fps, threshold=2"
        echo "  $0 pic16 8 5      # PIC16, 8fps, threshold=5"
        echo "  $0 pic18 12 0     # PIC18, 12fps, lossless"
        exit 1
        ;;
esac

FPS="${2:-$DEFAULT_FPS}"
THRESHOLD="${3:-$DEFAULT_THRESHOLD}"

echo "FPS: $FPS | Threshold: $THRESHOLD"
echo "─────────────────────────────────────────"

python3 "$CONVERTER" \
    --frames "$FRAMES" \
    $GAPS \
    $PIC_FLAG \
    --threshold "$THRESHOLD" \
    --fps "$FPS" \
    --output "$OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Listo! → $OUTPUT"
fi
