"""32-pixel duck frames, annotated-sheet import, and editable animation maps."""
from __future__ import annotations

import copy
from pathlib import Path

from PIL import Image

from .xnb import read_texture, MAX_BYTES, MAX_DIMENSION

STATES=("idle","walk","run","jump","fall","crouch")
DEFAULT_FPS={"idle":1.,"walk":6.,"run":12.,"jump":8.,"fall":8.,"crouch":1.}


def load_sprite_image(path):
    path=Path(path)
    if path.suffix.lower()==".xnb":return read_texture(path).image
    if path.stat().st_size>MAX_BYTES:raise ValueError("Sprite sheet exceeds the 72 MB limit.")
    with Image.open(path) as image:
        if image.format!="PNG":raise ValueError("Select a PNG or Texture2D XNB sprite sheet.")
        if max(image.size)>MAX_DIMENSION:raise ValueError("Sprite sheet is too large (maximum 4096 pixels per side).")
        image.verify()
    with Image.open(path) as image:return image.convert("RGBA")


def split_grid(image):
    if image.width%32 or image.height%32 or min(image.size)<32:
        raise ValueError("Duck textures must be a grid of 32 × 32 cells, or the 387 × 781 annotated reference sheet.")
    if image.width*image.height//1024>512:raise ValueError("Sprite sheet contains more than 512 frames.")
    return [image.crop((x,y,x+32,y+32)) for y in range(0,image.height,32) for x in range(0,image.width,32)]


def head_anchor(frame):
    # Locate the white/gray head in the upper part of the untinted sprite.
    pixels=frame.load();points=[]
    for y in range(0,25):
        row=[]
        for x in range(32):
            r,g,b,a=pixels[x,y]
            if a>127 and max(r,g,b)-min(r,g,b)<15 and (min(r,g,b)>215 or 145<=min(r,g,b)<=170):row.append(x)
        if len(row)>=2:
            top=y
            for yy in range(top,min(top+5,25)):
                for xx in range(32):
                    r,g,b,a=pixels[xx,yy]
                    if a>127 and max(r,g,b)-min(r,g,b)<15 and min(r,g,b)>=145:points.append(xx)
            return (round((min(points)+max(points))/2),top)
    return (17,10)


class DuckSprites:
    def __init__(self,normal,quack=None,source="Single-frame fallback"):
        if not normal:raise ValueError("No duck frames found.")
        self.normal=normal;self.quack=quack or [];self.source=source
        count=len(normal)
        cycle=list(range(min(6,count)))
        self.mapping={"idle":[0],"walk":cycle,"run":cycle,
                      "jump":[6 if count>6 else 0],"fall":[6 if count>6 else 0],
                      "crouch":[7 if count>7 else 0]}
        self.fps=dict(DEFAULT_FPS)
        self._cache={}

    @classmethod
    def from_image(cls,image,source="Imported sheet"):
        image=image.convert("RGBA")
        if image.size==(387,781):
            # The supplied annotated reference: labels/gutters are not frames.
            normal=split_grid(image.crop((0,8,192,200)))
            quack=split_grid(image.crop((194,8,386,776)))
            return cls(normal,quack,source+" · reference layout")
        return cls(split_grid(image),source=source)

    @classmethod
    def load(cls,path):
        return cls.from_image(load_sprite_image(path),Path(path).name)

    def set_quack(self,image):
        frames=split_grid(image.convert("RGBA"))
        if len(frames)<len(self.normal):raise ValueError("Quack texture needs at least as many cells as the normal duck texture.")
        self.quack=frames;self._cache.clear()

    def configure(self,mapping,fps):
        for state in STATES:
            frames=mapping.get(state,[])
            if not frames or len(frames)>128 or any(type(i) is not int or not 0<=i<len(self.normal) for i in frames):
                raise ValueError(f"{state.title()}: enter frame indices from 0 to {len(self.normal)-1}.")
            if not 0.1<=fps.get(state,0)<=60:raise ValueError(f"{state.title()}: speed must be between 0.1 and 60 fps.")
        self.mapping=copy.deepcopy(mapping);self.fps=dict(fps)

    def frame_index(self,state,clock):
        indices=self.mapping[state]
        offset=int(max(0,clock)*self.fps[state])
        if state in ("jump","fall","crouch"):offset=min(offset,len(indices)-1)
        else:offset%=len(indices)
        return indices[offset]

    def frame(self,state,clock,quacking,color,tint):
        index=self.frame_index(state,clock)
        use_quack=bool(quacking and index<len(self.quack))
        original=(self.quack if use_quack else self.normal)[index]
        key=(use_quack,index,color)
        if key not in self._cache:self._cache[key]=tint(original,color)
        return self._cache[key],head_anchor(original)
