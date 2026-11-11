"""Layered pixel artwork, reversible strokes, and portable project files."""
import io
import json
import zipfile
from dataclasses import dataclass
from PIL import Image, ImageDraw


@dataclass
class Layer:
    name: str
    image: Image.Image
    visible: bool = True
    opacity: int = 255


def regions(width,height):
    candidates=[('Idle',0,0,32,32),('Quack',32,0,64,32),('Cape',64,0,96,32),
                ('Rock',0,32,24,56),('FX 1',24,32,36,44),('FX 2',36,32,48,44),
                ('FX 3',24,44,36,56),('FX 4',36,44,48,56)]
    return [(name,x,y,min(right,width),min(bottom,height)) for name,x,y,right,bottom in candidates if x<width and y<height]


class Artwork:
    def __init__(self,image):
        self.size=image.size
        self.layers=[Layer('Original artwork',image.copy())]
        self.active=0
        self.past=[];self.future=[]

    def snapshot(self):
        return ([Layer(l.name,l.image.copy(),l.visible,l.opacity) for l in self.layers],self.active)

    def record(self):
        self.past.append(self.snapshot());self.future.clear()
        while len(self.past)>1 and (len(self.past)>30 or sum(len(s[0])*self.size[0]*self.size[1]*4 for s in self.past)>64*1024*1024):self.past.pop(0)

    def undo(self):
        if not self.past:return False
        self.future.append(self.snapshot());self.layers,self.active=self.past.pop();return True

    def redo(self):
        if not self.future:return False
        self.past.append(self.snapshot());self.layers,self.active=self.future.pop();return True

    def composite(self):
        visible=[l for l in self.layers if l.visible and l.opacity]
        if len(visible)==1 and visible[0].opacity==255:return visible[0].image.copy()
        result=Image.new('RGBA',self.size)
        for layer in visible:
            image=layer.image
            if layer.opacity!=255:
                image=image.copy();image.putalpha(image.getchannel('A').point(lambda a:a*layer.opacity//255))
            result.alpha_composite(image)
        return result

    def stroke(self,start,end,color,erase=False):
        image=self.layers[self.active].image
        ImageDraw.Draw(image).line([start,end],fill=(0,0,0,0) if erase else color,width=1)

    def fill(self,point,color):
        ImageDraw.floodfill(self.layers[self.active].image,point,color,thresh=0)

    def add(self):
        if len(self.layers)>=16:raise ValueError('A project supports up to 16 layers.')
        self.record();self.layers.append(Layer(f'Layer {len(self.layers)+1}',Image.new('RGBA',self.size)));self.active=len(self.layers)-1

    def remove(self):
        if len(self.layers)==1:raise ValueError('Keep at least one layer. Use the eraser to clear it.')
        self.record();self.layers.pop(self.active);self.active=min(self.active,len(self.layers)-1)

    def move(self,delta):
        target=self.active+delta
        if 0<=target<len(self.layers):
            self.record();self.layers[self.active],self.layers[target]=self.layers[target],self.layers[self.active];self.active=target

    def project(self,slots):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
            manifest={'version':1,'size':self.size,'active':self.active,'slots':slots,'layers':[]}
            for i,layer in enumerate(self.layers):
                name=f'layers/{i}.png';data=io.BytesIO();layer.image.save(data,format='PNG');archive.writestr(name,data.getvalue())
                manifest['layers'].append({'name':layer.name,'file':name,'visible':layer.visible,'opacity':layer.opacity})
            archive.writestr('project.json',json.dumps(manifest))
        return buffer.getvalue()

    @classmethod
    def load(cls,data):
        if len(data)>64*1024*1024:raise ValueError('Project exceeds 64 MB.')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if len(archive.infolist())>17 or sum(i.file_size for i in archive.infolist())>72*1024*1024:raise ValueError('Project expands beyond supported limits.')
            if archive.getinfo('project.json').file_size>128*1024:raise ValueError('Project manifest is too large.')
            manifest=json.loads(archive.read('project.json'))
            width,height=manifest['size']
            if manifest['version']!=1 or type(width)!=int or type(height)!=int or not 32<=width<=1024 or width%32 or not 32<=height<=1024:raise ValueError('Unsupported project dimensions or version.')
            entries=manifest['layers']
            if not 1<=len(entries)<=16:raise ValueError('Invalid layer count.')
            layers=[]
            for i,entry in enumerate(entries):
                if entry['file']!=f'layers/{i}.png' or not isinstance(entry['name'],str) or len(entry['name'])>100 or type(entry['visible'])!=bool or type(entry['opacity'])!=int or not 0<=entry['opacity']<=255:raise ValueError('Invalid layer settings.')
                with Image.open(io.BytesIO(archive.read(entry['file']))) as image:
                    if image.size!=(width,height):raise ValueError('Layer dimensions do not match.')
                    layers.append(Layer(entry['name'],image.convert('RGBA'),entry['visible'],entry['opacity']))
            slots=manifest['slots']
            if len(slots)!=height or any(not isinstance(p,list) or len(p)!=4 or any(type(v)!=int or not 0<=v<=255 for v in p) for p in slots):raise ValueError('Invalid metadata.')
            active=manifest['active']
            if type(active)!=int or not 0<=active<len(layers):raise ValueError('Invalid active layer.')
            result=cls(layers[0].image);result.layers=layers;result.active=active
            return result,[tuple(p) for p in slots]
