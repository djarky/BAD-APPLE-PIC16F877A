#!/usr/bin/env bash
# ============================================================
#  gen_video.sh - Extrae frames del video MP4 a la carpeta frames/
#  Busca el video directamente en esta misma carpeta (pic_port/)
#  y guarda los fotogramas en formato PNG 20x16 binarizados.
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTRACTOR="$SCRIPT_DIR/video2frames.py"
OUTPUT_FRAMES_DIR="$SCRIPT_DIR/frames"

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

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      Extracción de Frames desde Video MP4 a frames/      ║"
echo "║      Bad Apple en LCD 16x2 para PIC (CCS C Compiler)     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 2. Búsqueda automática de video en la misma carpeta
shopt -s nullglob
mp4_files=("$SCRIPT_DIR/"*.mp4)
shopt -u nullglob

VIDEO_INPUT=""
if [ -n "$1" ] && [ -f "$1" ]; then
    VIDEO_INPUT="$1"
elif [ -f "$SCRIPT_DIR/東方Bad Apple!! ＰＶ影絵.mp4" ]; then
    VIDEO_INPUT="$SCRIPT_DIR/東方Bad Apple!! ＰＶ影絵.mp4"
elif [ ${#mp4_files[@]} -gt 0 ]; then
    VIDEO_INPUT="${mp4_files[0]}"
elif [ -f "$SCRIPT_DIR/../badapple/img2lcdino-main/東方Bad Apple!! ＰＶ影絵.mp4" ]; then
    VIDEO_INPUT="$SCRIPT_DIR/../badapple/img2lcdino-main/東方Bad Apple!! ＰＶ影絵.mp4"
fi

if [ -z "$VIDEO_INPUT" ] || [ ! -f "$VIDEO_INPUT" ]; then
    echo "ERROR: No se encontró ningún video .mp4 en la carpeta:"
    echo "  $SCRIPT_DIR"
    echo ""
    echo "Por favor copia tu video MP4 en esta carpeta o pásalo como argumento:"
    echo "  $0 /ruta/al/video.mp4"
    exit 1
fi

echo "Video detectado en la carpeta:"
echo "  📄 $(basename "$VIDEO_INPUT")"
echo "  📁 $VIDEO_INPUT"
echo ""

# 3. Opciones de extracción
echo "Configuración de extracción a la carpeta 'frames/':"
echo "  1) 1000 frames a 10 FPS (Recomendado para PIC18 / set estándar)"
echo "  2) 1000 frames a 6 FPS  (Recomendado para PIC16)"
echo "  3) Todo el video completo a 10 FPS (~2190 frames)"
echo "  4) Personalizado"
echo ""
read -p "¿Opción? [1/2/3/4] (default: 1): " OPT_CHOICE

case "$OPT_CHOICE" in
    2)
        FPS=6
        MAX_FRAMES_ARG="--max-frames 1000"
        ;;
    3)
        FPS=10
        MAX_FRAMES_ARG=""
        ;;
    4)
        read -p "¿FPS de muestreo? (default: 10): " CUSTOM_FPS
        FPS=${CUSTOM_FPS:-10}
        read -p "¿Máximo de frames? (deja vacío para todo el video, o ej. 1000): " CUSTOM_MAX
        if [ -n "$CUSTOM_MAX" ]; then
            MAX_FRAMES_ARG="--max-frames $CUSTOM_MAX"
        else
            MAX_FRAMES_ARG=""
        fi
        ;;
    *)
        FPS=10
        MAX_FRAMES_ARG="--max-frames 1000"
        ;;
esac

echo ""
echo "Iniciando extracción de frames..."
echo "  Video:   $(basename "$VIDEO_INPUT")"
echo "  Destino: $OUTPUT_FRAMES_DIR/"
echo "  FPS:     $FPS"
echo "  Python:  $PYTHON"
echo "──────────────────────────────────────────────────────────"

"$PYTHON" "$EXTRACTOR" \
    --video "$VIDEO_INPUT" \
    --output-dir "$OUTPUT_FRAMES_DIR" \
    --fps "$FPS" \
    $MAX_FRAMES_ARG

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ¡Listo! Los frames se extrajeron correctamente a: $OUTPUT_FRAMES_DIR"
    echo ""
    echo "Para generar el archivo frame_data.h para tu microcontrolador:"
    echo "  👉 PIC18F4550 : ./gen_pic18.sh"
    echo "  👉 PIC16F877A : ./gen_pic16.sh"
    echo "  👉 Rápido     : ./gen_rapido.sh pic18 (o pic16)"
fi
