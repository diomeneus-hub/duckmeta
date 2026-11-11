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
        self.preferences=tempfile.TemporaryDirectory();self.addCleanup(self.preferences.cleanup)
        self.app=App(self.root,preferences_path=Path(self.preferences.name)/"settings.json");self.root.update();self.app.engine.paused=True

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
        self.app.engine.quack();self.assertGreater(self.app.engine.quacking,0)
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

    def test_export_defaults_to_detected_hats_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            hats=Path(directory)/"Documents/DuckGame/Custom/Hats"
            with patch("duckmeta.app.find_hats_directory",return_value=hats), patch("duckmeta.app.filedialog.asksaveasfilename",return_value="") as dialog:
                self.assertFalse(self.app.save_file())
                self.assertEqual(dialog.call_args.kwargs["initialdir"],str(hats))
                self.assertTrue(hats.is_dir())
            with patch("duckmeta.app.filedialog.askopenfilename",return_value="") as dialog:
                self.app.open_file()
                self.assertEqual(dialog.call_args.kwargs["initialdir"],str(hats))

    def test_file_menu_loads_lzx_hat_and_preserves_original(self):
        from xnb_fixtures import texture_payload, xnb
        labels=[self.app.file_menu.entrycget(i,'label') for i in range(self.app.file_menu.index('end')+1) if self.app.file_menu.type(i)=='command']
        self.assertIn('Load base hat...',labels)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'hat.xnb';data=xnb(texture_payload(),'lzx');path.write_bytes(data)
            with patch('duckmeta.app.filedialog.askopenfilename',return_value=str(path)):
                self.app.load_base_hat()
            self.assertEqual(self.app.hat.name,'hat.png');self.assertEqual(self.app.hat.width,32)
            self.assertEqual(path.read_bytes(),data)
            with patch('duckmeta.app.filedialog.asksaveasfilename',return_value=str(path)),patch('duckmeta.app.messagebox.showerror') as error:
                self.assertFalse(self.app.save_file());error.assert_called_once()
            self.assertEqual(path.read_bytes(),data)

    def test_bad_xnb_keeps_current_hat(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.xnb';path.write_bytes(b'not an xnb')
            before=self.app.hat.png()
            with patch('duckmeta.app.filedialog.askopenfilename',return_value=str(path)),patch('duckmeta.app.messagebox.showerror') as error:
                self.app.load_base_hat();error.assert_called_once()
            self.assertEqual(self.app.hat.png(),before)

    def test_loads_sprite_png_and_game_xnb_pair(self):
        from test_sprites import duck_grid
        from xnb_fixtures import texture_payload,xnb
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);image=duck_grid();path=folder/'reference.png';image.save(path)
            with patch('duckmeta.app.filedialog.askopenfilename',return_value=str(path)):
                self.app.load_duck_sheet()
            self.assertEqual(len(self.app.engine.sprites.normal),8)
            for name in ('duck.xnb','duckQuack.xnb'):
                (folder/name).write_bytes(xnb(texture_payload(image.width,image.height,pixels=image.tobytes()),'lz4'))
            self.app.content_directory=folder;self.app.auto_load_sprites()
            self.assertEqual(len(self.app.engine.sprites.quack),8)
            self.app.animation_settings();self.root.update()
            dialogs=[w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel)]
            self.assertEqual(len(dialogs),1);dialogs[0].destroy()

    def test_export_folder_override_survives_detection_and_restart(self):
        from duckmeta.settings import read_export_folder
        folder=Path(self.preferences.name)/"my hats";folder.mkdir()
        with patch("duckmeta.app.filedialog.askdirectory",return_value=str(folder)):
            self.app.choose_export_folder()
        self.assertEqual(read_export_folder(self.app.preferences_path),folder)
        with patch("duckmeta.app.find_hats_directory",return_value=Path("/wrong")), patch("duckmeta.app.filedialog.asksaveasfilename",return_value="") as dialog:
            self.app.save_file()
            self.assertEqual(dialog.call_args.kwargs["initialdir"],str(folder))

    def test_copy_sheet_preserves_original_pixels_and_optional_metadata(self):
        import io
        from PIL import Image
        self.assertTrue(self.app.sheet_label.bind('<Button-3>'))
        for include_metadata in (False,True):
            with patch('duckmeta.app.copy_png') as copy:
                self.app.copy_sheet(include_metadata)
                image=Image.open(io.BytesIO(copy.call_args.args[0]))
                expected=self.app.hat.image() if include_metadata else self.app.hat.artwork
                self.assertEqual(image.size,expected.size)
                self.assertEqual(image.tobytes(),expected.tobytes())
        with patch('duckmeta.app.copy_png',side_effect=RuntimeError('missing helper')),patch('duckmeta.app.messagebox.showerror') as error:
            self.app.copy_sheet();error.assert_called_once()

    def test_compact_modifier_controls_and_particle_count_range(self):
        self.assertIs(self.app.add_modifier_button.master,self.app.remove_modifier_button.master)
        self.app.add_effect(34);self.root.update()
        slider=self.app.slider_widgets[0]
        self.assertEqual(float(slider.cget('from')),0)
        self.assertEqual(float(slider.cget('to')),8)
        slider.set(1);self.root.update()
        self.assertEqual(self.app.hat.slots[self.app.selected][1],1)
        self.app.remove_modifier_button.invoke()
        self.assertEqual(self.app.hat.slots[self.app.selected],(0,0,0,0))

    def test_template_conflict_cancel_apply_undo_redo(self):
        before=list(self.app.hat.slots);art=self.app.hat.artwork.tobytes()
        pixels=[(1,140,130,255),(70,0,0,255)]
        with patch('duckmeta.app.messagebox.askyesno',return_value=False) as ask:
            self.assertFalse(self.app.apply_template('test',pixels));ask.assert_called_once()
        self.assertEqual(self.app.hat.slots,before);self.assertEqual(self.app.history.past,[])
        with patch('duckmeta.app.messagebox.askyesno',return_value=True):
            self.assertTrue(self.app.apply_template('test',pixels))
        after=list(self.app.hat.slots);self.assertNotEqual(before,after)
        self.assertEqual(self.app.hat.artwork.tobytes(),art)
        self.app.undo();self.assertEqual(self.app.hat.slots,before)
        self.app.redo();self.assertEqual(self.app.hat.slots,after)

    def test_template_dialog_save_selection_and_apply(self):
        from tkinter import ttk
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        self.app.save_template_dialog();self.root.update()
        dialog=next(w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel))
        widgets=list(descendants(dialog))
        entry=next(w for w in widgets if isinstance(w,ttk.Entry));entry.insert(0,'One modifier')
        checks=[w for w in widgets if isinstance(w,ttk.Checkbutton)]
        self.assertEqual(len(checks),sum(bool(p[3]) for p in self.app.hat.slots))
        for check in checks[1:]:check.invoke()
        next(w for w in widgets if isinstance(w,ttk.Button) and w.cget('text')=='Save template').invoke()
        entries,errors=self.app.templates.list();self.assertEqual(errors,[])
        entries=[entry for entry in entries if entry[0]=='One modifier']
        self.assertEqual(entries,[('One modifier',[self.app.hat.slots[0]])])
        self.app.hat.slots=[(0,0,0,0)]*self.app.hat.height;self.app.refresh()
        self.app.apply_template_dialog();self.root.update()
        dialog=next(w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel))
        box=next(w for w in descendants(dialog) if isinstance(w,tk.Listbox))
        index=next(i for i in range(box.size()) if box.get(i).startswith('One modifier'))
        box.selection_clear(0,'end');box.selection_set(index)
        with patch('duckmeta.app.messagebox.askyesno') as ask:
            next(w for w in descendants(dialog) if isinstance(w,ttk.Button) and w.cget('text')=='Apply').invoke()
            ask.assert_not_called()
        self.assertEqual(self.app.hat.slots[0],entries[0][1][0])

    def test_hold_quack_toggle_keyboard_and_focus(self):
        from types import SimpleNamespace
        engine=self.app.engine
        with patch.object(engine,'quack',wraps=engine.quack) as quack:
            self.app.hold_quack.set(True);self.app.update_quack_hold()
            self.assertTrue(engine.quack_held);quack.assert_called_once()
            self.app.release_controls();self.assertTrue(engine.quack_held)
            self.app.key_down(SimpleNamespace(keysym='q'))
            self.app.key_up(SimpleNamespace(keysym='q'))
            self.assertTrue(engine.quack_held);quack.assert_called_once()
            engine.paused=False
            for _ in range(120):engine.advance(1/60)
            self.assertGreater(engine.quacking,0);quack.assert_called_once()
            self.app.hold_quack.set(False);self.app.update_quack_hold()
            self.assertFalse(engine.quack_held);self.assertEqual(engine.quacking,0)
        self.app.key_down(SimpleNamespace(keysym='q'))
        self.app.hold_quack.set(True);self.app.update_quack_hold()
        self.app.hold_quack.set(False);self.app.update_quack_hold()
        self.assertTrue(engine.quack_held)
        self.app.key_up(SimpleNamespace(keysym='q'));self.assertFalse(engine.quack_held)
