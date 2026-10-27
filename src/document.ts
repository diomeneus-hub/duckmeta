import { decode, encode, convertIndexedToRgb } from 'fast-png';
import { byId, decodeValue } from './meta.ts';
export type Pixel = [number,number,number,number];
export interface HatDocument {name:string; width:number; height:number; artwork:Uint8Array; slots:Pixel[]; hadMeta:boolean}
export function loadPng(bytes: Uint8Array, name:string):HatDocument {
 // Bound allocations before decoding compressed pixel data.
 if(bytes.length<24 || bytes.length>8*1024*1024) throw new Error('Choose a PNG smaller than 8 MB.');
 const header=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 const w=header.getUint32(16),h=header.getUint32(20);
 if(w>1025 || h>1024 || w<32 || h<32) throw new Error('Hat sheets must be 32–1024 pixels tall and at most 1025 pixels wide.');
 if(w%32!==0 && w%32!==1) throw new Error('Expected 32-pixel columns, with an optional single metapixel column (for example 96 or 97 pixels wide).');
 const png=decode(bytes,{checkCrc:true});
 if(png.depth!==8 && !png.palette) throw new Error('Use an 8-bit RGB/RGBA or indexed PNG. 16-bit artwork is not converted silently.');
 const source=png.palette?convertIndexedToRgb(png):png.data;
 const channels=png.palette?png.palette[0].length:png.channels;
 const rgba=new Uint8Array(w*h*4);
 for(let i=0;i<w*h;i++) {
  const s=i*channels,t=i*4;
  rgba[t]=source[s];rgba[t+1]=channels<3?source[s]:source[s+1];rgba[t+2]=channels<3?source[s]:source[s+2];
  rgba[t+3]=channels===2?source[s+1]:channels===4?source[s+3]:255;
  if(!png.palette && png.transparency && (channels===1?source[s]===png.transparency[0]:channels===3&&source[s]===png.transparency[0]&&source[s+1]===png.transparency[1]&&source[s+2]===png.transparency[2])) rgba[t+3]=0;
 }
 const hadMeta=w%32===1,width=hadMeta?w-1:w;
 const artwork=new Uint8Array(width*h*4),slots:Pixel[]=[];
 for(let y=0;y<h;y++) {
  artwork.set(rgba.subarray(y*w*4,(y*w+width)*4),y*width*4);
  slots.push(hadMeta?Array.from(rgba.subarray((y*w+width)*4,(y*w+width+1)*4)) as Pixel:[0,0,0,0]);
 }
 return {name,width,height:h,artwork,slots,hadMeta};
}
export function exportPng(doc:HatDocument):Uint8Array {
 const width=doc.width+1,data=new Uint8Array(width*doc.height*4);
 for(let y=0;y<doc.height;y++) {
  data.set(doc.artwork.subarray(y*doc.width*4,(y+1)*doc.width*4),y*width*4);
  data.set(doc.slots[y],(y*width+doc.width)*4);
 }
 return encode({width,height:doc.height,data,channels:4,depth:8});
}
export const active = (p:Pixel)=>p[3]>0;
export const cloneSlots=(slots:Pixel[])=>slots.map(p=>[...p] as Pixel);
export function insertMeta(doc:HatDocument,id:number,after:number):number {
 const def=byId.get(id);if(!def) throw new Error('Unknown modifier.');
 const start=Math.min(doc.height-1,Math.max(0,after+1));
 let free=doc.slots.findIndex((p,i)=>i>=start&&!active(p)&&p.every(v=>v===0));
 if(free<0) throw new Error('No empty rows after this selection. Select an earlier row or remove a modifier.');
 for(let i=free;i>start;i--) doc.slots[i]=doc.slots[i-1];
 doc.slots[start]=[id,...def.defaults,255];return start;
}
export function evaluate(slots:Pixel[],random:()=>number=Math.random):Map<number,[number,number]> {
 const result=new Map<number,[number,number]>();let previous:number|undefined;
 for(const [id,g,b,a] of slots) {
  if(!a) continue;
  if(id>=100&&id<=102) {
   if(previous===undefined || !result.has(previous)) continue;
   const lo=g/255*2-1,hi=b/255*2-1,v=result.get(previous)!;
   const sample=()=>lo+random()*(hi-lo);
   if(id===100||id===102) v[0]*=sample();
   if(id===101||id===102) v[1]*=sample();
  } else {
   previous=id;const def=byId.get(id);
   if(def) result.set(id,[decodeValue(def,g),decodeValue(def,b)]);
  }
 }
 return result;
}
