"""Small deterministic-step preview engine, rendered with Pillow (no GUI needed)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageOps

from .model import ASSETS, evaluate
from .sprites import DuckSprites, head_anchor

COLORS = {
    "White": ((255,255,255),(157,157,157)), "Yellow": ((247,224,90),(174,158,63)),
    "Brown": ((205,107,29),(142,75,20)), "Gray": ((126,126,126),(87,87,87)),
    "Pink": ((255,104,116),(207,82,93)), "Blue": ((47,161,242),(8,123,182)),
    "Purple": ((176,86,222),(142,36,196)), "Green": ((0,134,74),(0,102,57)),
}
NEAREST = Image.Resampling.NEAREST


def clamp(value, low=0, high=1):
    return max(low, min(high, value))


def tint(image, color):
    result = image.copy()
    primary, shadow = COLORS[color]
    pixels = []
    for r,g,b,a in image.get_flattened_data():
        rgb = primary if (r,g,b)==(255,255,255) else shadow if (r,g,b)==(157,157,157) else (r,g,b)
        pixels.append((*rgb,a))
    result.putdata(pixels)
    return result


def opacity(image, value):
    if value >= 1:
        return image
    result = image.copy()
    result.putalpha(result.getchannel("A").point(lambda alpha: round(alpha*clamp(value))))
    return result


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    values: dict
    frame: int
    origin: tuple
    age: float = 0


class Preview:
    width, height, floor = 384, 240, 177

    def __init__(self, hat, seed=None):
        self.random = random.Random(seed)
        with Image.open(ASSETS / "duck.png") as image:
            self.original_duck = image.convert("RGBA")
        self.sprites = DuckSprites([self.original_duck])
        self.reference_head = head_anchor(self.original_duck)
        self.animation_state, self.animation_clock = "idle", 0.
        self.walking, self.crouching, self.quack_held = False, False, False
        self.vx = 0.
        self.color, self.zoom = "White", 2
        self.paused, self.running, self.auto_quack, self.grid = False, False, False, False
        self.facing, self.x, self.y, self.vy = 1, 192., float(self.floor), 0.
        self.time, self.quacking, self.since_emit = 0., 0., 0.
        self.accumulator = 0.
        self.direction = 0
        self.particles, self.trail = [], []
        self.set_hat(hat)

    def set_hat(self, hat):
        self.hat = hat
        self.particles, self.trail = [], []
        self.rebuild()

    def rebuild(self):
        self.values = evaluate(self.hat.slots, lambda: .5)
        self.sheet = tint(self.hat.artwork, self.color) if 2 in self.values else self.hat.artwork
        self.duck = tint(self.original_duck, self.color)
        # Duck Game treats magenta as transparent. Never alter exported artwork.
        self.sheet = self.sheet.copy()
        self.sheet.putdata([(r,g,b,0 if (r,g,b)==(255,0,255) else a)
                            for r,g,b,a in self.sheet.get_flattened_data()])
        self.frames = []
        if self.hat.height >= 56 and self.hat.width > 32:
            for x,y in ((24,32),(36,32),(24,44),(36,44)):
                frame = self.sheet.crop((x,y,x+12,y+12))
                if frame.getchannel("A").getbbox():
                    self.frames.append(frame)
        if not self.frames:
            self.particles.clear()

    def jump(self):
        if self.y >= self.floor:
            self.vy = -100. * self.zoom

    def quack(self):
        self.quacking = .3
        if not self.frames:
            return
        base = evaluate(self.hat.slots, self.random.random)
        preset = base.get(31, [0, 0])[1]
        if 31 in base and preset == 0:
            return
        count = (8 if preset==3 else 1 if preset==4 else 6) if preset else round(clamp(base.get(34,[4,0])[0],0,8))
        for i in range(count):
            values = evaluate(self.hat.slots, self.random.random)
            if preset:
                values = {k:v for k,v in values.items() if not 30<=k<=48}
                values.update({35:[1.2,0],40:[.65,.15],39:[1,0]})
            ox,oy = values.get(30,[0,0]); dx,dy = values.get(42,[0,0]); ox+=dx;oy+=dy
            shape,distribution = values.get(32,[0,0]); sx,sy=map(abs,values.get(33,[8,8]))
            t = i/max(1,count) if distribution==2 else self.random.random()
            if shape==1:
                radius=math.sqrt(self.random.random()) if distribution==1 else 1
                ox+=math.cos(t*math.tau)*sx*radius;oy+=math.sin(t*math.tau)*sy*radius
            elif shape==2:
                if distribution==1:
                    ox+=(self.random.random()*2-1)*sx;oy+=(self.random.random()*2-1)*sy
                else:
                    side=int(t*4)%4;f=t*4-int(t*4)
                    ox+=(-sx+f*2*sx,sx,sx-f*2*sx,-sx)[side]
                    oy+=(-sy,-sy+f*2*sy,sy,sy-f*2*sy)[side]
            vx,vy=values.get(36,[.4,-.7])
            if preset==1: vx,vy=1.8,-.1
            elif preset==2: vx,vy=math.cos(i/count*math.tau)*1.2,math.sin(i/count*math.tau)*1.2
            elif preset==3: ox,oy,vx,vy=math.cos(i/count*math.tau)*12,math.sin(i/count*math.tau)*4-8,0,-.1
            elif preset==4: oy,vx,vy=-12,0,-.2
            hx,hy=self.values.get(1,[0,0]); ax,ay=self.current_head_offset(); hx=ax-hx;hy=ay-hy
            self.particles.append(Particle(self.x+(hx+ox)*self.zoom*self.facing,self.y+(-23+hy+oy)*self.zoom,
                                           vx*self.facing,vy,values.get(35,[1.2,0])[0],values,
                                           self.random.randrange(max(1,len(self.frames))),(self.x,self.y)))
        self.particles=self.particles[-512:]

    def advance(self, seconds):
        if self.paused:
            return
        self.accumulator+=clamp(seconds,0,.1)
        while self.accumulator>=1/60:
            self.step(1/60)
            self.accumulator-=1/60

    def step(self, dt):
        self.time+=dt;self.since_emit+=dt;self.quacking=max(0,self.quacking-dt)
        direction=0 if self.crouching else self.direction or (self.facing if self.running else 0)
        speed=(22.5 if self.walking else 45.)*self.zoom
        target=direction*speed
        acceleration=(300. if direction else 420.)*self.zoom
        self.vx+=clamp(target-self.vx,-acceleration*dt,acceleration*dt)
        if direction:self.facing=direction
        self.x+=self.vx*dt
        if self.x>330:self.x,self.facing,self.vx=330,-1,0.
        elif self.x<54:self.x,self.facing,self.vx=54,1,0.
        self.vy+=300.*self.zoom*dt;self.y=min(self.floor,self.y+self.vy*dt)
        if self.y==self.floor:self.vy=0
        state=("jump" if self.vy<0 else "fall") if self.y<self.floor else "crouch" if self.crouching else ("walk" if self.walking else "run") if abs(self.vx)>.5 else "idle"
        if state!=self.animation_state:self.animation_state,self.animation_clock=state,0.
        self.animation_clock+=dt*(abs(self.vx)/speed if state in ("walk","run") else 1)
        if self.quack_held:self.quacking=max(self.quacking,.1)
        if self.auto_quack and self.since_emit>.85:
            self.quack();self.since_emit=0
        self.trail.insert(0,(self.x,self.y-21*self.zoom));self.trail=self.trail[:80]
        for particle in self.particles:
            gx,gy=particle.values.get(37,[0,.06]);fx,fy=particle.values.get(38,[1,1])
            particle.age+=dt
            particle.vx=(particle.vx+gx*dt*8)*clamp(fx)**(dt*60)
            particle.vy=(particle.vy+gy*dt*8)*clamp(fy)**(dt*60)
            particle.x+=particle.vx*dt*60*self.zoom;particle.y+=particle.vy*dt*60*self.zoom
        self.particles=[p for p in self.particles if p.age<p.life]

    def sprite(self, image, source, x, y, scale=1, mirror=False, alpha=1, rotation=0):
        if scale<=0 or alpha<=0: return
        w,h=max(1,round(source.width*scale)),max(1,round(source.height*scale))
        sprite=source.resize((w,h),NEAREST)
        if mirror: sprite=ImageOps.mirror(sprite)
        if alpha<1: sprite=opacity(sprite,alpha)
        if rotation:
            rotated=sprite.rotate(-math.degrees(rotation),resample=NEAREST,expand=True)
            x-=(rotated.width-w)/2;y-=(rotated.height-h)/2;sprite=rotated
        image.alpha_composite(sprite,(round(x),round(y)))

    def render(self):
        image=Image.new("RGBA",(self.width,self.height),"#111e23");draw=ImageDraw.Draw(image)
        draw.rectangle((0,118,384,180),fill="#16272c")
        for x in range(-20,384,55): draw.rectangle((x,95+x%3*8,x+36,180),fill="#1a2e31")
        for x in range(0,384,24): draw.line((x,180,x-70,240),fill="#20383b")
        for y in range(180,240,12): draw.line((0,y,384,y),fill="#20383b")
        draw.rectangle((0,180,384,182),fill="#3c6252")
        for x in range(0,384,6): draw.rectangle((x,179,x+3,180),fill="#547d61")
        if self.grid:
            for x in range(0,384,8): draw.line((x,0,x,240),fill="#263c3e")
            for y in range(0,240,8): draw.line((0,y,384,y),fill="#263c3e")
        draw.ellipse((self.x-20,176,self.x+20,182),fill="#0c181a")
        self.draw_particles(image,True)
        if 11 not in self.values: self.draw_cape(image)
        frame,anchor=self.sprites.frame(self.animation_state,self.animation_clock,self.quacking>0,self.color,tint)
        body=Image.new("RGBA",(96,96));body.alpha_composite(frame,(32,32))
        hx,hy=self.values.get(1,[0,0])
        hx=anchor[0]-self.reference_head[0]-hx;hy=anchor[1]-self.reference_head[1]-hy
        hat_frame=32 if self.quacking>0 and self.hat.width>=64 else 0
        body.alpha_composite(self.sheet.crop((hat_frame,0,hat_frame+32,32)),(round(32+hx),round(25+hy)))
        self.sprite(image,body,self.x-48*self.zoom,self.y-64*self.zoom,self.zoom,self.facing<0)
        if 11 in self.values: self.draw_cape(image)
        self.draw_particles(image,False)
        return image

    def set_sprites(self,sprites):
        self.sprites=sprites
        self.animation_clock=0.
        self.particles=[]
        self.trail=[]

    def current_head_offset(self):
        _,anchor=self.sprites.frame(self.animation_state,self.animation_clock,self.quacking>0,self.color,tint)
        return (anchor[0]-self.reference_head[0],anchor[1]-self.reference_head[1])

    def draw_cape(self,image):
        if self.hat.width<96: return
        ox,oy=self.values.get(10,[0,0]);ax,ay=self.current_head_offset();ox+=ax;oy+=ay
        sway,weight=self.values.get(12,[.3,1]);wx,wy=self.values.get(13,[.15,.1])
        start=self.values.get(14,[.45,0])[0];end=self.values.get(15,[1,0])[0]
        a0=self.values.get(16,[1,0])[0];a1=self.values.get(17,[1,0])[0]
        for row in range(32):
            f=row/31;alpha=clamp(a0+(a1-a0)*f)
            width=max(0,round((start+(end-start)*f)*18*self.zoom))
            if not width or alpha<=0: continue
            strip=self.sheet.crop((64,row,96,row+1)).resize((width,self.zoom+1),NEAREST)
            if self.facing<0: strip=ImageOps.mirror(strip)
            if 20 in self.values:
                if not self.trail: continue
                px,py=self.trail[min(len(self.trail)-1,row*2)]
                px+=ox*self.zoom*self.facing;py+=oy*self.zoom
            else:
                wind=math.sin(self.time*4-row*.25)*wx*5*f-(f*5 if self.running else 0)
                length=row*.8*weight+math.sin(self.time*3-row*.2)*wy*3*f
                px=self.x+(-5+ox+wind+row*.8*sway)*self.zoom*self.facing
                py=self.y+(-22+oy+length)*self.zoom
            image.alpha_composite(opacity(strip,alpha),(round(px-width/2),round(py)))

    def draw_particles(self,image,background):
        if not self.frames:
            return
        for p in self.particles:
            if (43 in p.values)!=background or p.life<=0: continue
            f=clamp(p.age/p.life);a=p.values.get(39,[1,0]);s=p.values.get(40,[.5,0]);r=p.values.get(41,[0,0])
            scale=max(0,s[0]+(s[1]-s[0])*f)*self.zoom
            if not scale: continue
            frame=p.frame
            if self.frames:
                if 45 in p.values:
                    frame=math.floor(p.age*p.values.get(48,[.5,0])[0]*24)+(p.frame if 47 in p.values else 0)
                    frame=frame%len(self.frames) if 46 in p.values else min(len(self.frames)-1,frame)
                source=self.frames[frame]
            else: continue
            x,y=p.x,p.y
            if 44 in p.values: x+=self.x-p.origin[0];y+=self.y-p.origin[1]
            self.sprite(image,source,x-source.width*scale/2,y-source.height*scale/2,scale,
                        alpha=clamp(a[0]+(a[1]-a[0])*f),rotation=math.radians(10*(r[0]+(r[1]-r[0])*f)))
