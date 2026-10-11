/*
 * badapple_pic.c - Bad Apple en LCD 16x2 para PIC16F877A / PIC18F4550
 * Compilador: CCS C Compiler v5
 *
 * Port basado en img2lcdino (arduinocelentano, GPLv3)
 *
 * ┌──────────────────────────────────────────────┐
 * │  INSTRUCCIONES:                              │
 * │  1. Descomenta UNA de las dos líneas de      │
 * │     #define abajo (USE_PIC16 o USE_PIC18)    │
 * │  2. Ajusta los pines del LCD si es necesario │
 * │  3. Genera frame_data.h con img2pic.py       │
 * │  4. Compila con CCS C v5 en MPLAB o PIC C   │
 * └──────────────────────────────────────────────┘
 *
 * Conexiones LCD 16x2 (modo 4 bits):
 *   D4 -> RD4       RS -> RD2
 *   D5 -> RD5       EN -> RD3
 *   D6 -> RD6       RW -> GND
 *   D7 -> RD7
 */

// ============================================================
//  SELECCIÓN DE PIC (descomentar UNO)
// ============================================================
//#define USE_PIC16    // PIC16F877A — ~6 KB para datos, ~170-480 frames
#define USE_PIC18    // PIC18F4550 — ~28 KB para datos, ~790-1000 frames

// ============================================================
//  CONFIGURACIÓN PIC16F877A
// ============================================================
#ifdef USE_PIC16

#include <16F877A.h>

#fuses HS                // Cristal alta velocidad
#fuses NOWDT             // Sin Watchdog
#fuses NOPROTECT         // Sin protección de código
#fuses NOLVP             // Sin Low Voltage Programming
#fuses PUT               // Power Up Timer habilitado
#fuses BROWNOUT          // Brown-out Reset habilitado
#fuses NODEBUG           // Sin modo debug
#fuses NOCPD             // Sin protección de datos EEPROM

#use delay(crystal = 20MHz)

#endif // USE_PIC16

// ============================================================
//  CONFIGURACIÓN PIC18F4550
// ============================================================
#ifdef USE_PIC18

#include <18F4550.h>

#fuses HS                // Cristal alta velocidad
#fuses NOWDT             // Sin Watchdog
#fuses NOPROTECT         // Sin protección de código
#fuses NOLVP             // Sin Low Voltage Programming
#fuses PUT               // Power Up Timer habilitado
#fuses BROWNOUT          // Brown-out Reset habilitado
#fuses NODEBUG           // Sin modo debug
#fuses NOPBADEN          // PORTB digital (no analógico)
#fuses CPUDIV1           // CPU sin divisor
#fuses NOVREGEN          // Regulador USB deshabilitado

#use delay(crystal = 20MHz)

#endif // USE_PIC18

// ============================================================
//  PINES DEL LCD (ajustar según tu circuito)
// ============================================================
// Conexión recomendada de 6 pines (RW conectado directo a GND)
#define LCD_DATA4  PIN_D4
#define LCD_DATA5  PIN_D5
#define LCD_DATA6  PIN_D6
#define LCD_DATA7  PIN_D7
#define LCD_RS     PIN_D2
#define LCD_EN     PIN_D3

// Driver flexible (soporta RW a GND y compatible con LiquidCrystal de Arduino)
#include <lcd_flex.h>
//ver repo lcd_flex_ccs de djarky

// NOTA: Si en el futuro deseas usar la librería de fábrica <lcd.c>,
// debes conectar obligatoriamente el pin RW a un pin del PIC y definir:
//   #define LCD_ENABLE_PIN  PIN_D3
//   #define LCD_RS_PIN      PIN_D2
//   #define LCD_RW_PIN      PIN_D1   // OBLIGATORIO en <lcd.c>
//   #define LCD_DATA4       PIN_D4
//   #define LCD_DATA5       PIN_D5
//   #define LCD_DATA6       PIN_D6
//   #define LCD_DATA7       PIN_D7
//   #include <lcd.c>

// ============================================================
//  DATOS DE FRAMES COMPRIMIDOS
// ============================================================
// Generados con img2pic.py — ver instrucciones al final del archivo
#include "frame_data.h"

// ============================================================
//  ACCESO A MEMORIA FLASH (ROM)
// ============================================================
// rom_read(idx) está implementada en frame_data.h manejando la lectura
// por chunks (bloques <= 1024 bytes) para evitar desbordar páginas de ROM.


// ============================================================
//  FUNCIONES PARA CUSTOM CHARACTERS
// ============================================================

/*
 * lcd_create_char() ya está implementada en lcd_flex/lcd_flex.c.
 * No redefinir aquí para evitar conflictos de compilación en CCS C.
 *
 * Firma de referencia (implementada en lcd_flex.c):
 *   void lcd_create_char(unsigned int8 location, unsigned int8 *charmap);
 *
 * @param location  Índice del carácter en CGRAM (0-7)
 * @param charmap   Puntero a 8 bytes (5 bits bajos = 1 fila de píxeles)
 */

// ============================================================
// ============================================================
//  CONFIGURACIÓN DE POSICIÓN DE LA ANIMACIÓN
// ============================================================
// Columna inicial en LCD 16x2 (0-indexed):
//   0 = Esquina izquierda (columnas 0, 1, 2, 3) — estándar de img2lcdino
//   6 = Centrado (columnas 6, 7, 8, 9) — estándar Arduino
#ifndef ANIM_START_COL
#define ANIM_START_COL  0
#endif

// ============================================================
//  CONFIGURAR TILES EN DDRAM (se llama UNA SOLA VEZ)
// ============================================================
/*
 * Escribe los 8 índices (0-7) de custom characters en la memoria DDRAM:
 *   Fila 0, cols (ANIM_START_COL .. +3): caracteres 0, 1, 2, 3
 *   Fila 1, cols (ANIM_START_COL .. +3): caracteres 4, 5, 6, 7
 *
 * Patrón idéntico a la versión de Arduino (sketch.ino / LiquidCrystal):
 * Los caracteres se posicionan UNA SOLA VEZ en la pantalla antes de la
 * animación. Durante la reproducción, SOLO se actualiza la memoria CGRAM
 * con lcd_create_char(), y el hardware del LCD refleja automáticamente
 * los nuevos píxeles sin necesidad de tocar la DDRAM en cada frame.
 */
void setup_lcd_positions(void) {
    lcd_set_cursor(ANIM_START_COL + 0, 0);
    lcd_write(0);
    lcd_set_cursor(ANIM_START_COL + 1, 0);
    lcd_write(1);
    lcd_set_cursor(ANIM_START_COL + 2, 0);
    lcd_write(2);
    lcd_set_cursor(ANIM_START_COL + 3, 0);
    lcd_write(3);

    lcd_set_cursor(ANIM_START_COL + 0, 1);
    lcd_write(4);
    lcd_set_cursor(ANIM_START_COL + 1, 1);
    lcd_write(5);
    lcd_set_cursor(ANIM_START_COL + 2, 1);
    lcd_write(6);
    lcd_set_cursor(ANIM_START_COL + 3, 1);
    lcd_write(7);
}

void write_ddram_positions(void) {
    setup_lcd_positions();
}

// ============================================================
//  INICIALIZAR CGRAM CON PATRÓN EN BLANCO
// ============================================================
/*
 * Inicializa los 8 slots de CGRAM con 0x00 para un arranque limpio.
 * Usa lcd_create_char() con un buffer estático en RAM (patrón probado).
 */
void init_cgram_blank(void) {
    static unsigned int8 blank[8] = {0,0,0,0,0,0,0,0};
    unsigned int8 slot;
    for (slot = 0; slot < 8; slot++) {
        lcd_create_char(slot, blank);
    }
}

// ============================================================
//  REPRODUCTOR DE ANIMACIÓN (DECODIFICADOR DELTA)
// ============================================================

/*
 * Lee los datos comprimidos desde ROM mediante rom_read(idx):
 *   - En PIC16: usa read_program_eeprom(FRAME_DATA_ADDR + idx) (hardware directo)
 *   - En PIC18: macro que expande a frame_data[idx] (punteros ROM 21-bit nativos)
 *
 * PATRÓN ARDUINO (sketch.ino / LiquidCrystal):
 *   1. Los 8 tiles (0-7) ya están fijados en la pantalla en setup().
 *   2. En cada frame, SOLO se actualiza la CGRAM de los chars que cambiaron.
 *   3. El hardware HD44780 refresca la pantalla mostrando automáticamente
 *      los nuevos píxeles sin necesidad de tocar la DDRAM.
 */
void play_animation(void) {
    unsigned int16 data_idx;
    unsigned int16 frame;
    unsigned int8  bitmask;
    unsigned int8  ch;
    unsigned int8  row;
    static unsigned int8 char_data[8];

    data_idx = 0;

    for (frame = 0; frame < TOTAL_FRAMES; frame++) {

        // --- Leer bitmask del frame actual desde ROM ---
        bitmask = rom_read(data_idx);
        data_idx++;

        // --- Actualizar CGRAM sólo para los chars que cambiaron ---
        for (ch = 0; ch < 8; ch++) {
            if (bit_test(bitmask, ch)) {
                for (row = 0; row < 8; row++) {
                    char_data[row] = rom_read(data_idx);
                    data_idx++;
                }
                lcd_create_char(ch, char_data);
            }
        }

        // --- Esperar entre frames ---
        // (Los tiles en DDRAM ya están seteados; el LCD actualiza los píxeles automáticamente)
        delay_ms(FRAME_DELAY_MS);
    }
}

// ============================================================
//  MAIN
// ============================================================
void main(void) {

    // --- Configurar pines como digitales ---
#ifdef USE_PIC16
    // PIC16F877A: ADCON1 controla analog/digital
    setup_adc(ADC_OFF);
    setup_adc_ports(NO_ANALOGS);
#endif

#ifdef USE_PIC18
    // PIC18F4550: desactivar ADC, comparadores y USB
    setup_adc(ADC_OFF);
    setup_adc_ports(NO_ANALOGS);
    setup_comparator(NC_NC_NC_NC);
    // USB queda deshabilitado por defecto si no se llama setup_usb()
#endif

    // --- Inicializar LCD ---
    lcd_init();
    delay_ms(100);

    // --- Pantalla de bienvenida (incluye test visual de custom char en slot 0) ---
    static unsigned int8 test_icon[8] = {0x00, 0x0A, 0x1F, 0x1F, 0x0E, 0x04, 0x00, 0x00}; // Corazón de prueba
    lcd_create_char(0, test_icon);

    lcd_gotoxy(1, 1);
#ifdef USE_PIC16
    lcd_write(0);
    lcd_puts(" Bad Apple!!  ");
    lcd_write(0);
    lcd_gotoxy(1, 2);
    lcd_puts(" PIC16F877A LCD ");
#endif
#ifdef USE_PIC18
    lcd_write(0);
    lcd_puts(" Bad Apple!!  ");
    lcd_write(0);
    lcd_gotoxy(1, 2);
    lcd_puts(" PIC18F4550 LCD ");
#endif
    delay_ms(2000);

    // --- Info de frames ---
    lcd_clear();       // Limpiar pantalla (incluye delay_ms(2) interno)
    delay_ms(5);       // Margen extra para HD44780 real (clear tarda hasta 1.52ms)
    lcd_gotoxy(1, 1);
    lcd_puts("Frames: ");
    lcd_print_uint((unsigned int16)TOTAL_FRAMES, DEC);
    lcd_gotoxy(1, 2);
    lcd_puts("FPS: ");
    lcd_print_uint((unsigned int16)(1000u / FRAME_DELAY_MS), DEC);
    delay_ms(2000);

    // --- DIAGNÓSTICO: Verificar lectura via rom_read() (read_program_eeprom) ---
    // rom_read(0) DEBE ser 0xFF (bitmask del frame 0: todos los 8 chars cambian)
    // rom_read(1) DEBE ser 0x00 (fila 0 del char 0: sin píxeles en frame negro)
    lcd_clear();
    delay_ms(5);
    lcd_gotoxy(1, 1);
    lcd_puts("ROM[0]: 0x");
    lcd_print_uint((unsigned int16)rom_read(0), HEX);
    lcd_gotoxy(1, 2);
    lcd_puts("ROM[1]: 0x");
    lcd_print_uint((unsigned int16)rom_read(1), HEX);
    delay_ms(3000);

    // --- Preparar pantalla para la animación ---
    lcd_clear();
    delay_ms(5);
    init_cgram_blank();
    setup_lcd_positions();

    // --- Bucle principal ---
    while (TRUE) {
        play_animation();

        // Mostrar "FIN" y repetir
        lcd_clear();
        delay_ms(5);
        lcd_gotoxy(4, 1);
        lcd_puts("- FIN -");
        lcd_gotoxy(2, 2);
        lcd_puts("Reiniciando...");
        delay_ms(3000);

        lcd_clear();
        delay_ms(5);
        init_cgram_blank();
        write_ddram_positions();
    }
}

/*
 * ============================================================
 *  CÓMO GENERAR frame_data.h
 * ============================================================
 *
 *  1. Instala Pillow:
 *       pip install Pillow
 *
 *  2. Elige tu modo:
 *
 *     --- MODO ESTÁNDAR (compatible PIC16 y PIC18) ---
 *     Usa pocos frames que caben en ambos PICs:
 *
 *       python3 img2pic.py --frames "frames/*.png" \
 *                          --pic16 \
 *                          --fps 4 \
 *                          --output frame_data.h
 *
 *     --- MODO PIC18 (máximo frames) ---
 *     Aprovecha toda la flash del PIC18F4550:
 *
 *       python3 img2pic.py --frames "pngs/*.png" \
 *                          --no-gaps \
 *                          --pic18 \
 *                          --fps 10 \
 *                          --output frame_data.h
 *
 *     --- MODO PIC16 + compresión agresiva ---
 *     Mete más frames sacrificando algo de calidad:
 *
 *       python3 img2pic.py --frames "pngs/*.png" \
 *                          --no-gaps \
 *                          --pic16 \
 *                          --threshold 5 \
 *                          --fps 8 \
 *                          --output frame_data.h
 *
 *  3. Coloca frame_data.h junto a badapple_pic.c
 *
 *  4. Compila con CCS C v5 en MPLAB X IDE o PIC C IDE
 *
 * ============================================================
 */
