"""Pixel workshop with layer editing and a side-by-side live duck."""
import colorsys
import io
import math
import os
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageDraw, ImageTk
from .artwork import Artwork, regions
from .model import Hat, History

NEAREST=Image.Resampling.NEAREST


class ArtEditor:
    def __init__(self,app):
        self.app=app
        if app.art_document is None:app.art_document=Artwork(app.hat.artwork)
        self.doc=app.art_document
        self.window=tk.Toplevel(app.root);self.window.title('Duckmeta — Pixel workshop');self.window.geometry('1250x760');self.window.minsize(950,600)
        self.window.transient(app.root);self.window.grab_set()
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.color=(255,255,255,255);self.tool=tk.StringVar(value='Pencil');self.zoom=tk.IntVar(value=6)
        self.guides=tk.BooleanVar(value=True);self.grid=tk.BooleanVar(value=True)
        self.last=None;self.stroke_started=False;self.timer=None;self.closed=False
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x')
        for tool in ('Pencil','Eraser','Fill','Eyedropper'):ttk.Radiobutton(bar,text=tool,value=tool,variable=self.tool).pack(side='left',padx=3)
        self.swatch=tk.Canvas(bar,width=34,height=28,highlightthickness=1,highlightbackground='#aaaaaa');self.swatch.pack(side='left',padx=8)
        self.swatch.bind('<Double-Button-1>',self.choose_color)
        ttk.Label(bar,text='Double-click color').pack(side='left')
        self.undo_button=ttk.Button(bar,text='Undo',command=self.undo);self.undo_button.pack(side='left',padx=5)
        self.redo_button=ttk.Button(bar,text='Redo',command=self.redo);self.redo_button.pack(side='left')
        ttk.Checkbutton(bar,text='Template guide',variable=self.guides,command=self.draw).pack(side='left',padx=8)
        ttk.Checkbutton(bar,text='Layout grid',variable=self.grid,command=self.draw).pack(side='left')
        combo=ttk.Combobox(bar,textvariable=self.zoom,values=(2,4,6,8,12,16),state='readonly',width=3);combo.pack(side='right');combo.bind('<<ComboboxSelected>>',lambda e:self.draw())
        ttk.Label(bar,text='Canvas zoom ').pack(side='right')
        files=ttk.Frame(self.window,padding=(8,0));files.pack(fill='x')
        for label,command in [('Open project',self.open_project),('Save project',self.save_project),('Export PNG',app.save_file)]:ttk.Button(files,text=label,command=command).pack(side='left',padx=3)
        ttk.Label(files,text='PNG flattens visible layers. Project preserves layers. Metadata is protected.').pack(side='left',padx=10)
        body=ttk.Frame(self.window,padding=8);body.pack(fill='both',expand=True)
        body.columnconfigure(1,weight=1);body.rowconfigure(0,weight=1)
        preview=ttk.Frame(body,width=290);preview.grid(row=0,column=0,sticky='nsew',padx=(0,8));preview.grid_propagate(False)
        ttk.Label(preview,text='LIVE DUCK').pack(anchor='w')
        self.preview=tk.Canvas(preview,width=280,height=250,bg='#111e23',highlightthickness=0);self.preview.pack(fill='both',expand=True)
        controls=ttk.Frame(preview);controls.pack(fill='x')
        for label,command in [('Quack',app.engine.quack),('Flip',app.flip),('Jump',app.engine.jump)]:ttk.Button(controls,text=label,command=command,width=6).pack(side='left')
        ttk.Checkbutton(preview,text='Hold quack',variable=app.hold_quack,command=app.update_quack_hold).pack(anchor='w')
        ttk.Checkbutton(preview,text='Auto quack',variable=app.auto,command=lambda:setattr(app.engine,'auto_quack',app.auto.get())).pack(anchor='w')
        center=ttk.Frame(body);center.grid(row=0,column=1,sticky='nsew');center.columnconfigure(0,weight=1);center.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(center,bg='#172322',highlightthickness=0,cursor='crosshair')
        self.canvas.grid(row=0,column=0,sticky='nsew')
        horizontal=ttk.Scrollbar(center,orient='horizontal',command=self.canvas.xview);horizontal.grid(row=1,column=0,sticky='ew')
        vertical=ttk.Scrollbar(center,orient='vertical',command=self.canvas.yview);vertical.grid(row=0,column=1,sticky='ns')
        self.canvas.configure(xscrollcommand=horizontal.set,yscrollcommand=vertical.set)
        self.canvas.bind('<Button-1>',self.press);self.canvas.bind('<B1-Motion>',self.drag);self.canvas.bind('<ButtonRelease-1>',self.release)
        side=ttk.Frame(body,width=180,padding=(8,0));side.grid(row=0,column=2,sticky='nsew')
        ttk.Label(side,text='LAYERS · top first').pack(anchor='w')
        self.layers=tk.Listbox(side,width=22,exportselection=False,bg='#182123',fg='#e5eae6',selectbackground='#425a36',highlightthickness=0);self.layers.pack(fill='both',expand=True);self.layers.bind('<<ListboxSelect>>',self.select_layer)
        for label,command in [('Add layer',lambda:self.layer_action(self.doc.add)),('Delete layer',lambda:self.layer_action(self.doc.remove)),('Move up',lambda:self.layer_action(lambda:self.doc.move(1))),('Move down',lambda:self.layer_action(lambda:self.doc.move(-1))),('Rename',self.rename),('Show / hide',self.toggle_visibility)]:ttk.Button(side,text=label,command=command).pack(fill='x',pady=2)
        ttk.Label(side,text='Layer opacity (0–255)').pack(anchor='w',pady=(8,0))
        self.opacity=tk.StringVar(value='255');ttk.Spinbox(side,from_=0,to=255,textvariable=self.opacity,width=6).pack(fill='x')
        ttk.Button(side,text='Apply opacity',command=self.set_opacity).pack(fill='x')
        self.status=tk.StringVar(value='Draw on the selected layer. Eyedropper samples visible artwork.')
        ttk.Label(self.window,textvariable=self.status,padding=8).pack(fill='x')
        self.window.bind('<Control-s>',lambda e:(self.save_project(),'break')[1]);self.window.bind('<Control-o>',lambda e:(self.open_project(),'break')[1])
        self.window.bind('<Control-z>',lambda e:(self.undo(),'break')[1]);self.window.bind('<Control-y>',lambda e:(self.redo(),'break')[1])
        self.refresh_layers();self.draw_swatch();self.draw();self.animate()

    def point(self,event):
        x=int(self.canvas.canvasx(event.x)//self.zoom.get());y=int(self.canvas.canvasy(event.y)//self.zoom.get())
        return (x,y) if 0<=x<self.doc.size[0] and 0<=y<self.doc.size[1] else None

    def press(self,event):
        self.last=None;self.stroke_started=False
        point=self.point(event)
        if point is None:return
        if self.tool.get()=='Eyedropper':
            self.color=self.doc.composite().getpixel(point);self.draw_swatch();return
        if not self.doc.layers[self.doc.active].visible:
            self.status.set('Show the selected layer before painting.');return
        self.doc.record();self.stroke_started=True;self.last=point
        if self.tool.get()=='Fill':self.doc.fill(point,self.color)
        else:self.doc.stroke(point,point,self.color,self.tool.get()=='Eraser')
        self.changed()

    def drag(self,event):
        point=self.point(event)
        if not self.stroke_started or self.tool.get() not in ('Pencil','Eraser'):return
        if point is None:self.last=None;return
        self.doc.stroke(self.last or point,point,self.color,self.tool.get()=='Eraser');self.last=point;self.changed()

    def release(self,event=None):self.last=None;self.stroke_started=False

    def changed(self):
        self.app.layer_project_dirty=True
        self.app.hat.artwork=self.doc.composite();self.app.engine.set_hat(self.app.hat)
        self.app.refresh(inspector=False);self.draw();self.refresh_layers()

    def undo(self):
        self.release()
        if self.doc.undo():self.changed()

    def redo(self):
        self.release()
        if self.doc.redo():self.changed()

    def layer_action(self,action):
        self.release()
        try:action()
        except ValueError as exc:messagebox.showerror('Layer',str(exc),parent=self.window);return
        self.changed()

    def refresh_layers(self):
        self.layers.delete(0,'end')
        for layer in reversed(self.doc.layers):self.layers.insert('end',f'{"●" if layer.visible else "○"} {layer.name}')
        self.layers.selection_set(len(self.doc.layers)-1-self.doc.active)
        self.opacity.set(str(self.doc.layers[self.doc.active].opacity))
        self.undo_button.configure(state='normal' if self.doc.past else 'disabled');self.redo_button.configure(state='normal' if self.doc.future else 'disabled')

    def select_layer(self,event=None):
        if self.layers.curselection():self.doc.active=len(self.doc.layers)-1-self.layers.curselection()[0];self.opacity.set(str(self.doc.layers[self.doc.active].opacity))

    def rename(self):
        value=simpledialog.askstring('Layer name','Name:',initialvalue=self.doc.layers[self.doc.active].name,parent=self.window)
        if value and value.strip():self.doc.record();self.doc.layers[self.doc.active].name=value.strip()[:100];self.changed()
        self.window.grab_set()

    def toggle_visibility(self):
        self.doc.record();layer=self.doc.layers[self.doc.active];layer.visible=not layer.visible;self.changed()

    def set_opacity(self):
        try:
            value=int(self.opacity.get())
            if not 0<=value<=255:raise ValueError()
        except ValueError:messagebox.showerror('Opacity','Enter a whole number from 0 to 255.',parent=self.window);return
        self.doc.record();self.doc.layers[self.doc.active].opacity=value;self.changed()

    def draw(self):
        width,height=self.doc.size;z=min(self.zoom.get(),max(1,4096//(max(width,height)+1)))
        if z!=self.zoom.get():self.zoom.set(z)
        base=Image.new('RGBA',(width+1,height));pixels=base.load()
        for y in range(height):
            for x in range(width+1):pixels[x,y]=(45,56,55,255) if (x//4+y//4)%2 else (29,39,38,255)
        if self.guides.get():
            guide=Image.new('RGBA',(width,height));pen=ImageDraw.Draw(guide)
            for name,x,y,r,b in regions(width,height):
                if name in ('Idle','Quack'):
                    frame,_=self.app.engine.sprites.frame('idle',0,name=='Quack','White',lambda image,color:image)
                    frame=frame.copy();frame.putalpha(frame.getchannel('A').point(lambda a:a//3));guide.alpha_composite(frame,(x,y))
                elif name=='Cape':pen.polygon([(x+12,y+4),(r-12,y+4),(r-3,b-3),(x+3,b-3)],fill=(120,190,150,55))
                else:pen.ellipse((x+2,y+2,r-3,b-3),outline=(150,200,170,100))
            base.alpha_composite(guide)
        base.alpha_composite(self.doc.composite())
        for y,pixel in enumerate(self.app.hat.slots):base.putpixel((width,y),pixel)
        self.photo=ImageTk.PhotoImage(base.resize(((width+1)*z,height*z),NEAREST),master=self.window)
        self.canvas.delete('all');self.canvas.create_image(0,0,image=self.photo,anchor='nw')
        if self.grid.get():
            for name,x,y,r,b in regions(width,height):
                self.canvas.create_rectangle(x*z,y*z,r*z,b*z,outline='#bde899',width=2)
                if z>=4:self.canvas.create_text(x*z+3,y*z+3,text=name,anchor='nw',fill='#bde899')
            self.canvas.create_rectangle(width*z,0,(width+1)*z,height*z,outline='#f5b860',width=2)
            for y in range(height):self.canvas.create_line(width*z,y*z,(width+1)*z,y*z,fill='#f5b860')
        self.canvas.configure(scrollregion=(0,0,(width+1)*z,height*z))

    def draw_swatch(self):
        r,g,b,a=self.color
        self.swatch.delete('all')
        for y in range(0,28,7):
            for x in range(0,35,7):
                bg=90 if (x//7+y//7)%2 else 170
                rgb=tuple(round(v*a/255+bg*(1-a/255)) for v in (r,g,b))
                self.swatch.create_rectangle(x,y,x+7,y+7,fill='#%02x%02x%02x'%rgb,outline='')
        self.status.set(f'Color #{r:02X}{g:02X}{b:02X} · alpha {a}/255')

    def choose_color(self,event=None):
        dialog=tk.Toplevel(self.window);dialog.title('Color — hue, saturation, brightness');dialog.transient(self.window);dialog.grab_set()
        h,s,v=colorsys.rgb_to_hsv(*(x/255 for x in self.color[:3]));choice=[h,s]
        wheel=tk.Canvas(dialog,width=200,height=200,highlightthickness=0);wheel.pack(padx=12,pady=12)
        image=Image.new('RGB',(200,200),'#182123')
        for y in range(200):
            for x in range(200):
                dx,dy=x-100,y-100;radius=math.hypot(dx,dy)/96
                if radius<=1:image.putpixel((x,y),tuple(round(c*255) for c in colorsys.hsv_to_rgb((math.atan2(dy,dx)/math.tau)%1,radius,1)))
        photo=ImageTk.PhotoImage(image,master=dialog);wheel.create_image(0,0,image=photo,anchor='nw');dialog.photo=photo
        value=tk.DoubleVar(value=v);alpha=tk.IntVar(value=self.color[3]);swatch=tk.Label(dialog,width=25,height=2);swatch.pack()
        def update(*args):
            rgb=tuple(round(c*255) for c in colorsys.hsv_to_rgb(*choice,value.get()))
            swatch.configure(bg='#%02x%02x%02x'%rgb,text='#%02X%02X%02X'%rgb)
            wheel.delete('selection');angle=choice[0]*math.tau;radius=choice[1]*96;x=100+math.cos(angle)*radius;y=100+math.sin(angle)*radius
            wheel.create_oval(x-4,y-4,x+4,y+4,outline='black',width=2,tags='selection')
        def pick(event):
            dx,dy=event.x-100,event.y-100;choice[:]=[(math.atan2(dy,dx)/math.tau)%1,min(1,math.hypot(dx,dy)/96)];update()
        wheel.bind('<Button-1>',pick);wheel.bind('<B1-Motion>',pick)
        ttk.Label(dialog,text='Brightness / value').pack();ttk.Scale(dialog,from_=0,to=1,variable=value,command=update).pack(fill='x',padx=12)
        ttk.Label(dialog,text='Alpha / opacity').pack();ttk.Scale(dialog,from_=0,to=255,variable=alpha).pack(fill='x',padx=12)
        def close():dialog.destroy();self.window.grab_set()
        def accept():
            self.color=(*[round(c*255) for c in colorsys.hsv_to_rgb(*choice,value.get())],round(alpha.get()));self.draw_swatch();close()
        ttk.Button(dialog,text='Use color',command=accept).pack(fill='x',padx=12,pady=6)
        ttk.Button(dialog,text='Cancel',command=close).pack(fill='x',padx=12,pady=6);dialog.protocol('WM_DELETE_WINDOW',close);update()

    def save_project(self):
        filename=filedialog.asksaveasfilename(parent=self.window,title='Save layered project',defaultextension='.duckmeta',filetypes=[('Duckmeta project','*.duckmeta')])
        if not filename:return False
        if Path(filename).suffix.lower()!='.duckmeta':
            messagebox.showerror('Save project','Use a .duckmeta filename. Use Export PNG for a game hat.',parent=self.window);return False
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=Path(filename).parent,delete=False) as stream:
                temporary=Path(stream.name);stream.write(self.doc.project(self.app.hat.slots))
            os.replace(temporary,filename)
        except Exception as exc:
            messagebox.showerror('Could not save project',str(exc),parent=self.window);return False
        finally:
            if temporary:temporary.unlink(missing_ok=True)
        self.app.layer_project_dirty=False;self.app.saved_slots=list(self.app.hat.slots);self.app.saved_artwork=self.app.hat.artwork.tobytes();self.app.refresh(inspector=False)
        self.status.set(f'Saved layered project: {filename}');return True

    def open_project(self):
        if (self.app.dirty or self.app.layer_project_dirty) and not messagebox.askyesno('Replace current work?','Open another project and discard unsaved changes?',parent=self.window):return
        filename=filedialog.askopenfilename(parent=self.window,title='Open layered project',filetypes=[('Duckmeta project','*.duckmeta')])
        if not filename:return
        try:
            path=Path(filename)
            if path.stat().st_size>64*1024*1024:raise ValueError('Project exceeds 64 MB.')
            doc,slots=Artwork.load(path.read_bytes())
        except Exception as exc:messagebox.showerror('Could not open project',str(exc),parent=self.window);return
        self.doc=doc;self.app.art_document=doc;self.app.hat=Hat(path.stem+'.png',doc.composite(),slots,True);self.app.history=History();self.app.selected=0
        self.app.engine.set_hat(self.app.hat);self.app.saved_slots=list(slots);self.app.saved_artwork=self.app.hat.artwork.tobytes();self.app.layer_project_dirty=False
        self.app.refresh();self.refresh_layers();self.draw()

    def animate(self):
        if self.closed:return
        image=self.app.engine.render()
        left=max(0,min(image.width-128,round(self.app.engine.x)-64));top=max(0,min(image.height-160,round(self.app.engine.y)-120))
        image=image.crop((left,top,left+128,top+160))
        w=max(1,self.preview.winfo_width());h=max(1,self.preview.winfo_height());scale=min(w/image.width,h/image.height)
        self.preview_photo=ImageTk.PhotoImage(image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),NEAREST),master=self.window)
        self.preview.delete('all');self.preview.create_image(w//2,h//2,image=self.preview_photo)
        self.timer=self.window.after(50,self.animate)

    def close(self):
        self.release()
        if self.app.layer_project_dirty:
            answer=messagebox.askyesnocancel('Save layered project?','Save a project to keep your editable layers? No keeps them in this session; PNG exports are flattened.',parent=self.window)
            if answer is None:return
            if answer and not self.save_project():return
        self.closed=True
        if self.timer:self.window.after_cancel(self.timer)
        self.window.destroy();self.app.art_editor=None
