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
        before=self.preview.render().tobytes();self.preview.quack();self.assertEqual(len(self.preview.particles),6)
        for _ in range(24):self.preview.advance(1/60)
        self.assertNotEqual(self.preview.render().tobytes(),before);self.assertEqual(len(self.preview.frames),1)
        for _ in range(180):self.preview.advance(1/60)
        self.assertEqual(len(self.preview.particles),0)

    def test_preset_overrides_count_and_none_emits_nothing(self):
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
