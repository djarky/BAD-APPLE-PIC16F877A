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
from glob import glob


# ============================================================
#  Límites de memoria (estimados, descontando código ~2-4KB)
# ============================================================
PIC16_FLASH_AVAILABLE = 6144    # PIC16F877A: ~6 KB para datos
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


def process_frames(file_list, use_gaps=True, threshold=0, max_frames=None, max_bytes=None):
    """
    Procesa frames con delta encoding.
    Se detiene si alcanza max_frames o si los datos exceden max_bytes.

    Retorna: (data_bytes, num_frames, stats)
    """
    data = bytearray()
    prev_frame = None
    num_frames = 0
    total_chars = 0
    changed_chars = 0
    skipped = 0

    for fn in sorted(file_list):
        # Verificar límite de frames
        if max_frames is not None and num_frames >= max_frames:
            skipped = len(file_list) - num_frames
            break

        matrix, width, height = load_and_binarize(fn)
        frame = img2frame(matrix, width, height, use_gaps)

        if frame is None:
            print(f"  WARN: Imagen inválida: {fn}, saltando...", file=sys.stderr)
            continue

        # Calcular datos de este frame ANTES de agregarlo
        frame_bytes = bytearray()
        if prev_frame is None:
            bitmask = 0xFF
            frame_bytes.append(bitmask)
            for ci in range(8):
                for rb in frame[ci]:
                    frame_bytes.append(rb)
            frame_changed = 8
        else:
            bitmask = 0x00
            char_data = bytearray()
            frame_changed = 0
            for ci in range(8):
                total_chars += 1
                if compare_chars(frame[ci], prev_frame[ci], threshold):
                    bitmask |= (1 << ci)
                    frame_changed += 1
                    for rb in frame[ci]:
                        char_data.append(rb)
            frame_bytes.append(bitmask)
            frame_bytes.extend(char_data)

        # Verificar límite de bytes
        if max_bytes is not None and (len(data) + len(frame_bytes)) > max_bytes:
            skipped = len(file_list) - num_frames
            print(f"  INFO: Límite de flash alcanzado ({max_bytes} bytes) en frame {num_frames}", file=sys.stderr)
            break

        data.extend(frame_bytes)
        changed_chars += frame_changed
        prev_frame = frame
        num_frames += 1

        if num_frames % 100 == 0:
            print(f"  Procesados {num_frames} frames ({len(data)} bytes)...", file=sys.stderr)

    if prev_frame is None:
        total_chars = 0
    else:
        total_chars += 8  # primer frame

    stats = {
        'total_chars': total_chars,
        'changed_chars': changed_chars,
        'compression_pct': 100.0 * changed_chars / total_chars if total_chars > 0 else 0,
        'data_size': len(data),
        'skipped_frames': skipped,
        'total_available': len(file_list),
    }
    return bytes(data), num_frames, stats


def generate_ccs_header(data, num_frames, stats, fps, output_file):
    """Genera .h compatible con CCS C Compiler v5 (dividido en chunks <= 1024 bytes)."""
    delay_ms = 1000 // fps if fps > 0 else 250
    CHUNK_SIZE = 1024
    chunks = [data[i:i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]

    with open(output_file, 'w') as f:
        f.write("/*\n")
        f.write(" * frame_data.h - Datos Bad Apple comprimidos (delta encoding)\n")
        f.write(f" * Generado por img2pic.py para CCS C Compiler v5\n")
        f.write(f" *\n")
        f.write(f" * Frames:          {num_frames} de {stats['total_available']} disponibles\n")
        f.write(f" * Tamaño datos:    {len(data)} bytes ({len(data)/1024:.1f} KB)\n")
        f.write(f" * Chars cambiados: {stats['compression_pct']:.1f}%\n")
        f.write(f" * FPS:             {fps} ({delay_ms} ms/frame)\n")
        if stats['skipped_frames'] > 0:
            f.write(f" * Frames omitidos: {stats['skipped_frames']} (por límite de flash)\n")
        f.write(f" *\n")
        f.write(" * Formato: [bitmask][char_data...] por frame\n")
        f.write(" * Chunks: Dividido en bloques <= 1024 bytes para evitar\n")
        f.write(" *         'Error 71: Out of ROM (A segment is too large)' en PIC16/PIC18.\n")
        f.write(" */\n\n")
        f.write("#ifndef FRAME_DATA_H\n")
        f.write("#define FRAME_DATA_H\n\n")
        f.write(f"#define TOTAL_FRAMES    {num_frames}u\n")
        f.write(f"#define FRAME_DATA_SIZE {len(data)}u\n")
        f.write(f"#define FRAME_DELAY_MS  {delay_ms}u\n\n")

        for c_idx, chunk_data in enumerate(chunks):
            f.write(f"// Chunk {c_idx} ({len(chunk_data)} bytes) - cabe holgadamente en páginas de 2048 words\n")
            f.write(f"const unsigned int8 frame_chunk_{c_idx}[{len(chunk_data)}] = {{\n")
            for i in range(0, len(chunk_data), 16):
                line = chunk_data[i:i+16]
                hex_vals = ", ".join(f"0x{b:02X}" for b in line)
                comma = "," if i + 16 < len(chunk_data) else ""
                f.write(f"    {hex_vals}{comma}\n")
            f.write("};\n\n")

        f.write("// Función unificada de lectura por chunks\n")
        f.write("// CCS C ubica cada chunk en una página de ROM distinta según haya espacio libre\n")
        f.write("unsigned int8 rom_read(unsigned int16 idx) {\n")
        for c_idx in range(len(chunks) - 1):
            limit = (c_idx + 1) * CHUNK_SIZE
            offset_str = f" - {c_idx * CHUNK_SIZE}u" if c_idx > 0 else ""
            f.write(f"    if (idx < {limit}u) return frame_chunk_{c_idx}[idx{offset_str}];\n")
        last_idx = len(chunks) - 1
        last_offset = f" - {last_idx * CHUNK_SIZE}u" if last_idx > 0 else ""
        f.write(f"    return frame_chunk_{last_idx}[idx{last_offset}];\n")
        f.write("}\n\n")
        f.write("#endif // FRAME_DATA_H\n")


def print_summary(num_frames, stats, fps):
    """Imprime resumen y estimaciones."""
    data_size = stats['data_size']
    delay_ms = 1000 // fps if fps > 0 else 250

    print(f"\n{'='*55}", file=sys.stderr)
    print(f"  RESUMEN DE CONVERSIÓN", file=sys.stderr)
    print(f"{'='*55}", file=sys.stderr)
    print(f"  Frames procesados:  {num_frames} / {stats['total_available']}", file=sys.stderr)
    if stats['skipped_frames'] > 0:
        print(f"  Frames omitidos:    {stats['skipped_frames']} (límite de flash)", file=sys.stderr)
    print(f"  Tamaño datos:       {data_size} bytes ({data_size/1024:.1f} KB)", file=sys.stderr)
    print(f"  Chars actualizados: {stats['compression_pct']:.1f}%", file=sys.stderr)

    if num_frames > 0:
        bpf = data_size / num_frames
        dur = num_frames * delay_ms / 1000.0
        print(f"  Bytes/frame prom:   {bpf:.1f}", file=sys.stderr)
        print(f"  Duración a {fps} FPS:  {dur:.1f} segundos", file=sys.stderr)

        print(f"\n  {'PIC16F877A':>14} | {'PIC18F4550':>14}", file=sys.stderr)
        print(f"  {'-'*14}-+-{'-'*14}", file=sys.stderr)

        fits16 = "✅ CABE" if data_size <= PIC16_FLASH_AVAILABLE else "❌ NO CABE"
        fits18 = "✅ CABE" if data_size <= PIC18_FLASH_AVAILABLE else "❌ NO CABE"
        print(f"  {fits16:>14} | {fits18:>14}", file=sys.stderr)

        max16 = min(stats['total_available'], int(PIC16_FLASH_AVAILABLE / bpf))
        max18 = min(stats['total_available'], int(PIC18_FLASH_AVAILABLE / bpf))
        print(f"  {'~'+str(max16)+' frames':>14} | {'~'+str(max18)+' frames':>14}", file=sys.stderr)

    print(f"{'='*55}\n", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Convierte frames Bad Apple a datos para PIC (CCS C v5)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Modo estándar compatible con ambos PICs:
  python3 img2pic.py --frames "frames/*.png" --pic16 --output frame_data.h

  # Modo PIC18, máximo de frames, 10 FPS:
  python3 img2pic.py --frames "pngs/*.png" --no-gaps --pic18 --fps 10 --output frame_data.h

  # PIC16 con compresión agresiva para más frames:
  python3 img2pic.py --frames "pngs/*.png" --no-gaps --pic16 --threshold 5 --fps 8

  # Frames manuales limitados:
  python3 img2pic.py --frames "pngs/*.png" --no-gaps --max-frames 300 --fps 6
        """
    )
    parser.add_argument('--frames', required=True,
                        help='Glob de los frames PNG (ej: "frames/*.png")')
    parser.add_argument('--output', default='frame_data.h',
                        help='Archivo .h de salida (default: frame_data.h)')
    parser.add_argument('--no-gaps', action='store_true',
                        help='Modo sin gaps para imágenes 20x16')
    parser.add_argument('--threshold', type=int, default=0,
                        help='Umbral de píxeles para compresión con pérdida (0=lossless)')
    parser.add_argument('--fps', type=int, default=4,
                        help='FPS objetivo (default: 4)')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='Máximo de frames a procesar (default: todos los que quepan)')

    # Opciones de PIC (mutuamente excluyentes con max-frames)
    pic_group = parser.add_mutually_exclusive_group()
    pic_group.add_argument('--pic16', action='store_true',
                           help='Limitar datos al flash del PIC16F877A (~6 KB)')
    pic_group.add_argument('--pic18', action='store_true',
                           help='Limitar datos al flash del PIC18F4550 (~28 KB)')

    args = parser.parse_args()

    files = sorted(glob(args.frames))
    if not files:
        print(f"ERROR: No se encontraron archivos con '{args.frames}'", file=sys.stderr)
        sys.exit(1)

    # Determinar límite de bytes
    max_bytes = None
    if args.pic16:
        max_bytes = PIC16_FLASH_AVAILABLE
        print(f"Modo: PIC16F877A (límite {PIC16_FLASH_AVAILABLE} bytes)", file=sys.stderr)
    elif args.pic18:
        max_bytes = PIC18_FLASH_AVAILABLE
        print(f"Modo: PIC18F4550 (límite {PIC18_FLASH_AVAILABLE} bytes)", file=sys.stderr)

    mode_str = 'sin gaps (20×16)' if args.no_gaps else 'con gaps (24×18)'
    print(f"Encontrados {len(files)} frames", file=sys.stderr)
    print(f"Formato: {mode_str}", file=sys.stderr)
    print(f"Umbral: {args.threshold} (0=lossless)", file=sys.stderr)
    print(f"FPS: {args.fps}", file=sys.stderr)
    if args.max_frames:
        print(f"Max frames: {args.max_frames}", file=sys.stderr)
    print(f"Procesando...\n", file=sys.stderr)

    use_gaps = not args.no_gaps
    data, num_frames, stats = process_frames(
        files, use_gaps, args.threshold, args.max_frames, max_bytes
    )

    generate_ccs_header(data, num_frames, stats, args.fps, args.output)
    print_summary(num_frames, stats, args.fps)
    print(f"Archivo generado: {args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()
