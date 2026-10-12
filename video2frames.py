#!/usr/bin/env python3
"""
video2frames.py - Extrae fotogramas de un video MP4 a la carpeta de frames (PNG 20x16)
Optimizado para Bad Apple en LCD 16x2 para microcontroladores PIC.

Convierte los fotogramas del video a imágenes binarias (20x16 blanco y negro)
y las guarda en la carpeta destino (por defecto 'frames/').
"""

import cv2
import argparse
import sys
import os
import glob
import shutil


def find_default_video(search_dir):
    """Busca automáticamente un archivo .mp4 en la carpeta indicada."""
    # Prioridad 1: Archivo con 'Bad Apple' en el nombre
    candidates = glob.glob(os.path.join(search_dir, "*Bad Apple*.mp4"))
    if candidates:
        return candidates[0]

    # Prioridad 2: Cualquier archivo .mp4 en la carpeta
    candidates = glob.glob(os.path.join(search_dir, "*.mp4"))
    if candidates:
        return candidates[0]

    return None


def extract_frames(
    video_path,
    output_dir,
    target_fps=10,
    width=20,
    height=16,
    threshold=127,
    max_frames=None,
    clean=True
):
    """Extrae fotogramas del video, redimensiona a 20x16, binariza y guarda en output_dir."""
    if not os.path.isfile(video_path):
        print(f"ERROR: No se encontró el archivo de video: {video_path}", file=sys.stderr)
        return False

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: OpenCV no pudo abrir el video: {video_path}", file=sys.stderr)
        return False

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_native_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_native_frames / native_fps if native_fps > 0 else 0

    print("═══════════════════════════════════════════════════════════")
    print(f"  Extrayendo frames desde video: {os.path.basename(video_path)}")
    print("═══════════════════════════════════════════════════════════")
    print(f"  FPS nativo del video:   {native_fps:.2f}")
    print(f"  Frames nativos totales: {total_native_frames}")
    print(f"  Duración del video:     {video_duration:.1f} segundos")
    print(f"  FPS de muestreo:        {target_fps if target_fps > 0 else native_fps} FPS")
    print(f"  Resolución de salida:   {width}x{height} píxeles (LCD 16x2)")
    print(f"  Umbral de binarizado:   {threshold}")
    print(f"  Límite de frames:       {'Sin límite (todo el video)' if max_frames is None else max_frames}")
    print(f"  Carpeta de salida:      {output_dir}")
    print("───────────────────────────────────────────────────────────")

    if clean and os.path.exists(output_dir):
        # Limpiar PNGs anteriores
        png_count = len(glob.glob(os.path.join(output_dir, "*.png")))
        if png_count > 0:
            print(f"  Limpiando {png_count} frames antiguos en {output_dir}...")
            for f in glob.glob(os.path.join(output_dir, "*.png")):
                try:
                    os.remove(f)
                except OSError:
                    pass

    os.makedirs(output_dir, exist_ok=True)

    frame_interval = (native_fps / target_fps) if (target_fps > 0 and target_fps < native_fps) else 1.0
    next_sample_frame = 0.0
    current_native_idx = 0
    extracted_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if current_native_idx >= next_sample_frame:
            # 1. Convertir a escala de grises
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 2. Redimensionar a resolución de LCD (20x16)
            resized = cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)

            # 3. Binarizar en blanco y negro puro
            _, binary = cv2.threshold(resized, threshold, 255, cv2.THRESH_BINARY)

            # 4. Guardar archivo PNG
            extracted_count += 1
            filename = f"frame_{extracted_count:04d}.png"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, binary)

            next_sample_frame += frame_interval

            if extracted_count % 100 == 0:
                print(f"  -> {extracted_count} frames guardados...", file=sys.stderr)

            if max_frames is not None and extracted_count >= max_frames:
                print(f"  -> Límite alcanzado ({max_frames} frames).", file=sys.stderr)
                break

        current_native_idx += 1

    cap.release()

    duration_sampled = extracted_count / (target_fps if target_fps > 0 else native_fps)
    print("───────────────────────────────────────────────────────────")
    print(f"✅ ¡Extracción completada con éxito!")
    print(f"   Frames generados: {extracted_count}")
    print(f"   Duración cubierta: {duration_sampled:.1f} segundos a {target_fps} FPS")
    print(f"   Ubicación:        {output_dir}/")
    print("═══════════════════════════════════════════════════════════")
    print("Siguientes pasos recomendados:")
    print("  1. Para PIC18F4550: ejecuta ./gen_pic18.sh")
    print("  2. Para PIC16F877A: ejecuta ./gen_pic16.sh")
    print("  3. O generación rápida: ./gen_rapido.sh pic18")
    return True


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(
        description='Extrae frames de un video MP4 a la carpeta frames/ (PNG 20x16 binarizados)'
    )
    parser.add_argument('--video', default=None,
                        help='Ruta al archivo MP4 (por defecto busca en la misma carpeta)')
    parser.add_argument('--output-dir', default=os.path.join(script_dir, 'frames'),
                        help='Carpeta de salida para los frames PNG (default: ./frames)')
    parser.add_argument('--fps', type=int, default=10,
                        help='FPS de muestreo (default: 10 FPS)')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='Máximo de frames a extraer (default: todos)')
    parser.add_argument('--threshold', type=int, default=127,
                        help='Umbral de binarizado 0-255 (default: 127)')
    parser.add_argument('--no-clean', action='store_true',
                        help='No borrar frames anteriores en la carpeta de salida')

    args = parser.parse_args()

    video_path = args.video
    if not video_path:
        video_path = find_default_video(script_dir)

    if not video_path or not os.path.exists(video_path):
        print("ERROR: No se encontró ningún video .mp4 en la carpeta.", file=sys.stderr)
        print("Copia tu video MP4 en esta carpeta o indica la ruta con --video /ruta/video.mp4", file=sys.stderr)
        sys.exit(1)

    success = extract_frames(
        video_path=video_path,
        output_dir=args.output_dir,
        target_fps=args.fps,
        threshold=args.threshold,
        max_frames=args.max_frames,
        clean=not args.no_clean
    )

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
