import { evaluate, type HatDocument } from './document.ts';
import { clamp } from './meta.ts';
export const colors:Record<string,[string,string]>={White:['#ffffff','#9d9d9d'],Yellow:['#f7e05a','#ae9e3f'],Brown:['#cd6b1d','#8e4b14'],Gray:['#7e7e7e','#575757'],Pink:['#ff6874','#cf525d'],Blue:['#2fa1f2','#087bb6'],Purple:['#b056de','#8e24c4'],Green:['#00864a','#006639']};
interface Particle {x:number;y:number;vx:number;vy:number;age:number;life:number;values:Map<number,[number,number]>;frame:number;anchor:boolean;originX:number;originY:number;back:boolean}
function surface(w:number,h:number){const c=document.createElement('canvas');c.width=w;c.height=h;return c;}
export class Preview {
 canvas:HTMLCanvasElement;ctx:CanvasRenderingContext2D;doc!:HatDocument;sheet!:HTMLCanvasElement;duckSource!:HTMLImageElement;duck!:HTMLCanvasElement;
 frameCount=1;color='White'; paused=false; motion='idle'; facing=1; grid=false; showCape=true; showParticles=true; autoQuack=false; zoom=2; time=0;x=192;y=177;vy=0;quacking=0; particles:Particle[]=[]; keys=new Set<string>();trail:{x:number;y:number}[]=[]; lastEmit=0;last=0;accumulator=0;values=new Map<number,[number,number]>();onStats:(n:number)=>void=()=>{};sound=false;audio?:AudioContext;
 constructor(canvas:HTMLCanvasElement){this.canvas=canvas;this.ctx=canvas.getContext('2d')!;
  canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight',' ','q','Q'].includes(e.key)){e.preventDefault();this.keys.add(e.key);if(e.key===' '&&!e.repeat)this.jump();if(e.key.toLowerCase()==='q'&&!e.repeat)this.quack();}});
  canvas.addEventListener('keyup',e=>this.keys.delete(e.key));canvas.addEventListener('blur',()=>this.keys.clear());
 }
 async init(doc:HatDocument){this.duckSource=new Image();this.duckSource.src='/assets/duck.png';await this.duckSource.decode();this.setDocument(doc);requestAnimationFrame(t=>this.tick(t));}
 setDocument(doc:HatDocument){this.doc=doc;this.particles=[];this.trail=[];this.rebuild();}
 rebuild(){if(!this.doc||!this.duckSource)return;
  this.values=evaluate(this.doc.slots,()=>0.5);
  // Trim only wholly empty trailing particle cells; keep internal blank animation frames.
  this.frameCount=1;
  if(this.doc.height>=56){for(let frame=0;frame<Math.floor(this.doc.width/24);frame++){
   let painted=false;for(let y=32;y<56&&!painted;y++)for(let x=frame*24;x<(frame+1)*24;x++)if(this.doc.artwork[(y*this.doc.width+x)*4+3]){painted=true;break;}
   if(painted)this.frameCount=frame+1;
  }}
  const rgba=new Uint8ClampedArray(this.doc.artwork);if(this.values.has(2))this.recolor(rgba);
  this.sheet=surface(this.doc.width,this.doc.height);this.sheet.getContext('2d')!.putImageData(new ImageData(rgba,this.doc.width,this.doc.height),0,0);
  this.duck=surface(32,32);const c=this.duck.getContext('2d')!;c.drawImage(this.duckSource,0,0);const data=c.getImageData(0,0,32,32);this.recolor(data.data);c.putImageData(data,0,0);
 }
 recolor(data:Uint8ClampedArray){const palette=colors[this.color].map(s=>[parseInt(s.slice(1,3),16),parseInt(s.slice(3,5),16),parseInt(s.slice(5,7),16)]);for(let i=0;i<data.length;i+=4){const shade=data[i]===255&&data[i+1]===255&&data[i+2]===255?0:data[i]===157&&data[i+1]===157&&data[i+2]===157?1:-1;if(shade>=0)data.set(palette[shade],i);}}
 get(id:number,fallback:[number,number]=[0,0]){return this.values.get(id)??fallback;}
 jump(){if(this.y>=177){this.vy=-135;}}
 quack(){this.quacking=0.3;this.emit();if(this.sound)this.beep();}
 beep(){this.audio??=new AudioContext();void this.audio.resume();const o=this.audio.createOscillator(),g=this.audio.createGain(),t=this.audio.currentTime;o.type=this.values.has(71)?'square':'sawtooth';o.frequency.setValueAtTime(this.values.has(70)?380:260,t);o.frequency.exponentialRampToValueAtTime(100,t+0.13);g.gain.setValueAtTime(.035,t);g.gain.exponentialRampToValueAtTime(.001,t+.16);o.connect(g).connect(this.audio.destination);o.start();o.stop(t+.17);}
 emit(){if(!this.showParticles)return;
  const base=evaluate(this.doc.slots),preset=base.get(31)?.[1]??0;
  if(base.has(31)&&preset===0)return;
  const count=preset?preset===3?8:preset===4?1:6:clamp(Math.round(base.get(34)?.[0]??4),0,8);
  for(let i=0;i<count;i++){
   const v=evaluate(this.doc.slots),get=(id:number,f:[number,number]):[number,number]=>v.get(id)??f;
   // Presets override every custom particle setting, as described in the reference.
   if(preset){for(const id of [...v.keys()])if(id>=30&&id<=48)v.delete(id);v.set(35,[1.2,0]);v.set(40,[.65,.15]);v.set(39,[1,0]);}
   let [ox,oy]=get(30,[0,0]);const offset=get(42,[0,0]);ox+=offset[0];oy+=offset[1];
   const [shape,distribution]=get(32,[0,0]),size=get(33,[8,8]);const t=distribution===2?i/Math.max(1,count):Math.random();
   if(shape===1){const radius=distribution===1?Math.sqrt(Math.random()):1;ox+=Math.cos(t*Math.PI*2)*Math.abs(size[0])*radius;oy+=Math.sin(t*Math.PI*2)*Math.abs(size[1])*radius;}
   if(shape===2){const sx=Math.abs(size[0]),sy=Math.abs(size[1]);if(distribution===1){ox+=(Math.random()*2-1)*sx;oy+=(Math.random()*2-1)*sy;}else{const edge=t*4,side=Math.floor(edge),f=edge-side;ox+=side===0?-sx+f*2*sx:side===1?sx:side===2?sx-f*2*sx:-sx;oy+=side===0?-sy:side===1?-sy+f*2*sy:side===2?sy:sy-f*2*sy;}}
   let [vx,vy]=get(36,[.4,-.7]);
   if(preset===1){vx=1.8;vy=-.1;}
   if(preset===2){const a=i/count*Math.PI*2;vx=Math.cos(a)*1.2;vy=Math.sin(a)*1.2;}
   if(preset===3){const a=i/count*Math.PI*2;ox=Math.cos(a)*12;oy=Math.sin(a)*4-8;vx=0;vy=-.1;}
   if(preset===4){oy=-12;vx=0;vy=-.2;}
   const [hx,hy]=this.get(1);const originX=this.x+(ox+hx)*this.zoom*this.facing,originY=this.y+(-23+oy+hy)*this.zoom;
   this.particles.push({x:originX,y:originY,vx:vx*this.facing,vy,age:0,life:get(35,[1.2,0])[0],values:v,frame:Math.floor(Math.random()*this.frameCount),anchor:v.has(44),originX:this.x,originY:this.y,back:v.has(43)});
  }if(this.particles.length>512)this.particles.splice(0,this.particles.length-512);
 }
 update(dt:number){this.time+=dt;this.quacking=Math.max(0,this.quacking-dt);
  const direction=this.keys.has('ArrowRight')?1:this.keys.has('ArrowLeft')?-1:this.motion==='run'?this.facing:0;
  if(direction){this.facing=direction;this.x+=direction*40*dt;if(this.x>330){this.x=330;this.facing=-1;}if(this.x<54){this.x=54;this.facing=1;}}
  this.vy+=370*dt;this.y=Math.min(177,this.y+this.vy*dt);if(this.y===177)this.vy=0;
  if(this.autoQuack&&this.time-this.lastEmit>.85){this.quack();this.lastEmit=this.time;}
  this.trail.unshift({x:this.x,y:this.y-21*this.zoom});if(this.trail.length>80)this.trail.pop();
  for(const p of this.particles){const gravity=p.values.get(37)??[0,.06],friction=p.values.get(38)??[1,1];p.age+=dt;p.vx+=gravity[0]*dt*8;p.vy+=gravity[1]*dt*8;p.vx*=Math.pow(clamp(friction[0],0,1),dt*60);p.vy*=Math.pow(clamp(friction[1],0,1),dt*60);p.x+=p.vx*dt*60*this.zoom;p.y+=p.vy*dt*60*this.zoom;}
  this.particles=this.particles.filter(p=>p.age<p.life);this.onStats(this.particles.length);
 }
 tick(now:number){const elapsed=this.last?Math.min(.1,(now-this.last)/1000):0;this.last=now;
  if(!this.paused){this.accumulator+=elapsed;while(this.accumulator>=1/60){this.update(1/60);this.accumulator-=1/60;}}
  this.draw();requestAnimationFrame(t=>this.tick(t));
 }
 draw(){if(!this.sheet)return;const c=this.ctx;c.setTransform(this.canvas.width/384,0,0,this.canvas.height/240,0,0);c.imageSmoothingEnabled=false;
  c.fillStyle='#111e23';c.fillRect(0,0,384,240);
  // A deliberately quiet pixel-art test room keeps the hat readable.
  c.fillStyle='#16272c';c.fillRect(0,118,384,62);c.fillStyle='#1a2e31';for(let x=-20;x<384;x+=55){c.fillRect(x,95+(x%3)*8,36,85);}
  c.strokeStyle='#20383b';c.lineWidth=.5;for(let x=0;x<384;x+=24){c.beginPath();c.moveTo(x,180);c.lineTo(x-70,240);c.stroke();}for(let y=180;y<240;y+=12){c.beginPath();c.moveTo(0,y);c.lineTo(384,y);c.stroke();}
  c.fillStyle='#3c6252';c.fillRect(0,180,384,2);c.fillStyle='#203d34';c.fillRect(0,182,384,3);
  c.fillStyle='#547d61';for(let x=0;x<384;x+=6)c.fillRect(x,179,3,1);
  if(this.grid){c.strokeStyle='#6b8b8225';for(let x=0;x<384;x+=8){c.beginPath();c.moveTo(x,0);c.lineTo(x,240);c.stroke();}for(let y=0;y<240;y+=8){c.beginPath();c.moveTo(0,y);c.lineTo(384,y);c.stroke();}}
  c.fillStyle='#080f1480';c.beginPath();c.ellipse(this.x,179,20,3,0,0,Math.PI*2);c.fill();
  this.drawParticles(true);if(!this.values.has(11))this.drawCape();
  const moving=this.motion==='run'||this.keys.has('ArrowLeft')||this.keys.has('ArrowRight');const bob=moving?Math.round(Math.sin(this.time*18)):.35*Math.sin(this.time*3);
  c.save();c.translate(Math.round(this.x),Math.round(this.y+bob));c.scale(this.zoom*this.facing,this.zoom);
  c.drawImage(this.duck,-16,-32);
  if(moving&&this.y===177){c.fillStyle='#e99b39';const foot=Math.sin(this.time*18)*2;c.fillRect(-2+foot,-2,5,2);c.fillRect(4-foot,-2,4,2);}
  if(this.quacking>0){c.fillStyle='#e99b39';c.fillRect(6,-13,8,2);c.fillStyle='#392622';c.fillRect(7,-15,7,1);}
  const [hx,hy]=this.get(1);const frame=this.quacking>0&&this.doc.width>=64?32:0;c.drawImage(this.sheet,frame,0,32,32,Math.round(-16+hx),Math.round(-39+hy),32,32);
  c.restore();if(this.values.has(11))this.drawCape();this.drawParticles(false);
 }
 drawCape(){if(!this.showCape||this.doc.width<96)return;
  const c=this.ctx,[ox,oy]=this.get(10),[sway,weight]=this.get(12,[0,.7]),[wiggleX,wiggleY]=this.get(13,[.15,.1]);
  const start=this.get(14,[.45,0])[0],end=this.get(15,[1,0])[0],a0=this.get(16,[1,0])[0],a1=this.get(17,[1,0])[0];
  c.save();if(this.values.has(20)){
   for(let row=31;row>=0;row--){const p=this.trail[Math.min(this.trail.length-1,row*2)];if(!p)continue;const f=row/31,w=Math.max(0,(start+(end-start)*f)*16*this.zoom);if(!w)continue;c.globalAlpha=clamp(a0+(a1-a0)*f,0,1);c.drawImage(this.sheet,64,row,32,1,p.x+ox*this.zoom-w/2,p.y+oy*this.zoom,w,this.zoom+1);}
  }else{
   c.translate(this.x+(-5+ox)*this.zoom*this.facing,this.y+(-22+oy)*this.zoom);c.scale(this.zoom*this.facing,this.zoom);c.rotate(sway*1.8);
   for(let row=0;row<32;row++){const f=row/31,w=Math.max(0,(start+(end-start)*f)*18);if(!w)continue;const wind=Math.sin(this.time*4-row*.25)*wiggleX*5*f-(this.motion==='run'?f*5:0);c.globalAlpha=clamp(a0+(a1-a0)*f,0,1);c.drawImage(this.sheet,64,row,32,1,wind-w/2,row*(.25+.55*Math.abs(weight))*(weight<0?-1:1)+Math.sin(this.time*3-row*.2)*wiggleY*3*f,w,1);}
  }c.restore();
 }
 drawParticles(back:boolean){if(!this.showParticles)return;const c=this.ctx;
  for(const p of this.particles){if(p.back!==back)continue;const f=clamp(p.age/p.life,0,1),a=p.values.get(39)??[1,0],s=p.values.get(40)??[.5,0],r=p.values.get(41)??[0,0],size=Math.max(0,s[0]+(s[1]-s[0])*f);if(size===0)continue;
   c.save();c.globalAlpha=clamp(a[0]+(a[1]-a[0])*f,0,1);c.translate(p.x+(p.anchor?this.x-p.originX:0),p.y+(p.anchor?this.y-p.originY:0));c.rotate(r[0]+(r[1]-r[0])*f);c.scale(size*this.zoom,size*this.zoom);
   const frames=this.frameCount;let frame=p.frame;if(p.values.has(45)){frame=Math.floor(p.age*(p.values.get(48)?.[0]??.5)*24)+(p.values.has(47)?p.frame:0);frame=p.values.has(46)?frame%frames:Math.min(frames-1,frame);}
   if(this.doc.height>=56)c.drawImage(this.sheet,frame*24,32,24,24,-12,-12,24,24);else{c.fillStyle='#ffd172';c.fillRect(-1,-1,3,3);}c.restore();
  }
 }
}
