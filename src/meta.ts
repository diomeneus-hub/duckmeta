export type Kind = 'VEC' | 'NVEC' | 'NNVEC' | 'FLOAT' | 'NFLOAT' | 'INT' | 'BOOL' | 'SPECIAL';
export type Group = 'Hat' | 'Cape' | 'Particles' | 'Quack' | 'Randomizers';
export interface Definition { id: number; name: string; group: Group; kind: Kind; max: number; labels: string[]; defaults: [number, number]; description: string; choices?: Record<number, string[]> }
const d = (id: number, name: string, group: Group, kind: Kind, max: number, labels: string[], defaults: [number, number], description: string, choices?: Record<number,string[]>): Definition => ({id,name,group,kind,max,labels,defaults,description,choices});
export const definitions: Definition[] = [
 d(1,'Hat offset','Hat','VEC',16,['Horizontal','Vertical'],[128,128],'Move the hat relative to the duck’s head. 128 encodes zero offset.'),
 d(2,'Use duck color','Hat','BOOL',1,[],[0,0],'Replace pure white and gray (157,157,157) in the hat with the selected duck colors.'),
 d(10,'Cape offset','Cape','VEC',16,['Horizontal','Vertical'],[128,128],'Move the cape attachment point.'),
 d(11,'Cape in foreground','Cape','BOOL',1,[],[0,0],'Draw the cape in front of the duck.'),
 d(12,'Cape sway','Cape','NNVEC',1,['Rotation','Weight'],[128,220],'Adjust cape rotation and weight. Preview uses an approximate cloth simulation.'),
 d(13,'Cape wiggle','Cape','NNVEC',1,['Horizontal','Vertical'],[170,150],'Adjust how much wind moves the cape.'),
 d(14,'Cape taper · start','Cape','FLOAT',1,['Width'],[128,0],'Width at the cape attachment, normalized from 0 to 1.'),
 d(15,'Cape taper · end','Cape','FLOAT',1,['Width'],[255,0],'Width at the bottom of the cape.'),
 d(16,'Cape alpha · start','Cape','FLOAT',1,['Opacity'],[255,0],'Opacity at the cape attachment.'),
 d(17,'Cape alpha · end','Cape','FLOAT',1,['Opacity'],[255,0],'Opacity at the bottom of the cape.'),
 d(20,'Cape as trail','Cape','BOOL',1,[],[0,0],'Render the cape along the duck’s recent path instead of hanging cloth.'),
 d(30,'Emitter offset','Particles','VEC',16,['Horizontal','Vertical'],[128,128],'Particle spawn position relative to the hat. This preview follows the reference’s signed VEC definition.'),
 d(31,'Particle preset','Particles','SPECIAL',4,['Unused G','Behavior'],[0,2],'Preset behavior overrides custom particle modifiers. Preview presets are approximations.',{1:['None','Spit','Burst','Halo','Exclamation']}),
 d(32,'Emitter shape','Particles','SPECIAL',2,['Shape','Distribution'],[1,0],'Choose a point, circle, or box and how particles fill it.',{0:['Point','Circle','Box'],1:['Random edges','Random fill','Uniform edges']}),
 d(33,'Emitter size','Particles','VEC',24,['Horizontal','Vertical'],[136,136],'Size of the emitter shape; preview uses the absolute decoded dimensions.'),
 d(34,'Particle count','Particles','INT',8,['Count'],[134,0],'Particles per quack. G minus 128, clamped to ±8. Negative counts emit nothing.'),
 d(35,'Particle lifespan','Particles','FLOAT',2,['Seconds'],[170,0],'Time before particles disappear.'),
 d(36,'Particle velocity','Particles','NNVEC',2,['Horizontal','Vertical'],[150,75],'Initial velocity of the particles.'),
 d(37,'Particle gravity','Particles','NNVEC',2,['Horizontal','Vertical'],[128,140],'Acceleration applied to particles.'),
 d(38,'Particle friction','Particles','NVEC',1,['Horizontal','Vertical'],[250,250],'Velocity multiplier each simulation frame. 255 keeps full velocity.'),
 d(39,'Particle alpha','Particles','NVEC',1,['Start','End'],[255,0],'Opacity over the particle’s lifetime.'),
 d(40,'Particle scale','Particles','NVEC',2,['Start','End'],[100,0],'Size over the particle’s lifetime.'),
 d(41,'Particle rotation','Particles','NVEC',36,['Start','End'],[0,40],'Rotation over the particle’s lifetime. The reference does not specify units; preview uses radians.'),
 d(42,'Particle offset','Particles','VEC',16,['Horizontal','Vertical'],[128,128],'Additional offset for particles.'),
 d(43,'Particles behind duck','Particles','BOOL',1,[],[0,0],'Render particles behind the duck.'),
 d(44,'Anchor particles','Particles','BOOL',1,[],[0,0],'Particles follow the hat as the duck moves.'),
 d(45,'Animate particles','Particles','BOOL',1,[],[0,0],'Animate through the 24 × 24 frames beneath the hat.'),
 d(46,'Loop particle animation','Particles','BOOL',1,[],[0,0],'Loop the animation instead of stopping on the last frame.'),
 d(47,'Random animation start','Particles','BOOL',1,[],[0,0],'Start animated particles on a random frame.'),
 d(48,'Particle animation speed','Particles','FLOAT',1,['Speed'],[128,0],'Normalized speed, mapped to 0–24 frames per second.'),
 d(70,'Wet lips','Quack','BOOL',1,[],[0,0],'Changes the game’s quack sound. Export supported; original game audio is not included.'),
 d(71,'Mechanical lips','Quack','BOOL',1,[],[0,0],'Changes the game’s quack sound. Export supported; original game audio is not included.'),
 ...([100,101,102] as const).map((id)=>d(id,`Randomize ${id===100?'X':id===101?'Y':'X + Y'}`,'Randomizers','NNVEC',1,['Minimum multiplier','Maximum multiplier'],[128,255],'Multiplies the preceding non-randomizer’s decoded parameter(s) by a random value in this range. Order matters. Particle parameters are sampled per spawn.')),
];
export const byId = new Map(definitions.map(d=>[d.id,d]));
export const clamp = (n:number, a:number, b:number)=>Math.max(a, Math.min(b,n));
export function decodeValue(def: Definition, raw: number): number {
 switch(def.kind) {
  case 'VEC': case 'INT': return clamp(raw-128,-def.max,def.max);
  case 'NVEC': case 'FLOAT': return raw/255*def.max;
  case 'NNVEC': case 'NFLOAT': return (raw/255*2-1)*def.max;
  default: return raw;
 }
}
export function rawBounds(def: Definition): [number, number] { return ['VEC','INT'].includes(def.kind) ? [128-def.max,128+def.max] : [0,255]; }
export function displayValue(def:Definition, raw:number):string {
 const v=decodeValue(def,raw);
 if(def.id===48) return `${(v*24).toFixed(1)} fps`;
 if(['VEC','INT','SPECIAL'].includes(def.kind)) return String(v);
 return v.toFixed(2);
}
