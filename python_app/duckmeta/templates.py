"""Local metadata templates and transactional, order-aware application."""
import json
import os
import tempfile
import uuid
from pathlib import Path
from .model import EMPTY

RANDOMIZERS = (100, 101, 102)


def validate_pixels(pixels):
    if not isinstance(pixels, list) or not 1 <= len(pixels) <= 1024:
        raise ValueError('Select at least one metapixel (maximum 1024).')
    result = []
    for pixel in pixels:
        if not isinstance(pixel, (list, tuple)) or len(pixel) != 4 or any(type(v) is not int or not 0 <= v <= 255 for v in pixel) or not pixel[3]:
            raise ValueError('Templates must contain enabled RGBA metapixels.')
        if not result and pixel[0] in RANDOMIZERS:
            raise ValueError('Select the target modifier along with its randomizer.')
        result.append(tuple(pixel))
    return result


def selected_pixels(slots, indices):
    selected = set(indices)
    target = None
    result = []
    for i, pixel in enumerate(slots):
        if not pixel[3]:continue
        if pixel[0] not in RANDOMIZERS:target = i
        elif i in selected and target not in selected:
            raise ValueError('Select each randomizer’s target modifier too.')
        if i in selected:result.append(pixel)
    return validate_pixels(result)


def plan_apply(slots, pixels):
    pixels = validate_pixels(pixels)
    ids = {p[0] for p in pixels if p[0] not in RANDOMIZERS}
    kept, replaced = [], []
    replacing = False
    insertion = None
    for pixel in slots:
        if pixel[3] and pixel[0] not in RANDOMIZERS:
            replacing = pixel[0] in ids
        if pixel[3] and replacing:
            if insertion is None:insertion = len(kept)
            replaced.append(pixel)
        elif pixel != EMPTY:
            kept.append(pixel)
    if insertion is None:insertion = len(kept)
    merged = kept[:insertion] + pixels + kept[insertion:]
    if len(merged) > len(slots):
        raise ValueError('This hat has too few metadata rows for the template. Remove some modifiers first.')
    merged += [EMPTY] * (len(slots)-len(merged))
    # Identical settings need neither confirmation nor an undo entry.
    if replaced == pixels:return list(slots), []
    return merged, sorted({p[0] for p in replaced if p[0] not in RANDOMIZERS})


class TemplateStore:
    def __init__(self, directory):self.directory = Path(directory)

    def list(self):
        entries, errors = [], []
        for path in sorted(self.directory.glob('*.json')):
            try:
                if path.stat().st_size > 65536:raise ValueError('File too large')
                data = json.loads(path.read_text(encoding='utf-8'))
                if data.get('version') != 1 or not isinstance(data.get('name'),str) or not data['name'].strip():
                    raise ValueError('Invalid template name or version')
                entries.append((data['name'],validate_pixels(data['pixels'])))
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                errors.append(f'{path.name}: {exc}')
        return sorted(entries,key=lambda entry:entry[0].casefold()), errors

    def save(self, name, pixels):
        name = name.strip()
        if not name or len(name)>100:raise ValueError('Enter a template name of 1–100 characters.')
        pixels = validate_pixels(pixels)
        entries, _ = self.list()
        if any(n.casefold()==name.casefold() for n,_ in entries):
            raise ValueError('That template name already exists. Choose another name.')
        self.directory.mkdir(parents=True,exist_ok=True)
        path = self.directory / (uuid.uuid4().hex+'.json')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.directory,delete=False) as stream:
                temporary = Path(stream.name)
                json.dump({'version':1,'name':name,'pixels':pixels},stream)
            os.replace(temporary,path)
        finally:
            if temporary:temporary.unlink(missing_ok=True)
        return path
