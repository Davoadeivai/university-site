"""تولید SVG بارکد Code39 برای اسکن در جلسه امتحان."""
from __future__ import annotations

import html

# Code39 patterns (narrow/wide as 0/1 bits with inter-char gap)
_CODE39 = {
    '0': '101001101101', '1': '110100101011', '2': '101100101011', '3': '110110010101',
    '4': '101001101011', '5': '110100110101', '6': '101100110101', '7': '101001011011',
    '8': '110100101101', '9': '101100101101', 'A': '110101001011', 'B': '101101001011',
    'C': '110110100101', 'D': '101011001011', 'E': '110101100101', 'F': '101101100101',
    'G': '101010011011', 'H': '110101001101', 'I': '101101001101', 'J': '101011001101',
    'K': '110101010011', 'L': '101101010011', 'M': '110110101001', 'N': '101011010011',
    'O': '110101101001', 'P': '101101101001', 'Q': '101010110011', 'R': '110101011001',
    'S': '101101011001', 'T': '101011011001', 'U': '110010101011', 'V': '100110101011',
    'W': '110011010101', 'X': '100101101011', 'Y': '110010110101', 'Z': '100110110101',
    '-': '100101011011', '.': '110010101101', ' ': '100110101101', '*': '100101101101',
}


def barcode_svg(data: str, height: int = 60, module_width: int = 2) -> str:
    raw = ''.join(ch for ch in (data or '').upper() if ch in _CODE39 and ch != '*')
    if not raw:
        raw = '0'
    payload = f'*{raw}*'
    bits = []
    for i, ch in enumerate(payload):
        bits.append(_CODE39[ch])
        if i < len(payload) - 1:
            bits.append('0')  # inter-character gap
    stream = ''.join(bits)
    width = len(stream) * module_width
    rects = []
    x = 0
    for bit in stream:
        if bit == '1':
            rects.append(f'<rect x="{x}" y="0" width="{module_width}" height="{height}" fill="#000"/>')
        x += module_width
    label = html.escape(raw)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height + 18}" '
        f'viewBox="0 0 {width} {height + 18}" role="img" aria-label="{label}">'
        f'{"".join(rects)}'
        f'<text x="{width/2}" y="{height + 14}" text-anchor="middle" '
        f'font-family="monospace" font-size="12">{label}</text></svg>'
    )
