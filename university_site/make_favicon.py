"""Create a minimal blue 16x16 favicon.ico"""
import struct
import os

def create_simple_ico(path):
    # 16x16 BGRA8888 image - solid navy blue (#1a3a5c = B=0x5c, G=0x3a, R=0x1a)
    width, height = 16, 16
    # BGRA for #1a3a5c
    b, g, r, a = 0x5c, 0x3a, 0x1a, 0xff
    pixel_data = bytes([b, g, r, a] * (width * height))

    # BITMAPINFOHEADER (40 bytes)
    bih = struct.pack('<IiiHHIIiiII',
        40,          # biSize
        width,       # biWidth
        height * 2,  # biHeight (x2 for ICO format)
        1,           # biPlanes
        32,          # biBitCount (BGRA)
        0,           # biCompression
        len(pixel_data),  # biSizeImage
        0, 0, 0, 0)

    # AND mask: all zeros (fully visible)
    and_mask = bytes(height * ((width + 31) // 32) * 4)

    image_data = bih + pixel_data + and_mask
    image_size = len(image_data)

    # ICO header
    ico_header = struct.pack('<HHH', 0, 1, 1)  # reserved, type=1 (ICO), count=1

    # ICONDIRENTRY
    entry = struct.pack('<BBBBHHIi',
        width,      # bWidth
        height,     # bHeight
        0,          # bColorCount (0 = more than 256)
        0,          # bReserved
        1,          # wPlanes
        32,         # wBitCount
        image_size, # dwBytesInRes
        22          # dwImageOffset (after 6+16 bytes headers)
    )

    with open(path, 'wb') as f:
        f.write(ico_header + entry + image_data)
    print(f"Favicon created at {path} ({os.path.getsize(path)} bytes)")

target = os.path.join(os.path.dirname(__file__), 'static', 'images', 'favicon.ico')
create_simple_ico(target)
