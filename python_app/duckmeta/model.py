"""PNG and metadata handling. Independent of the desktop UI."""
from __future__ import annotations

import copy
import io
import json
import random
import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "assets"
EFFECTS = json.loads(Path(__file__).with_name("effects.json").read_text(encoding="utf-8"))
BY_ID = {d["id"]: d for d in EFFECTS}
EMPTY = (0, 0, 0, 0)


def decode_value(definition, raw):
    kind, maximum = definition["kind"], definition["max"]
    if kind in ("VEC", "INT"):
        return max(-maximum, min(maximum, raw - 128))
    if kind in ("NVEC", "FLOAT"):
        return raw / 255 * maximum
    if kind in ("NNVEC", "NFLOAT"):
        return (raw / 255 * 2 - 1) * maximum
    return raw


def evaluate(slots, rng=random.random):
    values, previous = {}, None
    for ident, green, blue, alpha in slots:
        if not alpha:
            continue
        if ident in (100, 101, 102):
            if previous not in values:
                continue
            low, high = green / 255 * 2 - 1, blue / 255 * 2 - 1
            if ident in (100, 102):
                values[previous][0] *= low + rng() * (high - low)
            if ident in (101, 102):
                values[previous][1] *= low + rng() * (high - low)
        else:
            previous = ident
            if ident in BY_ID:
                values[ident] = [decode_value(BY_ID[ident], green), decode_value(BY_ID[ident], blue)]
    return values


@dataclass
class Hat:
    name: str
    artwork: Image.Image
    slots: list[tuple[int, int, int, int]]
    had_meta: bool = False

    @property
    def width(self):
        return self.artwork.width

    @property
    def height(self):
        return self.artwork.height

    @classmethod
    def read(cls, source, name=None):
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("Choose a PNG smaller than 8 MB.")
            data = path.read_bytes()
            name = name or path.name
        else:
            data = bytes(source)
        if not 33 <= len(data) <= 8 * 1024 * 1024 or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Choose a valid PNG smaller than 8 MB.")
        width, height, depth, color = struct.unpack(">IIBB", data[16:26])
        if not 32 <= width <= 1025 or not 32 <= height <= 1024 or width % 32 not in (0, 1):
            raise ValueError("Use 32-pixel columns, optionally plus one metadata column (e.g. 96 or 97 wide); maximum artwork is 1024 × 1024.")
        if depth != 8 and color != 3:
            raise ValueError("Use an 8-bit RGB/RGBA/grayscale or indexed PNG. High bit depths are not converted silently.")
        with Image.open(io.BytesIO(data)) as check:
            check.verify()  # Validate PNG chunk checksums before reading pixels.
        with Image.open(io.BytesIO(data)) as source_image:
            image = source_image.convert("RGBA")
        has_meta = width % 32 == 1
        art_width = width - int(has_meta)
        slots = [image.getpixel((art_width, y)) if has_meta else EMPTY for y in range(height)]
        return cls(name or "hat.png", image.crop((0, 0, art_width, height)), slots, has_meta)

    def image(self):
        result = Image.new("RGBA", (self.width + 1, self.height))
        # No mask: preserve even the RGB bytes of fully transparent pixels.
        result.paste(self.artwork, (0, 0))
        for y, pixel in enumerate(self.slots):
            result.putpixel((self.width, y), pixel)
        return result

    def png(self):
        buffer = io.BytesIO()
        self.image().save(buffer, format="PNG")
        return buffer.getvalue()

    def add(self, ident, after=-1):
        definition = BY_ID[ident]
        start = min(self.height - 1, max(0, after + 1))
        free = next((i for i in range(start, self.height) if self.slots[i] == EMPTY), None)
        if free is None:
            raise ValueError("No empty rows after this selection. Select an earlier modifier or remove one.")
        self.slots[start + 1:free + 1] = self.slots[start:free]
        self.slots[start] = (ident, *definition["defaults"], 255)
        return start

    @classmethod
    def example(cls):
        hat = cls.read(ASSETS / "wizard.png")
        demo = [(1,128,128,255),(10,128,128,255),(12,128,220,255),(13,180,145,255),
                (34,134,0,255),(35,170,0,255),(36,150,80,255),(100,0,255,255),
                (37,128,138,255),(39,255,0,255),(40,100,20,255)]
        hat.slots[:len(demo)] = demo
        return hat


class History:
    def __init__(self):
        self.past, self.future = [], []

    def record(self, slots):
        self.past.append(copy.deepcopy(slots))
        self.past = self.past[-100:]
        self.future.clear()

    def undo(self, hat):
        if self.past:
            self.future.append(list(hat.slots))
            hat.slots = self.past.pop()
            return True
        return False

    def redo(self, hat):
        if self.future:
            self.past.append(list(hat.slots))
            hat.slots = self.future.pop()
            return True
        return False
