"""Read XNA Texture2D XNBs without modifying the installed game content.

XNB frame/header layout follows the XNA/MonoGame format. LZX frames are put
in an in-memory, single-member CAB so libmspack handles the real codec and
its cross-frame dictionary. No game code or serialized reader is executed.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

MAX_BYTES = 72 * 1024 * 1024
MAX_DIMENSION = 4096


class XnbError(ValueError):
    pass


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, length):
        if length < 0 or length > len(self.data) - self.pos:
            raise XnbError("Truncated XNB data.")
        result = self.data[self.pos:self.pos + length]
        self.pos += length
        return result

    def u32(self):
        return struct.unpack("<I", self.take(4))[0]

    def varint(self):
        value = 0
        for shift in range(0, 35, 7):
            byte = self.take(1)[0]
            if shift == 28 and byte > 15:
                raise XnbError("Invalid XNB variable-length integer.")
            value |= (byte & 127) << shift
            if not byte & 128:
                return value
        raise XnbError("Invalid XNB variable-length integer.")

    def string(self):
        length = self.varint()
        if length > 4096:
            raise XnbError("XNB reader name is too long.")
        try:
            return self.take(length).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise XnbError("Invalid XNB reader name.") from exc


def _lzx(payload, expected):
    try:
        from pylibmspack import CabArchive
    except ImportError as exc:
        raise XnbError("LZX support is missing. Install this version's requirements.txt first.") from exc
    reader, blocks, total = Reader(payload), [], 0
    while reader.pos < len(payload):
        first = reader.take(1)[0]
        if first == 255:
            frame_size, block_size = struct.unpack(">HH", reader.take(4))
        else:
            frame_size, block_size = 32768, (first << 8) | reader.take(1)[0]
        if not frame_size or not block_size:
            if any(reader.take(len(payload)-reader.pos)):
                raise XnbError("Unexpected data after LZX terminator.")
            break
        if frame_size > 32768 or total + frame_size > expected:
            raise XnbError("Invalid LZX frame length.")
        blocks.append(struct.pack("<IHH", 0, block_size, frame_size) + reader.take(block_size))
        total += frame_size
    if total != expected or not blocks:
        raise XnbError("LZX output length does not match the XNB header.")
    if len(blocks) > 65535:
        raise XnbError("Too many LZX frames.")
    filename = b"texture\0"
    file_entry = struct.pack("<IIHHHH", expected, 0, 0, 0, 0, 0) + filename
    data_offset = 36 + 8 + len(file_entry)
    data = b"".join(blocks)
    header = struct.pack("<4sIIIII BBHHHHH", b"MSCF", 0, data_offset + len(data), 0,
                         44, 0, 3, 1, 1, 1, 0, 0, 0)
    # CAB type 3 is LZX; its high byte supplies the 16-bit XNB dictionary size.
    folder = struct.pack("<IHH", data_offset, len(blocks), 0x1003)
    try:
        result = CabArchive.from_bytes(header + folder + file_entry + data).read("texture", max_size=expected)
    except Exception as exc:
        raise XnbError(f"Could not decompress the XNB's LZX stream: {exc}") from exc
    if len(result) != expected:
        raise XnbError("LZX decompressed to an unexpected length.")
    return result


def _surface_size(fmt, width, height):
    if fmt in (4, 5, 6):
        return ((width + 3) // 4) * ((height + 3) // 4) * (8 if fmt == 4 else 16)
    if fmt in (0, 1, 2, 3, 12):
        return width * height * {0:4, 1:2, 2:2, 3:2, 12:1}[fmt]
    raise XnbError(f"Unsupported XNB surface format {fmt}. Supported: Color, Bgr565, Bgra5551, Bgra4444, DXT1/3/5, Alpha8.")


def _pixels(fmt, width, height, data):
    if fmt == 0:
        return Image.frombytes("RGBA", (width, height), data)
    if fmt in (4, 5, 6):
        # Decode complete 4x4 blocks, then trim for non-multiple-of-four dimensions.
        size = ((width+3)//4*4, (height+3)//4*4)
        n = {4:1, 5:2, 6:3}[fmt]
        return Image.frombytes("RGBA", size, data, "bcn", (n, f"DXT{n if n==1 else 3 if n==2 else 5}")).crop((0,0,width,height))
    result = Image.new("RGBA", (width, height))
    if fmt == 12:
        result.putdata([(255,255,255,a) for a in data])
        return result
    rgba = []
    for (value,) in struct.iter_unpack("<H", data):
        if fmt == 1:
            r,g,b,a=(value>>11)&31,(value>>5)&63,value&31,255
            rgba.append(((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2),a))
        elif fmt == 2:
            r,g,b=(value>>10)&31,(value>>5)&31,value&31
            rgba.append(((r<<3)|(r>>2),(g<<3)|(g>>2),(b<<3)|(b>>2),255 if value&0x8000 else 0))
        else:
            rgba.append((((value>>8)&15)*17,((value>>4)&15)*17,(value&15)*17,((value>>12)&15)*17))
    result.putdata(rgba)
    return result


@dataclass
class Texture:
    image: Image.Image
    compression: str
    surface_format: int
    mip_count: int


def read_texture(source, *, straight_alpha=True):
    """Decode one Texture2D. XNA pipeline colors are premultiplied by default."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.stat().st_size > MAX_BYTES:
            raise XnbError("XNB is larger than the 72 MB import limit.")
        data = path.read_bytes()
    else:
        data = bytes(source)
    if len(data)<10 or len(data)>MAX_BYTES or data[:3]!=b"XNB":
        raise XnbError("This is not a supported XNB file.")
    if data[3] not in b"wmlai":
        raise XnbError("Unsupported XNB platform (console texture layouts are not supported).")
    if data[4] not in (4,5):
        raise XnbError(f"Unsupported XNB version {data[4]}.")
    flags = data[5]
    if flags & ~0xC1 or flags & 0xC0 == 0xC0:
        raise XnbError("Unsupported XNB flags.")
    if struct.unpack_from("<I",data,6)[0] != len(data):
        raise XnbError("XNB file size does not match its header.")
    payload, compression = data[10:], "none"
    if flags & 0xC0:
        header = Reader(payload);expected=header.u32();payload=header.take(len(payload)-4)
        if not 0<expected<=MAX_BYTES:
            raise XnbError("Invalid XNB decompressed size.")
        if flags & 0x80:
            payload, compression = _lzx(payload,expected), "LZX"
        else:
            try:
                from lz4.block import decompress
                payload = decompress(payload,uncompressed_size=expected)
            except ImportError as exc:
                raise XnbError("LZ4 support is missing. Install this version's requirements.txt first.") from exc
            except Exception as exc:
                raise XnbError(f"Invalid LZ4 XNB: {exc}") from exc
            compression = "LZ4"
            if len(payload)!=expected:raise XnbError("LZ4 output size mismatch.")
    reader=Reader(payload)
    count=reader.varint()
    if not 1<=count<=128:raise XnbError("Invalid XNB type-reader count.")
    names=[]
    for _ in range(count):
        names.append(reader.string().split(",",1)[0]);reader.u32()
    if reader.varint()!=0:raise XnbError("Shared-resource XNBs are not supported; select an individual hat Texture2D.")
    root=reader.varint()
    if not 1<=root<=count or names[root-1]!="Microsoft.Xna.Framework.Content.Texture2DReader":
        raise XnbError("This XNB is not a Texture2D image. Select a hat texture, not a font, sound, or model.")
    fmt,width,height,mips=reader.u32(),reader.u32(),reader.u32(),reader.u32()
    if not 1<=width<=MAX_DIMENSION or not 1<=height<=MAX_DIMENSION or not 1<=mips<=13:
        raise XnbError("Invalid or oversized XNB texture dimensions/mipmap count.")
    if mips>max(width,height).bit_length():raise XnbError("Invalid XNB mipmap count.")
    image=None
    for level in range(mips):
        w,h=max(1,width>>level),max(1,height>>level)
        length=reader.u32()
        if length!=_surface_size(fmt,w,h):raise XnbError("XNB pixel data length does not match its surface format.")
        raw=reader.take(length)
        if level==0:image=_pixels(fmt,w,h,raw)
    if reader.pos!=len(payload):raise XnbError("Unexpected data after the XNB texture.")
    if straight_alpha:
        converted=[]
        for r,g,b,a in image.get_flattened_data():
            if 0<a<255:
                converted.append((min(255,(r*255+a//2)//a),min(255,(g*255+a//2)//a),min(255,(b*255+a//2)//a),a))
            else:converted.append((r,g,b,a))
        image.putdata(converted)
    return Texture(image,compression,fmt,mips)
