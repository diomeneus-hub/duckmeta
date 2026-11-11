import unittest
from duckmeta.model import EMPTY, Hat
from duckmeta.preview import Preview


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.hat=Hat.example();self.preview=Preview(self.hat,seed=2)

    def test_move_jump_and_return_to_ground(self):
        self.preview.running=True
        for _ in range(30):self.preview.advance(1/60)
        self.assertGreater(self.preview.x,192)
        self.preview.jump();self.preview.advance(1/60);self.assertLess(self.preview.y,self.preview.floor)
        for _ in range(120):self.preview.advance(1/60)
        self.assertEqual(self.preview.y,self.preview.floor)

    def test_paused_render_and_live_offset(self):
        self.preview.paused=True;before=self.preview.render().tobytes()
        self.preview.advance(.1);self.assertEqual(self.preview.render().tobytes(),before)
        self.hat.slots[0]=(1,144,128,255);self.preview.rebuild();self.assertNotEqual(self.preview.render().tobytes(),before)
        self.hat.slots[0]=(1,128,128,255);self.preview.rebuild();self.assertEqual(self.preview.render().tobytes(),before)

    def test_duck_color_and_mirroring(self):
        before=self.preview.render().tobytes();self.preview.color="Blue";self.preview.rebuild()
        colored=self.preview.render().tobytes();self.assertNotEqual(colored,before)
        self.preview.facing=-1;self.assertNotEqual(self.preview.render().tobytes(),colored)

    def test_particles_render_and_expire(self):
        self.hat.artwork.putpixel((24,32),(255,255,255,255));self.preview.rebuild()
        before=self.preview.render().tobytes();self.preview.quack();self.assertEqual(len(self.preview.particles),6)
        for _ in range(24):self.preview.advance(1/60)
        self.assertNotEqual(self.preview.render().tobytes(),before);self.assertEqual(len(self.preview.frames),1)
        for _ in range(180):self.preview.advance(1/60)
        self.assertEqual(len(self.preview.particles),0)

    def test_preset_overrides_count_and_none_emits_nothing(self):
        self.hat.artwork.putpixel((24,32),(255,255,255,255))
        self.hat.slots=[EMPTY]*self.hat.height;self.hat.slots[:2]=[(31,0,3,255),(34,120,0,255)]
        self.preview.rebuild();self.preview.quack();self.assertEqual(len(self.preview.particles),8)
        self.hat.slots[0]=(31,0,0,255);self.preview.set_hat(self.hat);self.preview.quack()
        self.assertEqual(len(self.preview.particles),0)

    def test_cape_taper_alpha_trail_and_foreground_render(self):
        before=self.preview.render().tobytes();self.hat.slots[20]=(11,0,0,255);self.preview.rebuild()
        self.assertNotEqual(self.preview.render().tobytes(),before)
        self.hat.slots[20:23]=[(16,0,0,255),(17,0,0,255),(15,0,0,255)];self.preview.rebuild()
        self.assertNotEqual(self.preview.render().tobytes(),before)
        self.hat.slots[20:23]=[(20,0,0,255),EMPTY,EMPTY];self.preview.rebuild();self.preview.running=True
        for _ in range(60):self.preview.advance(1/60)
        self.assertEqual(len(self.preview.trail),60);self.assertEqual(self.preview.render().size,(384,240))

    def test_fixed_step_independent_of_display_rate(self):
        other=Preview(self.hat,seed=2);self.preview.running=other.running=True
        for _ in range(60):self.preview.advance(1/60)
        for _ in range(30):other.advance(1/30)
        self.assertAlmostEqual(self.preview.time,other.time);self.assertAlmostEqual(self.preview.x,other.x)

    def test_rock_only_and_short_hats_do_not_emit(self):
        self.preview.quack()
        self.assertGreater(self.preview.quacking,0)
        self.assertEqual(self.preview.frames,[])
        self.assertEqual(self.preview.particles,[])
        self.preview.set_hat(Hat.from_image(self.hat.artwork.crop((0,0,64,32)),"master.png"))
        self.preview.quack()
        self.assertEqual(self.preview.particles,[])

    def test_particle_cells_order_transparency_and_preservation(self):
        colors=[(255,0,0,255),(255,0,255,255),(0,255,0,255),(0,0,255,255)]
        for xy,color in zip(((24,32),(36,32),(24,44),(36,44)),colors):
            self.hat.artwork.putpixel(xy,color)
        before=self.hat.png()
        self.preview.rebuild()
        self.assertEqual([f.size for f in self.preview.frames],[(12,12)]*3)
        self.assertEqual([f.getpixel((0,0)) for f in self.preview.frames],[colors[0],colors[2],colors[3]])
        self.assertEqual(self.hat.png(),before)

    def test_hat_offset_moves_backward_and_up_in_both_facings(self):
        from PIL import Image
        art=Image.new('RGBA',(32,32));art.putpixel((16,16),(17,231,42,255))
        hat=Hat.from_image(art,'marker.png');preview=Preview(hat)
        def marker():
            image=preview.render()
            return min((x,y) for y in range(image.height) for x in range(image.width)
                       if image.getpixel((x,y))==(17,231,42,255))
        for facing in (1,-1):
            preview.facing=facing;hat.slots[0]=(1,128,128,255);preview.rebuild()
            before=marker()
            hat.slots[0]=(1,132,131,255);preview.rebuild();after=marker()
            self.assertEqual((after[0]-before[0],after[1]-before[1]),(-8*facing,-6))

    def test_cape_offset_is_additive_and_sway_is_not_rotation(self):
        from PIL import Image
        def bounds():
            image=Image.new('RGBA',(384,240));self.preview.draw_cape(image)
            return image.getbbox()
        self.hat.slots=[EMPTY]*self.hat.height
        self.hat.slots[0]=(12,128,255,255);self.preview.rebuild()
        for facing in (1,-1):
            self.preview.facing=facing;self.hat.slots[1]=EMPTY;self.preview.rebuild()
            before=bounds()
            self.hat.slots[1]=(10,132,131,255);self.preview.rebuild();after=bounds()
            self.assertEqual(tuple(b-a for a,b in zip(before,after)),(8*facing,6,8*facing,6))
        self.hat.slots[0]=(12,255,255,255);self.preview.rebuild()
        self.assertGreater(bounds()[3]-bounds()[1],20)

    def test_single_particle_and_one_turn_rotation(self):
        import math
        from unittest.mock import patch
        from PIL import Image
        self.hat.artwork.putpixel((24,32),(255,255,255,255))
        self.hat.slots=[EMPTY]*self.hat.height
        self.hat.slots[:3]=[(34,1,0,255),(35,255,0,255),(41,0,255,255)]
        self.preview.rebuild();self.preview.quack()
        self.assertEqual(len(self.preview.particles),1)
        particle=self.preview.particles[0];particle.age=particle.life/2
        with patch.object(self.preview,'sprite') as draw:
            self.preview.draw_particles(Image.new('RGBA',(384,240)),False)
            self.assertAlmostEqual(draw.call_args.kwargs['rotation'],math.pi)

    def test_particle_scale_clamps_after_interpolation(self):
        from unittest.mock import patch
        from PIL import Image
        self.hat.artwork.putpixel((24,32),(255,255,255,255))
        self.hat.slots=[EMPTY]*self.hat.height
        self.hat.slots[:2]=[(34,1,0,255),(35,255,0,255)]
        self.preview.rebuild();self.preview.quack()
        particle=self.preview.particles[0]
        for endpoints,fraction,expected in [([0,2],0,0),([0,2],.25,.5),([0,2],.75,1),([1,2],.5,1)]:
            particle.values[40]=endpoints;particle.age=particle.life*fraction
            with patch.object(self.preview,'sprite') as draw:
                self.preview.draw_particles(Image.new('RGBA',(384,240)),False)
                if expected==0:draw.assert_not_called()
                else:self.assertAlmostEqual(draw.call_args.args[4],expected*self.preview.zoom)

    def test_default_cape_is_shorter_narrower_and_slants_back(self):
        from PIL import Image
        from unittest.mock import patch
        self.hat.slots=[EMPTY]*self.hat.height;self.preview.rebuild()
        for facing in (1,-1):
            self.preview.facing=facing
            with patch.object(self.preview,'sheet') as sheet:
                sheet.crop.return_value=Image.new('RGBA',(32,1),'red')
                canvas=Image.new('RGBA',(384,240))
                self.preview.draw_cape(canvas)
            bounds=canvas.getbbox()
            self.assertLessEqual(bounds[3]-bounds[1],24)
            self.assertLess(bounds[3],self.preview.floor)
            self.assertLessEqual(bounds[2]-bounds[0],30)
            top=[x for x in range(384) if canvas.getpixel((x,bounds[1]))[3]]
            bottom=[x for x in range(384) if canvas.getpixel((x,bounds[3]-1))[3]]
            self.assertLess((sum(bottom)/len(bottom)-sum(top)/len(top))*facing,0)
