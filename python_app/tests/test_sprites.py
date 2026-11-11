import unittest
from PIL import Image, ImageDraw
from duckmeta.sprites import DuckSprites, head_anchor
from duckmeta.model import Hat
from duckmeta.preview import Preview


def duck_grid(count=8):
    image=Image.new('RGBA',(32*count,32))
    draw=ImageDraw.Draw(image)
    for i in range(count):
        x=i*32
        draw.rectangle((x+12,10+i%2,x+20,17+i%2),fill='white')
        draw.rectangle((x+13,19,x+20,27),fill='white')
        draw.rectangle((x+13+i%3,28,x+19+i%3,30),fill=(230,140,30,255))
        draw.point((x+18,12+i%2),fill='black')
    return image


class SpriteTests(unittest.TestCase):
    def test_raw_grid_and_walk_run_rates(self):
        sprites=DuckSprites.from_image(duck_grid())
        self.assertEqual(len(sprites.normal),8)
        self.assertEqual(sprites.frame_index('walk',.2),1)
        self.assertEqual(sprites.frame_index('run',.2),2)
        self.assertEqual(sprites.frame_index('idle',10),0)
        self.assertEqual(sprites.frame_index('jump',10),6)

    def test_reference_layout_excludes_labels_and_loads_quack(self):
        reference=Image.new('RGBA',(387,781),(220,90,100,255))
        normal=Image.new('RGBA',(192,192),(0,0,0,0));normal.paste(duck_grid(6),(0,0))
        reference.paste(normal,(0,8))
        quack=Image.new('RGBA',(192,768),(0,0,0,0));quack.paste(duck_grid(6),(0,0))
        reference.paste(quack,(194,8))
        sprites=DuckSprites.from_image(reference)
        self.assertEqual(len(sprites.normal),36);self.assertEqual(len(sprites.quack),144)
        self.assertEqual(sprites.normal[0].tobytes(),normal.crop((0,0,32,32)).tobytes())
        self.assertEqual(sprites.quack[0].getpixel((0,0)),(0,0,0,0))

    def test_uses_real_quack_frame_not_drawn_beak(self):
        sprites=DuckSprites.from_image(duck_grid())
        quack=duck_grid();quack.putpixel((24,16),(123,45,67,255));sprites.set_quack(quack)
        identity=lambda image,color:image
        normal,_=sprites.frame('idle',0,False,'White',identity)
        quacking,_=sprites.frame('idle',0,True,'White',identity)
        self.assertEqual(normal.getpixel((24,16)),(0,0,0,0))
        self.assertEqual(quacking.getpixel((24,16)),(123,45,67,255))

    def test_head_anchor_follows_vertical_frame_motion(self):
        sprites=DuckSprites.from_image(duck_grid())
        self.assertEqual(head_anchor(sprites.normal[1])[1]-head_anchor(sprites.normal[0])[1],1)
        preview=Preview(Hat.example());preview.set_sprites(sprites)
        preview.animation_state='run';preview.animation_clock=0
        first=preview.current_head_offset()
        preview.animation_clock=1/12
        self.assertEqual(preview.current_head_offset()[1]-first[1],1)

    def test_tunable_mapping_and_invalid_input(self):
        sprites=DuckSprites.from_image(duck_grid())
        mapping=dict(sprites.mapping);mapping['run']=[3,2,1]
        sprites.configure(mapping,sprites.fps);self.assertEqual(sprites.frame_index('run',0),3)
        mapping['run']=[99]
        with self.assertRaises(ValueError):sprites.configure(mapping,sprites.fps)
        self.assertEqual(sprites.mapping['run'],[3,2,1])
        with self.assertRaises(ValueError):DuckSprites.from_image(Image.new('RGBA',(33,32)))
        with self.assertRaises(ValueError):sprites.set_quack(Image.new('RGBA',(32,32)))

    def test_preview_accelerates_walks_runs_jumps_and_crouches(self):
        preview=Preview(Hat.example());preview.set_sprites(DuckSprites.from_image(duck_grid()))
        preview.running=True;preview.walking=True
        preview.advance(1/60);first_speed=preview.vx
        for _ in range(20):preview.advance(1/60)
        self.assertGreater(preview.vx,first_speed);self.assertEqual(preview.animation_state,'walk')
        walk_speed=preview.vx;preview.walking=False
        for _ in range(20):preview.advance(1/60)
        self.assertGreater(preview.vx,walk_speed);self.assertEqual(preview.animation_state,'run')
        preview.running=False;preview.crouching=True;preview.advance(1/60)
        self.assertEqual(preview.animation_state,'crouch')
        preview.crouching=False;preview.jump();preview.advance(1/60)
        self.assertEqual(preview.animation_state,'jump')
        for _ in range(25):preview.advance(1/60)
        self.assertEqual(preview.animation_state,'fall')
        preview.quack_held=True
        for _ in range(30):preview.advance(1/60)
        self.assertGreater(preview.quacking,0)
