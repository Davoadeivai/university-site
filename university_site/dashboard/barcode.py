"""تولید SVG بارکد Code128 ساده برای دسترسی امتحان."""
from __future__ import annotations

# الگوهای Code128B (subset) — کافی برای اعداد و حروف بزرگ
_PATTERNS = {
    ' ': '11011001100', '!': '11001101100', '"': '11001100110', '#': '10010011000',
    '$': '10010001100', '%': '10001001100', '&': '10011001000', "'": '10011000100',
    '(': '10001100100', ')': '11001001000', '*': '11001000100', '+': '11000100100',
    ',': '10110011100', '-': '10011011100', '.': '10011001110', '/': '10111001100',
    '0': '10011101100', '1': '10011100110', '2': '11001110010', '3': '11001011100',
    '4': '11001001110', '5': '11011100100', '6': '11001110100', '7': '11101101110',
    '8': '11101001100', '9': '11100101100', ':': '11100100110', ';': '11101100100',
    '<': '11100110100', '=': '11100110010', '>': '11011011000', '?': '11011000110',
    '@': '11000110110', 'A': '10100011000', 'B': '10001011000', 'C': '10001000110',
    'D': '10110001000', 'E': '10001101000', 'F': '10001100010', 'G': '11010001000',
    'H': '11000101000', 'I': '11000100010', 'J': '10110111000', 'K': '10110001110',
    'L': '10001101110', 'M': '10111011000', 'N': '10111000110', 'O': '10001110110',
    'P': '11101110110', 'Q': '11010001110', 'R': '11000101110', 'S': '11011101000',
    'T': '11011100010', 'U': '11011101110', 'V': '11101011000', 'W': '11101000110',
    'X': '11100010110', 'Y': '11101101000', 'Z': '11101100010',
}
_START_B = '11010010000'
_STOP = '1100011101011'


def _value(ch: str) -> int:
    return ord(ch) - 32


def code128_bits(data: str) -> str:
    data = ''.join(ch if ch in _PATTERNS else '-' for ch in (data or '').upper())
    if not data:
        data = '0'
    checksum = 104  # Start B
    bits = [_START_B]
    for i, ch in enumerate(data, start=1):
        bits.append(_PATTERNS.get(ch, _PATTERNS['-']))
        checksum += _value(ch) * i
    checksum %= 103
    # checksum pattern from value
    check_ch = chr(checksum + 32) if 0 <= checksum <= 94 else '-'
    bits.append(_PATTERNS.get(check_ch, _PATTERNS['-']))
    bits.append(_STOP)
    return ''.join(bits)


def barcode_svg(data: str, height: int = 60, module_width: int = 2) -> str:
    bits = code128_bits(data)
    width = len(bits) * module_width
    rects = []
    x = 0
    for bit in bits:
        if bit == '1':
            rects.append(f'<rect x="{x}" y="0" width="{module_width}" height="{height}" fill="#000"/>')
        x += module_width
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height + 18}" '
        f'viewBox="0 0 {width} {height + 18}" role="img" aria-label="{data}">'
        f'{"".join(rects)}'
        f'<text x="{width/2}" y="{height + 14}" text-anchor="middle" '
        f'font-family="monospace" font-size="12">{data}</text></svg>'
    )
