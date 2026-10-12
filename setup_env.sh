#!/usr/bin/env bash
# ============================================================
#  setup_env.sh - Crear entorno virtual para Bad Apple PIC Port
#  100% libre de sudo / root - Todo local en .venv
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "============================================================"
echo "  Configuración de entorno virtual Python (.venv)"
echo "============================================================"

# Verificar python3
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 no está instalado en el sistema."
    exit 1
fi

# Crear .venv si no existe
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/3] Creando entorno virtual en $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "[1/3] El entorno virtual ya existe en $VENV_DIR"
fi

# Instalar o verificar dependencias
echo "[2/3] Instalando dependencias (Pillow, opencv-python-headless, numpy)..."
"$VENV_DIR/bin/pip" install --quiet Pillow opencv-python-headless numpy

# Verificación final
echo "[3/3] Verificando instalación..."
"$VENV_DIR/bin/python3" -c "
import PIL
import cv2
import numpy
print(f'  ✓ Pillow:  {PIL.__version__}')
print(f'  ✓ OpenCV:  {cv2.__version__}')
print(f'  ✓ NumPy:   {numpy.__version__}')
"

echo "============================================================"
echo "✅ Entorno virtual listo en: $VENV_DIR"
echo "   Para activarlo manualmente si lo deseas:"
echo "     source $VENV_DIR/bin/activate"
echo "   (Los scripts detectan y usan .venv automáticamente)"
echo "============================================================"
