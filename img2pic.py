#!/usr/bin/env python3
"""
img2pic.py - Convierte frames de Bad Apple a datos comprimidos para PIC16F877A / PIC18F4550
Genera un .h con array 'rom const' compatible con CCS C Compiler v5.

Basado en img2lcdino de arduinocelentano (GPLv3)

Formato de datos comprimidos (delta encoding):
  Para cada frame:
    1 byte  = bitmask (bits 0-7 indican cuáles de los 8 chars cambiaron)
    N * 8 bytes = datos de los chars que cambiaron (N = bits activos)

Ejemplos:
  # Modo estándar (compatible PIC16 y PIC18, pocos frames):
  python3 img2pic.py --frames "frames/*.png" --pic16 --output frame_data.h

  # Modo PIC18 (máximo de frames):
  python3 img2pic.py --frames "pngs/*.png" --no-gaps --pic18 --fps 10 --output frame_data.h

  # Limitar frames manualmente:
  python3 img2pic.py --frames "pngs/*.png" --no-gaps --max-frames 200 --output frame_data.h

  # Compresión con pérdida para meter más frames:
  python3 img2pic.py --frames "pngs/*.png" --no-gaps --pic16 --threshold 5 --output frame_data.h

Requiere: Pillow (PIL)  ->  pip install Pillow
"""

from PIL import Image
import argparse
import sys
import re
from glob import glob


def natural_sort_key(s):
    """Ordenamiento natural (numérico) para ordenar correctamente secuencias como png (1)..png (1000)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


# ============================================================
#  Límites de memoria (ajustados para dejar espacio a main + driver LCD)
# ============================================================
# PIC16F877A: 8192 words totales en 4 páginas de 2048 words.
# Descontando código (~1.5K words) y fragmentación: ~4.5 KB (4608 bytes)
PIC16_FLASH_AVAILABLE = 4608
PIC18_FLASH_AVAILABLE = 28672   # PIC18F4550: ~28 KB para datos


def load_and_binarize(filepath, threshold=127):
    """Carga una imagen y la convierte a matriz binaria (0=negro, 1=blanco)."""
    img = Image.open(filepath).convert('L')
    pixels = img.load()
    width, height = img.size

    matrix = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append(1 if pixels[x, y] > threshold else 0)
        matrix.append(row)

    return matrix, width, height


def extract_rect(matrix, x1, y1, x2, y2):
    """
    Extrae un rectángulo de la matriz y lo convierte a lista de 8 bytes.
    Cada byte = 1 fila del custom char LCD (5 bits bajos).
    """
    rows = []
    for y in range(y1, y2):
        val = 0
        for x in range(x1, x2):
            val <<= 1
            if y < len(matrix) and x < len(matrix[y]):
                val |= matrix[y][x]
        rows.append(val & 0x1F)
    return rows


def img2frame(matrix, width, height, use_gaps=True):
    """
    Convierte una imagen binarizada a 8 custom characters del LCD 16x2.

    Con gaps (24x18): columnas [0-4][6-10][12-16][18-22], filas [0-7][9-16]
    Sin gaps (20x16): columnas [0-4][5-9][10-14][15-19], filas [0-7][8-15]
    """
    if use_gaps:
        if height < 17 or width < 23:
            return None
        frame = [
            extract_rect(matrix, 0,  0,  5,  8),
            extract_rect(matrix, 6,  0,  11, 8),
            extract_rect(matrix, 12, 0,  17, 8),
            extract_rect(matrix, 18, 0,  23, 8),
            extract_rect(matrix, 0,  9,  5,  17),
            extract_rect(matrix, 6,  9,  11, 17),
            extract_rect(matrix, 12, 9,  17, 17),
            extract_rect(matrix, 18, 9,  23, 17),
        ]
    else:
        if height < 16 or width < 20:
            return None
        frame = [
            extract_rect(matrix, 0,  0,  5,  8),
            extract_rect(matrix, 5,  0,  10, 8),
            extract_rect(matrix, 10, 0,  15, 8),
            extract_rect(matrix, 15, 0,  20, 8),
            extract_rect(matrix, 0,  8,  5,  16),
            extract_rect(matrix, 5,  8,  10, 16),
            extract_rect(matrix, 10, 8,  15, 16),
            extract_rect(matrix, 15, 8,  20, 16),
        ]
    return frame


def compare_chars(c1, c2, threshold=0):
    """Compara dos chars. Retorna True si difieren más que el umbral."""
    diff = 0
    for i in range(len(c1)):
        xor = c1[i] ^ c2[i]
        diff += bin(xor).count('1')
    return diff > threshold


import os


def process_frames(file_list, use_gaps=True, threshold=0, max_frames=None, max_bytes=None, split=True):
    """
    Procesa frames con delta encoding.
    Si split=True y max_bytes está definido, divide la secuencia en múltiples partes
    de modo que cada parte quepa holgadamente dentro de max_bytes.
    Cada parte inicia con un keyframe (bitmask 0xFF, todos los 8 chars actualizados).

    Retorna una lista de partes: [ { 'data': bytes, 'num_frames': int, 'stats': dict, 'start_frame': int, 'end_frame': int }, ... ]
    """
    sorted_files = sorted(file_list, key=natural_sort_key)
    if max_frames is not None:
        sorted_files = sorted_files[:max_frames]

    parts = []
    current_data = bytearray()
    prev_frame = None
    part_start_idx = 0
    part_frames = 0
    part_total_chars = 0
    part_changed_chars = 0

    for i, fn in enumerate(sorted_files):
        matrix, width, height = load_and_binarize(fn)
        frame = img2frame(matrix, width, height, use_gaps)

        if frame is None:
            print(f"  WARN: Imagen inválida: {fn}, saltando...", file=sys.stderr)
            continue

        # Primer frame de la parte: KEYFRAME (bitmask 0xFF, todos los chars)
        if prev_frame is None:
            frame_bytes = bytearray([0xFF])
            for ci in range(8):
                for rb in frame[ci]:
                    frame_bytes.append(rb)
            frame_changed = 8
        else:
            bitmask = 0x00
            char_data = bytearray()
            frame_changed = 0
            for ci in range(8):
                if compare_chars(frame[ci], prev_frame[ci], threshold):
                    bitmask |= (1 << ci)
                    frame_changed += 1
                    for rb in frame[ci]:
                        char_data.append(rb)
            frame_bytes = bytearray([bitmask])
            frame_bytes.extend(char_data)

        # Verificar límite de flash para la parte actual
        if max_bytes is not None and (len(current_data) + len(frame_bytes)) > max_bytes and part_frames > 0:
            if not split:
                print(f"  INFO: Límite de flash alcanzado ({max_bytes} bytes) en frame {part_frames} (sin split)", file=sys.stderr)
                break

            # Guardar parte actual completada
            stats = {
                'total_chars': part_total_chars,
                'changed_chars': part_changed_chars,
                'compression_pct': 100.0 * part_changed_chars / part_total_chars if part_total_chars > 0 else 0,
                'data_size': len(current_data),
                'total_available': len(sorted_files),
            }
            parts.append({
                'data': bytes(current_data),
                'num_frames': part_frames,
                'stats': stats,
                'start_frame': part_start_idx + 1,
                'end_frame': i,
            })

            # Iniciar nueva parte comenzando en el frame actual como KEYFRAME
            current_data = bytearray()
            part_start_idx = i
            part_frames = 0
            part_total_chars = 0
            part_changed_chars = 0
            prev_frame = None

            frame_bytes = bytearray([0xFF])
            for ci in range(8):
                for rb in frame[ci]:
                    frame_bytes.append(rb)
            frame_changed = 8

        current_data.extend(frame_bytes)
        part_changed_chars += frame_changed
        part_total_chars += 8
        prev_frame = frame
        part_frames += 1

        if (i + 1) % 100 == 0:
            print(f"  Procesados {i + 1} frames...", file=sys.stderr)

    if part_frames > 0:
        stats = {
            'total_chars': part_total_chars,
            'changed_chars': part_changed_chars,
            'compression_pct': 100.0 * part_changed_chars / part_total_chars if part_total_chars > 0 else 0,
            'data_size': len(current_data),
            'total_available': len(sorted_files),
        }
        parts.append({
            'data': bytes(current_data),
            'num_frames': part_frames,
            'stats': stats,
            'start_frame': part_start_idx + 1,
            'end_frame': part_start_idx + part_frames,
        })

    return parts


def generate_ccs_header(data, num_frames, stats, fps, output_file, part_num=1, total_parts=1, start_frame=1, end_frame=None):
    """Genera .h compatible con CCS C Compiler v5 (dividido en chunks <= 512 bytes)."""
    delay_ms = 1000 // fps if fps > 0 else 250
    CHUNK_SIZE = 512
    chunks = [data[i:i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]
    if end_frame is None:
        end_frame = start_frame + num_frames - 1

    filename = os.path.basename(output_file)

    with open(output_file, 'w') as f:
        f.write("/*\n")
        f.write(f" * {filename} - Datos Bad Apple comprimidos (delta encoding)\n")
        f.write(f" * Generado por img2pic.py para CCS C Compiler v5\n")
        f.write(f" *\n")
        if total_parts > 1:
            f.write(f" * [PARTE {part_num} DE {total_parts}] -> Frames {start_frame} a {end_frame}\n")
        f.write(f" * Frames en esta parte: {num_frames}\n")
        f.write(f" * Tamaño datos:        {len(data)} bytes ({len(data)/1024:.1f} KB)\n")
        f.write(f" * Chars cambiados:     {stats['compression_pct']:.1f}%\n")
        f.write(f" * FPS:                 {fps} ({delay_ms} ms/frame)\n")
        f.write(" *\n")
        f.write(" * Formato: [bitmask][char_data...] por frame\n")
        f.write(" * Chunks: Bloques de 512 bytes para evitar 'Out of ROM' en CCS C.\n")
        f.write(" */\n\n")
        f.write("#ifndef FRAME_DATA_H\n")
        f.write("#define FRAME_DATA_H\n\n")
        f.write(f"#define TOTAL_FRAMES    {num_frames}u\n")
        f.write(f"#define FRAME_DATA_SIZE {len(data)}u\n")
        f.write(f"#define FRAME_DELAY_MS  {delay_ms}u\n")
        f.write(f"#define PART_NUMBER     {part_num}u\n")
        f.write(f"#define PART_TOTAL      {total_parts}u\n")
        f.write(f"#define START_FRAME_NUM {start_frame}u\n")
        f.write(f"#define END_FRAME_NUM   {end_frame}u\n\n")

        for c_idx, chunk_data in enumerate(chunks):
            f.write(f"// Chunk {c_idx} ({len(chunk_data)} bytes)\n")
            f.write(f"const unsigned int8 frame_chunk_{c_idx}[{len(chunk_data)}] = {{\n")
            for i in range(0, len(chunk_data), 16):
                line = chunk_data[i:i+16]
                hex_vals = ", ".join(f"0x{b:02X}" for b in line)
                comma = "," if i + 16 < len(chunk_data) else ""
                f.write(f"    {hex_vals}{comma}\n")
            f.write("};\n\n")

        f.write("// Función de lectura por chunks con switch (eficiente en ROM y velocidad)\n")
        f.write("unsigned int8 rom_read(unsigned int16 idx) {\n")
        f.write("    unsigned int8 chunk = (unsigned int8)(idx >> 9);\n")
        f.write("    unsigned int16 offset = idx & 0x1FFu;\n")
        f.write("    switch (chunk) {\n")
        for c_idx in range(len(chunks)):
            f.write(f"        case {c_idx}: return frame_chunk_{c_idx}[offset];\n")
        f.write("        default: return 0;\n")
        f.write("    }\n")
        f.write("}\n\n")
        f.write("#endif // FRAME_DATA_H\n")


def print_multi_part_summary(parts, fps):
    """Imprime un resumen completo de todas las partes generadas."""
    delay_ms = 1000 // fps if fps > 0 else 250
    total_frames = sum(p['num_frames'] for p in parts)
    total_bytes = sum(len(p['data']) for p in parts)
    total_duration = total_frames * delay_ms / 1000.0

    print(f"\n{'='*65}", file=sys.stderr)
    print(f"  RESUMEN DE CONVERSIÓN ({len(parts)} {'PARTE' if len(parts)==1 else 'PARTES'})", file=sys.stderr)
    print(f"{'='*65}", file=sys.stderr)
    print(f"  Frames totales cubiertos: {total_frames}", file=sys.stderr)
    print(f"  Duración total a {fps} FPS:  {total_duration:.1f} segundos", file=sys.stderr)
    print(f"  Memoria acumulada:        {total_bytes} bytes ({total_bytes/1024:.1f} KB)\n", file=sys.stderr)

    print(f"  {'Parte':<7} | {'Frames':<16} | {'Tamaño':<12} | {'Duración':<10} | {'Archivo'}", file=sys.stderr)
    print(f"  {'-'*7}-+-{'-'*16}-+-{'-'*12}-+-{'-'*10}-+-{'-'*15}", file=sys.stderr)

    for idx, p in enumerate(parts):
        part_num = idx + 1
        nf = p['num_frames']
        sf = p['start_frame']
        ef = p['end_frame']
        sz = len(p['data'])
        dur = nf * delay_ms / 1000.0
        fname = "frame_data.h" if (len(parts) == 1 or part_num == 1) else f"frame_data{part_num}.h"
        f_range = f"{nf} ({sf}..{ef})"
        print(f"  P{part_num:<5} | {f_range:<16} | {sz:>5} B ({sz/1024:.1f}K) | {dur:>5.1f}s     | {fname}", file=sys.stderr)

    print(f"{'='*65}\n", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Convierte frames Bad Apple a datos para PIC (CCS C v5)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # PIC16 con división automática (genera frame_data.h, frame_data2.h, frame_data3.h):
  python3 img2pic.py --frames "pngs/*.png" --no-gaps --pic16 --threshold 3 --fps 6

  # PIC18 entran 1000 frames en 1 archivo:
  python3 img2pic.py --frames "pngs/*.png" --no-gaps --pic18 --fps 10
        """
    )
    parser.add_argument('--frames', required=True,
                        help='Glob de los frames PNG (ej: "frames/*.png")')
    parser.add_argument('--output', default='frame_data.h',
                        help='Archivo base .h de salida (default: frame_data.h)')
    parser.add_argument('--no-gaps', action='store_true',
                        help='Modo sin gaps para imágenes 20x16')
    parser.add_argument('--threshold', type=int, default=0,
                        help='Umbral de píxeles para compresión con pérdida (0=lossless)')
    parser.add_argument('--fps', type=int, default=4,
                        help='FPS objetivo (default: 4)')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='Máximo de frames a procesar')
    parser.add_argument('--no-split', action='store_true',
                        help='No dividir en partes (detenerse al primer límite de flash)')

    # Opciones de PIC
    pic_group = parser.add_mutually_exclusive_group()
    pic_group.add_argument('--pic16', action='store_true',
                           help='Limitar datos al flash del PIC16F877A (~4.5 KB)')
    pic_group.add_argument('--pic18', action='store_true',
                           help='Limitar datos al flash del PIC18F4550 (~28 KB)')

    args = parser.parse_args()

    files = sorted(glob(args.frames), key=natural_sort_key)
    if not files:
        print(f"ERROR: No se encontraron archivos con '{args.frames}'", file=sys.stderr)
        sys.exit(1)

    max_bytes = None
    if args.pic16:
        max_bytes = PIC16_FLASH_AVAILABLE
        print(f"Modo: PIC16F877A (límite {PIC16_FLASH_AVAILABLE} bytes por parte)", file=sys.stderr)
    elif args.pic18:
        max_bytes = PIC18_FLASH_AVAILABLE
        print(f"Modo: PIC18F4550 (límite {PIC18_FLASH_AVAILABLE} bytes por parte)", file=sys.stderr)

    mode_str = 'sin gaps (20×16)' if args.no_gaps else 'con gaps (24×18)'
    print(f"Encontrados {len(files)} frames", file=sys.stderr)
    print(f"Formato: {mode_str} | Umbral: {args.threshold} | FPS: {args.fps}", file=sys.stderr)
    print(f"División en partes (multi-part): {'Desactivada' if args.no_split else 'Activada'}", file=sys.stderr)
    print(f"Procesando...\n", file=sys.stderr)

    use_gaps = not args.no_gaps
    parts = process_frames(
        files, use_gaps, args.threshold, args.max_frames, max_bytes, split=(not args.no_split)
    )

    if not parts:
        print("ERROR: No se generó ninguna parte de datos.", file=sys.stderr)
        sys.exit(1)

    # Generar archivos .h para cada parte
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
                # Parte 1 se escribe a frame_data.h Y a frame_data1.h
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
