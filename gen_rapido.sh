#!/usr/bin/env bash
# ============================================================
#  gen_rapido.sh - Generación rápida sin preguntas
#  Usa el set de frames de frames/ (o pngs/)
# ============================================================
#
#  Uso:
#    ./gen_rapido.sh pic16          # PIC16F877A, 6fps, threshold=3
#    ./gen_rapido.sh pic18          # PIC18F4550, 10fps, threshold=2
#    ./gen_rapido.sh pic16 8 3      # PIC16, 8fps, threshold=3
#    ./gen_rapido.sh pic18 12 0     # PIC18, 12fps, lossless
#
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONVERTER="$SCRIPT_DIR/img2pic.py"
OUTPUT="$SCRIPT_DIR/frame_data.h"

# 1. Detectar Python con entorno virtual (.venv)
if [ -x "$SCRIPT_DIR/.venv/bin/python3" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python3"
elif [ -x "$SCRIPT_DIR/../.venv/bin/python3" ]; then
    PYTHON="$SCRIPT_DIR/../.venv/bin/python3"
elif [ -n "$VIRTUAL_ENV" ] && command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "ERROR: No se encontró Python 3 ni el entorno virtual .venv."
    echo "Ejecuta ./setup_env.sh para crearlo automáticamente sin sudo."
    exit 1
fi

# 2. Selección de carpeta de frames (prioridad a ./frames local)
FRAMES_DIR="$SCRIPT_DIR/frames"
shopt -s nullglob
files=("$FRAMES_DIR/"*.png)
shopt -u nullglob

if [ ${#files[@]} -eq 0 ]; then
    FRAMES_DIR="$SCRIPT_DIR/../Bad-Apple-On-Arduino-LCD-main/pngs"
    shopt -s nullglob
    files=("$FRAMES_DIR/"*.png)
    shopt -u nullglob
fi

if [ ${#files[@]} -eq 0 ]; then
    echo "ERROR: No se encontraron frames en $SCRIPT_DIR/frames ni en ../Bad-Apple-On-Arduino-LCD-main/pngs"
    echo "Ejecuta ./gen_video.sh para extraerlos desde el video MP4."
    exit 1
fi

# Parámetros
PIC="${1:-pic18}"
case "$PIC" in
    pic16|PIC16|16)
        TARGET="--pic16"
        FPS="${2:-6}"
        TH="${3:-3}"
        NAME="PIC16F877A"
        ;;
    *)
        TARGET="--pic18"
        FPS="${2:-10}"
        TH="${3:-2}"
        NAME="PIC18F4550"
        ;;
esac

echo "Generando frames para $NAME ($FPS FPS, threshold=$TH) desde $FRAMES_DIR (${#files[@]} frames)..."

"$PYTHON" "$CONVERTER" \
    --frames "$FRAMES_DIR/*.png" \
    --no-gaps \
    $TARGET \
    --threshold "$TH" \
    --fps "$FPS" \
    --output "$OUTPUT"

echo "✅ Listo: $OUTPUT"
