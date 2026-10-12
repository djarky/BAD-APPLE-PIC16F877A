#!/usr/bin/env bash
# ============================================================
#  gen_pic18.sh - Genera frame_data.h para PIC18F4550
#  Usa el set de frames (20x16) de frames/ (o pngs/)
#  Flash disponible: ~28 KB (hasta 1000 frames en 1 parte)
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

echo "╔══════════════════════════════════════════╗"
echo "║  Generador de frames para PIC18F4550     ║"
echo "║  Set de frames (20x16, sin gaps)         ║"
echo "║  Flash disponible: ~28 KB por parte      ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Carpeta origen:    $FRAMES_DIR"
echo "Frames detectados: ${#files[@]}"
echo ""
echo "Configuración de compresión:"
echo "  [1] Lossless   (threshold=0) - Calidad perfecta (~790 frames máx en 1 parte)"
echo "  [2] Suave      (threshold=2) - 1000 frames COMPLETOS en flash ← RECOMENDADO"
echo "  [3] Agresiva   (threshold=4) - 1000 frames, aún más espacio libre"
echo ""
read -p "¿Nivel de compresión? [1/2/3] (default: 2): " COMP

case "$COMP" in
    1) THRESHOLD=0 ;;
    3) THRESHOLD=4 ;;
    *) THRESHOLD=2 ;;
esac

read -p "¿FPS? (default: 10): " FPS_INPUT
FPS=${FPS_INPUT:-10}

echo ""
echo "Generando con: --pic18 --threshold $THRESHOLD --fps $FPS"
echo "Python: $PYTHON"
echo "─────────────────────────────────────────────"

"$PYTHON" "$CONVERTER" \
    --frames "$FRAMES_DIR/*.png" \
    --no-gaps \
    --pic18 \
    --threshold "$THRESHOLD" \
    --fps "$FPS" \
    --output "$OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Conversión completa lista para CCS C v5."
    echo "   Archivo generado: $OUTPUT"
    echo "   Abre badapple_pic.c y asegúrate de tener: #define USE_PIC18"
fi
