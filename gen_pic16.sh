#!/usr/bin/env bash
# ============================================================
#  gen_pic16.sh - Genera frame_data.h para PIC16F877A
#  Usa el set de frames (20x16) de frames/ (o pngs/)
#  Flash disponible: ~4.5 KB (genera partes frame_data.h, frame_data2.h...)
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
echo "║  Generador de frames para PIC16F877A     ║"
echo "║  Set de frames (20x16, sin gaps)         ║"
echo "║  Flash disponible: ~4.5 KB por parte     ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Carpeta origen:    $FRAMES_DIR"
echo "Frames detectados: ${#files[@]}"
echo "Nota: El script genera automáticamente múltiples partes si los frames"
echo "      superan la memoria Flash del PIC16F877A (frame_data.h, frame_data2.h...)."
echo ""
echo "Configuración de compresión:"
echo "  [1] Lossless (threshold=0) - Calidad perfecta, ~140-170 frames/parte"
echo "  [2] Suave    (threshold=2) - Pérdida casi imperceptible, ~250-300 frames/parte"
echo "  [3] Agresiva (threshold=3) - Máxima duración, ~350-400+ frames/parte ← RECOMENDADO"
echo ""
read -p "¿Nivel de compresión? [1/2/3] (default: 3): " COMP

case "$COMP" in
    1) THRESHOLD=0 ;;
    2) THRESHOLD=2 ;;
    *) THRESHOLD=3 ;;
esac

read -p "¿FPS? (default: 6): " FPS_INPUT
FPS=${FPS_INPUT:-6}

echo ""
echo "Generando con: --pic16 --threshold $THRESHOLD --fps $FPS"
echo "Python: $PYTHON"
echo "─────────────────────────────────────────────"

"$PYTHON" "$CONVERTER" \
    --frames "$FRAMES_DIR/*.png" \
    --no-gaps \
    --pic16 \
    --threshold "$THRESHOLD" \
    --fps "$FPS" \
    --output "$OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Conversión completa lista para CCS C v5."
    echo "   Si se generaron varias partes (frame_data.h, frame_data2.h, frame_data3.h...):"
    echo "   En badapple_pic.c cambia #define USE_PART 1 (o 2, 3...) para elegir qué parte compilar."
fi
