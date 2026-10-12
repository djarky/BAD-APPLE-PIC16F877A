#!/usr/bin/env bash
#!/usr/bin/env python3
"""
video2pic.py - Convierte directamente el video original de Bad Apple a datos para PIC16/PIC18
Lee el archivo MP4/video con OpenCV, redimensiona a 20x16, binariza y aplica delta encoding.
Genera frame_data.h compatible con CCS C Compiler v5.

Uso:
  python3 video2pic.py --video "../badapple/img2lcdino-main/東方Bad Apple!! ＰＶ影絵.mp4" --pic18 --fps 10
  python3 video2pic.py --video "../badapple/img2lcdino-main/東方Bad Apple!! ＰＶ影絵.mp4" --pic16 --fps 6
"""

import cv2
import argparse
import sys
import os

# Importar funciones de compresión y generación de headers desde img2pic
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from img2pic import (
    PIC16_FLASH_AVAILABLE,
    PIC18_FLASH_AVAILABLE,
    compare_chars,
    generate_ccs_header,
    print_multi_part_summary
)


def frame_to_lcd_chars(binary_matrix):
    """
    Convierte una matriz 20x16 (20 col x 16 fil) a 8 custom chars (5x8 cada uno).
    Distribución en LCD 16x2:
      Fila 0: Chars 0, 1, 2, 3
      Fila 1: Chars 4, 5, 6, 7
    """
    def extract_rect(m, x1, x2, y1, y2):
        rows = []
        for y in range(y1, y2):
            val = 0
            for x in range(x1, x2):
                val <<= 1
                if y < len(m) and x < len(m[y]):
                    val |= (1 if m[y][x] else 0)
            rows.append(val & 0x1F)
        return rows

    return [
        extract_rect(binary_matrix, 0,  5,  0, 8),   # Char 0
        extract_rect(binary_matrix, 5,  10, 0, 8),   # Char 1
        extract_rect(binary_matrix, 10, 15, 0, 8),   # Char 2
        extract_rect(binary_matrix, 15, 20, 0, 8),   # Char 3
        extract_rect(binary_matrix, 0,  5,  8, 16),  # Char 4
        extract_rect(binary_matrix, 5,  10, 8, 16),  # Char 5
        extract_rect(binary_matrix, 10, 15, 8, 16),  # Char 6
        extract_rect(binary_matrix, 15, 20, 8, 16),  # Char 7
    ]


def process_video(
    video_path,
    target_fps=10,
    bin_threshold=127,
    diff_threshold=2,
    max_bytes=None,
    max_frames=None,
    start_sec=0.0,
    duration=None,
    save_frames_dir=None,
    split=True
):
    """Procesa el video leyendo fotogramas y dividiendo en partes si supera max_bytes."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: No se pudo abrir el archivo de video: {video_path}", file=sys.stderr)
        sys.exit(1)

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_native_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_native_frames / native_fps if native_fps > 0 else 0

    print(f"Video abierto: {video_path}", file=sys.stderr)
    print(f"  FPS nativo: {native_fps:.2f} | Frames totales: {total_native_frames} | Duración: {video_duration:.1f}s", file=sys.stderr)
    print(f"  Muestreo objetivo: {target_fps} FPS | Binarización: {bin_threshold} | Diff threshold: {diff_threshold}", file=sys.stderr)
    print(f"  División en partes (multi-part): {'Desactivada' if not split else 'Activada'}", file=sys.stderr)

    if save_frames_dir:
        os.makedirs(save_frames_dir, exist_ok=True)
        print(f"  Guardando frames PNG en: {save_frames_dir}", file=sys.stderr)

    start_frame = int(start_sec * native_fps)
    if start_frame > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    frame_interval = native_fps / target_fps
    next_sample_time = start_frame

    parts = []
    current_data = bytearray()
    prev_frame = None
    part_start_frame = 1
    part_frames = 0
    part_total_chars = 0
    part_changed_chars = 0
    current_native_idx = start_frame
    global_frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_native_idx += 1

        if duration and ((current_native_idx - start_frame) / native_fps) > duration:
            break

        # Muestreo al FPS indicado
        if current_native_idx < next_sample_time:
            continue

        next_sample_time += frame_interval

        if max_frames is not None and global_frame_count >= max_frames:
            break

        # 1. Escala de grises y redimensionado a 20x16
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (20, 16), interpolation=cv2.INTER_AREA)

        # 2. Binarizar (0 o 1)
        _, binary = cv2.threshold(resized, bin_threshold, 255, cv2.THRESH_BINARY)
        binary_matrix = (binary > 127).astype(int)

        if save_frames_dir:
            cv2.imwrite(os.path.join(save_frames_dir, f"frame_{global_frame_count+1:04d}.png"), binary)

        # 3. Extraer 8 custom chars
        lcd_frame = frame_to_lcd_chars(binary_matrix)

        # 4. Delta encoding (o keyframe si inicia parte)
        if prev_frame is None:
            frame_bytes = bytearray([0xFF])
            for ci in range(8):
                for rb in lcd_frame[ci]:
                    frame_bytes.append(rb)
            frame_changed = 8
        else:
            bitmask = 0x00
            char_data = bytearray()
            frame_changed = 0
            for ci in range(8):
                if compare_chars(lcd_frame[ci], prev_frame[ci], diff_threshold):
                    bitmask |= (1 << ci)
                    frame_changed += 1
                    for rb in lcd_frame[ci]:
                        char_data.append(rb)
            frame_bytes = bytearray([bitmask])
            frame_bytes.extend(char_data)

        # 5. Comprobar límite de memoria flash para la parte actual
        if max_bytes is not None and (len(current_data) + len(frame_bytes)) > max_bytes and part_frames > 0:
            if not split:
                print(f"  INFO: Límite de flash alcanzado ({max_bytes} bytes) en frame {part_frames} (sin split)", file=sys.stderr)
                break

            stats = {
                'total_chars': part_total_chars,
                'changed_chars': part_changed_chars,
                'compression_pct': 100.0 * part_changed_chars / part_total_chars if part_total_chars > 0 else 0,
                'data_size': len(current_data),
            }
            parts.append({
                'data': bytes(current_data),
                'num_frames': part_frames,
                'stats': stats,
                'start_frame': part_start_frame,
                'end_frame': part_start_frame + part_frames - 1,
            })

            # Iniciar nueva parte
            current_data = bytearray()
            part_start_frame = global_frame_count + 1
            part_frames = 0
            part_total_chars = 0
            part_changed_chars = 0
            prev_frame = None

            # Recalcular fotograma como KEYFRAME de la nueva parte
            frame_bytes = bytearray([0xFF])
            for ci in range(8):
                for rb in lcd_frame[ci]:
                    frame_bytes.append(rb)
            frame_changed = 8

        current_data.extend(frame_bytes)
        part_changed_chars += frame_changed
        part_total_chars += 8
        prev_frame = lcd_frame
        part_frames += 1
        global_frame_count += 1

        if global_frame_count % 100 == 0:
            print(f"  Procesados {global_frame_count} frames del video...", file=sys.stderr)

    cap.release()

    if part_frames > 0:
        stats = {
            'total_chars': part_total_chars,
            'changed_chars': part_changed_chars,
            'compression_pct': 100.0 * part_changed_chars / part_total_chars if part_total_chars > 0 else 0,
            'data_size': len(current_data),
        }
        parts.append({
            'data': bytes(current_data),
            'num_frames': part_frames,
            'stats': stats,
            'start_frame': part_start_frame,
            'end_frame': part_start_frame + part_frames - 1,
        })

    return parts


def main():
    parser = argparse.ArgumentParser(
        description='Convierte video MP4 de Bad Apple a datos para PIC (CCS C v5)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--video', default='../badapple/img2lcdino-main/東方Bad Apple!! ＰＶ影絵.mp4',
                        help='Ruta al video MP4 original')
    parser.add_argument('--output', default='frame_data.h',
                        help='Archivo de salida .h (default: frame_data.h)')
    parser.add_argument('--fps', type=int, default=10,
                        help='FPS objetivo de muestreo (default: 10)')
    parser.add_argument('--threshold', type=int, default=2,
                        help='Umbral de tolerancia de cambio de píxeles (default: 2)')
    parser.add_argument('--binarize-threshold', type=int, default=127,
                        help='Umbral de binarización blanco/negro (0-255, default: 127)')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='Máximo de frames a convertir')
    parser.add_argument('--start-sec', type=float, default=0.0,
                        help='Segundo de inicio del video (default: 0.0)')
    parser.add_argument('--duration', type=float, default=None,
                        help='Duración máxima en segundos a procesar')
    parser.add_argument('--save-frames', default=None,
                        help='Directorio opcional donde exportar los frames PNG 20x16')
    parser.add_argument('--no-split', action='store_true',
                        help='No dividir en partes (detenerse al primer límite de flash)')

    pic_group = parser.add_mutually_exclusive_group()
    pic_group.add_argument('--pic16', action='store_true',
                           help='Limitar al flash del PIC16F877A (~4.5 KB)')
    pic_group.add_argument('--pic18', action='store_true',
                           help='Limitar al flash del PIC18F4550 (~28 KB)')

    args = parser.parse_args()

    video_path = args.video
    if not os.path.isabs(video_path) and not os.path.exists(video_path):
        candidate = os.path.join(SCRIPT_DIR, video_path)
        if os.path.exists(candidate):
            video_path = candidate

    if not os.path.exists(video_path):
        print(f"ERROR: No se encontró el video en '{video_path}'", file=sys.stderr)
        sys.exit(1)

    max_bytes = None
    if args.pic16:
        max_bytes = PIC16_FLASH_AVAILABLE
        print(f"Modo: PIC16F877A (límite {PIC16_FLASH_AVAILABLE} bytes por parte)", file=sys.stderr)
    elif args.pic18:
        max_bytes = PIC18_FLASH_AVAILABLE
        print(f"Modo: PIC18F4550 (límite {PIC18_FLASH_AVAILABLE} bytes por parte)", file=sys.stderr)

    parts = process_video(
        video_path=video_path,
        target_fps=args.fps,
        bin_threshold=args.binarize_threshold,
        diff_threshold=args.threshold,
        max_bytes=max_bytes,
        max_frames=args.max_frames,
        start_sec=args.start_sec,
        duration=args.duration,
        save_frames_dir=args.save_frames,
        split=(not args.no_split)
    )

    if not parts:
        print("ERROR: No se generó ninguna parte de datos.", file=sys.stderr)
        sys.exit(1)

    out_dir = os.path.dirname(args.output) or '.'
    base_name = os.path.basename(args.output)
    stem, ext = os.path.splitext(base_name)
    total_parts = len(parts)

    for idx, p in enumerate(parts):
        part_num = idx + 1
        if total_parts == 1:
            part_file = os.path.join(out_dir, f"{stem}{ext}")
            generate_ccs_header(p['data'], p['num_frames'], p['stats'], args.fps, part_file, 1, 1, p['start_frame'], p['end_frame'])
        else:
            if part_num == 1:
                part_file_main = os.path.join(out_dir, f"{stem}{ext}")
                part_file_num = os.path.join(out_dir, f"{stem}1{ext}")
                generate_ccs_header(p['data'], p['num_frames'], p['stats'], args.fps, part_file_main, part_num, total_parts, p['start_frame'], p['end_frame'])
                generate_ccs_header(p['data'], p['num_frames'], p['stats'], args.fps, part_file_num, part_num, total_parts, p['start_frame'], p['end_frame'])
            else:
                part_file = os.path.join(out_dir, f"{stem}{part_num}{ext}")
                generate_ccs_header(p['data'], p['num_frames'], p['stats'], args.fps, part_file, part_num, total_parts, p['start_frame'], p['end_frame'])

    print_multi_part_summary(parts, args.fps)
    print(f"✅ Generadas {total_parts} partes listas para compilar.", file=sys.stderr)


if __name__ == '__main__':
    main()
