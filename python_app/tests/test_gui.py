import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import ImageGrab
from duckmeta.app import App
from duckmeta.model import Hat


@unittest.skipUnless(os.environ.get("DISPLAY") or os.name=="nt", "GUI tests need a desktop display (Linux: xvfb-run)")
class GuiTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.errors=[]
        self.root.report_callback_exception=lambda *args:self.errors.append(args)
        self.app=App(self.root);self.root.update();self.app.engine.paused=True

    def tearDown(self):
        self.app.closed=True
        if self.app.timer:self.root.after_cancel(self.app.timer)
        self.root.destroy();self.assertEqual(self.errors,[])

    def test_slider_undo_redo_and_preview(self):
        before=self.app.engine.render().tobytes();self.app.slider_widgets[0].set(140);self.root.update()
        self.assertEqual(self.app.hat.slots[0][1],140);self.assertTrue(self.app.dirty)
        self.assertNotEqual(self.app.engine.render().tobytes(),before)
        self.app.undo();self.root.update();self.assertEqual(self.app.hat.slots[0][1],128)
        self.app.redo();self.root.update();self.assertEqual(self.app.hat.slots[0][1],140)

    def test_real_export_and_import_callbacks(self):
        with tempfile.TemporaryDirectory() as directory:
            filename=Path(directory)/"test-hat.png";self.app.change_channel(1,137)
            with patch("duckmeta.app.filedialog.asksaveasfilename",return_value=str(filename)):
                self.assertTrue(self.app.save_file())
            self.assertFalse(self.app.dirty);saved=Hat.read(filename)
            self.assertEqual(saved.slots[0][1],137);self.assertEqual(saved.artwork.tobytes(),self.app.hat.artwork.tobytes())
            with patch("duckmeta.app.filedialog.askopenfilename",return_value=str(filename)):self.app.open_file()
            self.assertEqual(self.app.hat.name,"test-hat.png");self.assertEqual(self.app.hat.slots[0][1],137)

    def test_add_move_remove_raw_and_invalid_input(self):
        self.assertTrue(self.app.add_effect(2));self.root.update();self.assertEqual(self.app.selected,1)
        self.app.move(1);self.root.update();self.assertEqual(self.app.hat.slots[2][0],2)
        self.app.remove();self.root.update();self.assertEqual(self.app.hat.slots[2],(0,0,0,0))
        self.app.undo();self.root.update();self.app.raw_vars[1].set("256")
        with patch("duckmeta.app.messagebox.showerror") as error:self.app.apply_raw();error.assert_called_once()
        self.assertEqual(self.app.hat.slots[2][1],0)
        self.app.raw_vars[1].set("200");self.app.apply_raw();self.root.update();self.assertEqual(self.app.hat.slots[2][1],200)

    def test_controls_dialogs_and_unsaved_cancel(self):
        self.app.motion(True);self.app.engine.paused=False;self.app.engine.advance(.1);self.assertGreater(self.app.engine.x,192)
        self.app.color.set("Pink");self.app.color_changed();self.assertEqual(self.app.engine.color,"Pink")
        self.app.engine.quack();self.assertGreater(len(self.app.engine.particles),0)
        self.app.pause();self.assertTrue(self.app.engine.paused)
        self.app.add_dialog();self.root.update()
        dialogs=[w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel)]
        self.assertEqual(len(dialogs),1);dialogs[0].destroy()
        self.app.help();self.root.update()
        for w in self.root.winfo_children():
            if isinstance(w,tk.Toplevel):w.destroy()
        self.app.change_channel(1,135)
        with patch("duckmeta.app.messagebox.askyesnocancel",return_value=None):self.assertFalse(self.app.confirm_replace())
        self.assertEqual(self.app.hat.slots[0][1],135)

    def test_window_and_screenshot(self):
        self.root.update();self.assertGreater(self.app.canvas.winfo_width(),400);self.assertGreater(self.app.canvas.winfo_height(),200)
        output=os.environ.get("DUCKMETA_SCREENSHOT")
        if output:
            self.root.after_cancel(self.app.timer);self.app.animate();self.root.update()
            x,y=self.root.winfo_rootx(),self.root.winfo_rooty()
            ImageGrab.grab(bbox=(x,y,x+self.root.winfo_width(),y+self.root.winfo_height()),xdisplay=os.environ.get("DISPLAY")).save(output)
