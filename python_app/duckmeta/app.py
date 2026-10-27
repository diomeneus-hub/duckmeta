"""Native Tkinter UI. No embedded web browser or local web server."""
from __future__ import annotations

import os
import tempfile
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from PIL import Image, ImageDraw, ImageTk

from .model import ASSETS, BY_ID, EFFECTS, EMPTY, Hat, History, decode_value
from .preview import COLORS, NEAREST, Preview

BG, PANEL, TEXT, MUTED, ACCENT = "#101719", "#182123", "#e5eae6", "#96a89c", "#bde899"


class App:
    def __init__(self, root, hat=None):
        self.root = root
        root.title("Duckmeta — Hat workshop")
        root.geometry("1280x860");root.minsize(1080,700)
        root.configure(bg=BG)
        self.hat = hat or Hat.example()
        self.engine = Preview(self.hat)
        self.history = History()
        self.saved_slots = list(self.hat.slots)
        self.selected = next((i for i,p in enumerate(self.hat.slots) if p[3]),0)
        self.building = False
        self.drag_snapshot = None
        self.closed = False
        self.last_frame = time.monotonic()
        self.timer = None
        self.slider_widgets = []
        self._theme()
        self._build()
        self.refresh()
        self.status.set(f"{self.hat.name} loaded. Open a PNG or start editing. All files stay on this computer.")
        root.protocol("WM_DELETE_WINDOW", self.close)
        for sequence, command in [("<Control-o>",self.open_file),("<Control-s>",self.save_file),
                                  ("<Control-z>",self.undo),("<Control-y>",self.redo)]:
            root.bind(sequence,lambda event,fn=command: (fn(),"break")[1])
        self.animate()

    @property
    def dirty(self):
        return self.hat.slots != self.saved_slots

    def _theme(self):
        self.font = tkfont.nametofont("TkDefaultFont").actual("family")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".",background=PANEL,foreground=TEXT,font=(self.font,10),bordercolor="#35443c")
        style.configure("TFrame",background=PANEL)
        style.configure("TLabel",background=PANEL,foreground=TEXT)
        style.configure("Muted.TLabel",foreground=MUTED,font=(self.font,9))
        style.configure("Title.TLabel",font=(self.font,20,"bold"),foreground=ACCENT)
        style.configure("TButton",padding=(10,7),background="#28362e",foreground=TEXT)
        style.map("TButton",background=[("active","#41543a")])
        style.configure("Accent.TButton",background=ACCENT,foreground="#25321f")
        style.map("Accent.TButton",background=[("active","#d0f5b3")])
        style.configure("Treeview",background=PANEL,fieldbackground=PANEL,foreground=TEXT,rowheight=32)
        style.map("Treeview",background=[("selected","#3b5133")],foreground=[("selected",TEXT)])
        style.configure("TEntry",fieldbackground="#101c19",foreground=TEXT,insertcolor=TEXT)
        style.configure("TSpinbox",fieldbackground="#101c19",foreground=TEXT,insertcolor=TEXT)
        style.configure("TCombobox",fieldbackground="#22352b",foreground=TEXT,arrowcolor=ACCENT)
        style.map("TCombobox",fieldbackground=[("readonly","#22352b")],foreground=[("readonly",TEXT)])
        style.configure("TCheckbutton",background=PANEL,foreground=TEXT)
        style.configure("Horizontal.TScale",background=ACCENT,troughcolor="#27372c",bordercolor="#4a5c41")
        self.root.option_add("*TCombobox*Listbox.background",PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground",TEXT)

    def _build(self):
        header=ttk.Frame(self.root,padding=18);header.pack(fill="x")
        ttk.Label(header,text="DUCKMETA",style="Title.TLabel").pack(side="left")
        ttk.Label(header,text="  PYTHON HAT WORKSHOP",style="Muted.TLabel").pack(side="left",padx=12)
        for label,command in [("Export PNG",self.save_file),("Open PNG",self.open_file),("Help",self.help)]:
            ttk.Button(header,text=label,command=command,style="Accent.TButton" if label=="Export PNG" else "TButton").pack(side="right",padx=5)
        self.status=tk.StringVar()
        ttk.Label(self.root,textvariable=self.status,padding=(18,10),style="Muted.TLabel",wraplength=1200).pack(side="bottom",fill="x")
        content=ttk.Frame(self.root,padding=(14,10));content.pack(fill="both",expand=True)
        content.columnconfigure(1,weight=1);content.rowconfigure(0,weight=1)
        left=ttk.Frame(content,width=225,padding=12);left.grid(row=0,column=0,sticky="nsew",padx=(0,12));left.grid_propagate(False)
        left.columnconfigure(0,weight=1);left.rowconfigure(3,weight=1)
        self.file_label=ttk.Label(left,text="",wraplength=195,font=(self.font,11,"bold"));self.file_label.grid(sticky="w",pady=8)
        ttk.Button(left,text="Load wizard example",command=self.example).grid(sticky="ew",pady=(4,18))
        self.stack_heading=ttk.Label(left,text="METAPIXEL STACK",style="Muted.TLabel");self.stack_heading.grid(sticky="w",pady=(0,8))
        tree_frame=ttk.Frame(left);tree_frame.grid(sticky="nsew")
        self.stack=ttk.Treeview(tree_frame,columns=("id","effect"),show="headings",selectmode="browse",height=12)
        self.stack.heading("id",text="ID");self.stack.heading("effect",text="Modifier")
        self.stack.column("id",width=35,stretch=False);self.stack.column("effect",width=144,stretch=True)
        scroll=ttk.Scrollbar(tree_frame,orient="vertical",command=self.stack.yview);self.stack.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right",fill="y");self.stack.pack(fill="both",expand=True)
        self.stack.bind("<<TreeviewSelect>>",self.select)
        ttk.Button(left,text="+ Add modifier",command=self.add_dialog).grid(sticky="ew",pady=(14,8))
        ttk.Label(left,text="Order matters. Randomizers affect\nthe preceding non-randomizer.",style="Muted.TLabel",wraplength=195).grid(sticky="w",pady=6)
        middle=ttk.Frame(content,padding=10);middle.grid(row=0,column=1,sticky="nsew")
        middle.columnconfigure(0,weight=1);middle.rowconfigure(1,weight=1)
        ttk.Label(middle,text="LIVE DUCK PREVIEW",style="Muted.TLabel").grid(row=0,column=0,sticky="w",pady=(0,12))
        self.canvas=tk.Canvas(middle,bg="#111e23",width=600,height=375,highlightthickness=1,highlightbackground="#35443c",takefocus=True)
        self.canvas.grid(row=1,column=0,sticky="nsew")
        self.canvas.bind("<Button-1>",lambda event:self.canvas.focus_set())
        self.canvas.bind("<KeyPress>",self.key_down);self.canvas.bind("<KeyRelease>",self.key_up)
        self.canvas.bind("<FocusOut>",lambda event:setattr(self.engine,"direction",0))
        transport=ttk.Frame(middle);transport.grid(row=2,column=0,sticky="ew",pady=10)
        for label,command in [("Idle",lambda:self.motion(False)),("Run",lambda:self.motion(True)),("Jump",self.engine.jump),("Quack!",self.engine.quack)]:
            ttk.Button(transport,text=label,command=command,width=7).pack(side="left",padx=(0,5))
        self.pause_button=ttk.Button(transport,text="Pause",command=self.pause,width=7);self.pause_button.pack(side="right")
        ttk.Button(transport,text="Flip",command=self.flip,width=5).pack(side="right",padx=5)
        settings=ttk.Frame(middle);settings.grid(row=3,column=0,sticky="ew",pady=(0,10))
        ttk.Label(settings,text="Duck").pack(side="left",padx=(0,6))
        self.color=tk.StringVar(value="White")
        combo=ttk.Combobox(settings,values=list(COLORS),textvariable=self.color,state="readonly",width=8)
        combo.pack(side="left");combo.bind("<<ComboboxSelected>>",self.color_changed)
        self.auto=tk.BooleanVar();ttk.Checkbutton(settings,text="Auto quack",variable=self.auto,command=lambda:setattr(self.engine,"auto_quack",self.auto.get())).pack(side="left",padx=9)
        self.grid=tk.BooleanVar();ttk.Checkbutton(settings,text="Grid",variable=self.grid,command=lambda:setattr(self.engine,"grid",self.grid.get())).pack(side="left")
        self.zoom=tk.StringVar(value="2")
        combo=ttk.Combobox(settings,values=["1","2","3"],textvariable=self.zoom,width=2,state="readonly");combo.pack(side="right")
        combo.bind("<<ComboboxSelected>>",self.zoom_changed);ttk.Label(settings,text="Zoom ").pack(side="right")
        ttk.Label(middle,text="SPRITE SHEET  ·  IDLE / QUACK / CAPE / PARTICLES / METADATA",style="Muted.TLabel").grid(row=4,column=0,sticky="w",pady=8)
        self.sheet_label=ttk.Label(middle,anchor="center");self.sheet_label.grid(row=5,column=0,sticky="ew")
        ttk.Label(middle,text="Click preview: arrows move · Space jumps · Q quacks\nApproximate game physics. Check final behavior in Duck Game.",style="Muted.TLabel",justify="left").grid(row=6,column=0,sticky="w",pady=10)
        right=ttk.Frame(content,width=280,padding=12);right.grid(row=0,column=2,sticky="nsew",padx=(12,0));right.pack_propagate(False)
        bar=ttk.Frame(right);bar.pack(fill="x")
        ttk.Label(bar,text="INSPECTOR",style="Muted.TLabel").pack(side="left")
        self.redo_button=ttk.Button(bar,text="Redo",command=self.redo,width=5);self.redo_button.pack(side="right")
        self.undo_button=ttk.Button(bar,text="Undo",command=self.undo,width=5);self.undo_button.pack(side="right",padx=4)
        scroller=tk.Canvas(right,bg=PANEL,highlightthickness=0,width=250);scroller.pack(side="left",fill="both",expand=True,pady=(15,0))
        scrollbar=ttk.Scrollbar(right,orient="vertical",command=scroller.yview);scrollbar.pack(side="right",fill="y",pady=(15,0));scroller.configure(yscrollcommand=scrollbar.set)
        self.inspector=ttk.Frame(scroller)
        window=scroller.create_window((0,0),window=self.inspector,anchor="nw")
        self.inspector.bind("<Configure>",lambda event:scroller.configure(scrollregion=scroller.bbox("all")))
        scroller.bind("<Configure>",lambda event:scroller.itemconfigure(window,width=event.width))

    def refresh(self, inspector=True):
        self.engine.rebuild()
        self.file_label.configure(text=f"{self.hat.name}\n{self.hat.width} × {self.hat.height} artwork")
        self.stack.delete(*self.stack.get_children())
        count=0
        for index,p in enumerate(self.hat.slots):
            if p[3]:
                count+=1
                self.stack.insert("","end",iid=str(index),values=(p[0],BY_ID.get(p[0],{}).get("name",f"Unknown {p[0]}")))
        self.stack_heading.configure(text=f"METAPIXEL STACK   {count}/{self.hat.height}")
        if self.stack.exists(str(self.selected)):
            self.stack.selection_set(str(self.selected));self.stack.see(str(self.selected))
        if inspector:self.inspect()
        self.draw_sheet()
        self.undo_button.configure(state="normal" if self.history.past else "disabled")
        self.redo_button.configure(state="normal" if self.history.future else "disabled")
        self.root.title(f"Duckmeta — {self.hat.name}{' *' if self.dirty else ''}")

    def select(self,event=None):
        selection=self.stack.selection()
        if selection and self.selected!=int(selection[0]):
            self.selected=int(selection[0]);self.inspect()

    def inspect(self):
        self.building=True;self.slider_widgets=[]
        for child in self.inspector.winfo_children():child.destroy()
        p=self.hat.slots[self.selected]
        if not p[3]:
            ttk.Label(self.inspector,text="Select a modifier or add one\nto begin editing.",wraplength=235).pack(anchor="w",pady=20)
            self.building=False;return
        definition=BY_ID.get(p[0]);name=definition["name"] if definition else f"Unknown ID {p[0]}"
        ttk.Label(self.inspector,text=name,font=(self.font,16,"bold"),wraplength=230).pack(anchor="w",pady=(0,12))
        desc=definition["description"] if definition else "Not in the supplied reference. Bytes are preserved; no preview behavior is assumed."
        ttk.Label(self.inspector,text=desc,wraplength=230,style="Muted.TLabel").pack(anchor="w",pady=(0,15))
        ttk.Label(self.inspector,text=f"ID {p[0]}  ·  ROW {self.selected}  ·  {definition['kind'] if definition else 'RAW'}",foreground=ACCENT).pack(anchor="w",pady=8)
        if definition and definition["kind"]=="BOOL":
            ttk.Label(self.inspector,text="Enabled by this pixel’s presence.\nRemove the modifier to disable it.",wraplength=230,style="Muted.TLabel").pack(anchor="w",pady=12)
        elif definition:
            for channel,label in enumerate(definition["labels"],1):
                ttk.Label(self.inspector,text=label,wraplength=230).pack(anchor="w",pady=(14,3))
                choices=definition.get("choices",{}).get(str(channel-1))
                if choices:
                    options=[f"{i}: {v}" for i,v in enumerate(choices)]
                    if p[channel]>=len(options):options.append(f"{p[channel]}: Unknown")
                    combo=ttk.Combobox(self.inspector,values=options,state="readonly",width=23)
                    combo.set(next(s for s in options if s.startswith(f"{p[channel]}:")));combo.pack(fill="x",padx=(0,5))
                    combo.bind("<<ComboboxSelected>>",lambda event,c=channel,w=combo:self.change_channel(c,int(w.get().split(":")[0])))
                else:
                    value_label=ttk.Label(self.inspector,text=self.value_text(definition,p[channel]),foreground=ACCENT);value_label.pack(anchor="e")
                    low,high=(128-definition["max"],128+definition["max"]) if definition["kind"] in ("VEC","INT") else (0,255)
                    scale=ttk.Scale(self.inspector,from_=low,to=high,orient="horizontal")
                    scale.set(p[channel]);scale.configure(command=lambda v,c=channel,l=value_label,d=definition:self.slide(c,v,l,d))
                    scale.pack(fill="x",padx=(0,8));self.slider_widgets.append(scale)
                    scale.bind("<ButtonPress-1>",lambda event:setattr(self,"drag_snapshot",list(self.hat.slots)))
                    scale.bind("<ButtonRelease-1>",self.finish_slide)
        ttk.Separator(self.inspector).pack(fill="x",pady=20)
        ttk.Label(self.inspector,text="RAW RGB + ALPHA",style="Muted.TLabel").pack(anchor="w")
        raw=ttk.Frame(self.inspector);raw.pack(fill="x",pady=10);self.raw_vars=[]
        for i,label in enumerate(["R · ID","G","B","A"]):
            group=ttk.Frame(raw);group.pack(side="left",fill="x",expand=True,padx=(0,3))
            ttk.Label(group,text=label,style="Muted.TLabel").pack(anchor="w")
            var=tk.StringVar(value=str(p[i]));self.raw_vars.append(var)
            entry=ttk.Spinbox(group,from_=0,to=255,textvariable=var,width=4,state="readonly" if i==0 else "normal")
            entry.pack(fill="x");entry.bind("<Return>",lambda event:self.apply_raw())
        ttk.Button(self.inspector,text="Apply raw values",command=self.apply_raw).pack(fill="x",padx=(0,5))
        order=ttk.Frame(self.inspector);order.pack(fill="x",pady=18)
        ttk.Button(order,text="Move up",command=lambda:self.move(-1),state="normal" if self.selected else "disabled").pack(side="left")
        ttk.Button(order,text="Move down",command=lambda:self.move(1),state="normal" if self.selected<self.hat.height-1 else "disabled").pack(side="right",padx=(0,5))
        ttk.Button(self.inspector,text="Remove modifier",command=self.remove).pack(fill="x",padx=(0,5),pady=(0,12))
        if p[0] in (70,71):
            ttk.Label(self.inspector,text="Audio flags export normally. Original Duck Game sounds are not included.",wraplength=230,style="Muted.TLabel").pack(anchor="w",pady=8)
        if p[0] in (100,101,102):
            ttk.Label(self.inspector,text="Targets the preceding non-randomizer. Non-particle values use the range midpoint in this preview.",wraplength=230,style="Muted.TLabel").pack(anchor="w",pady=8)
        self.building=False

    @staticmethod
    def value_text(definition,raw):
        value=decode_value(definition,raw)
        return f"{value*24:.1f} fps  ·  byte {raw}" if definition["id"]==48 else f"{value:.2f}  ·  byte {raw}"

    def slide(self,channel,value,label,definition):
        if self.building:return
        raw=max(0,min(255,round(float(value))))
        p=list(self.hat.slots[self.selected])
        if p[channel]==raw:return
        if self.drag_snapshot is None:self.history.record(self.hat.slots)
        p[channel]=raw;self.hat.slots[self.selected]=tuple(p)
        self.engine.rebuild();label.configure(text=self.value_text(definition,raw))
        self.raw_vars[channel].set(str(raw));self.draw_sheet()
        self.undo_button.configure(state="normal");self.redo_button.configure(state="disabled")
        self.root.title(f"Duckmeta — {self.hat.name}{' *' if self.dirty else ''}")
        self.status.set("Preview updated. Export PNG to save your edits.")

    def finish_slide(self,event=None):
        if self.drag_snapshot is not None and self.hat.slots!=self.drag_snapshot:
            self.history.record(self.drag_snapshot)
        self.drag_snapshot=None
        self.undo_button.configure(state="normal" if self.history.past else "disabled")

    def change_channel(self,channel,value):
        self.history.record(self.hat.slots)
        p=list(self.hat.slots[self.selected]);p[channel]=value;self.hat.slots[self.selected]=tuple(p)
        self.refresh();self.status.set("Modifier updated. Export PNG to save.")

    def apply_raw(self):
        try:
            values=tuple(int(var.get()) for var in self.raw_vars)
            if len(values)!=4 or any(not 0<=v<=255 for v in values):raise ValueError
        except ValueError:
            messagebox.showerror("Invalid channel","Enter whole numbers from 0 to 255.",parent=self.root);return
        if values!=self.hat.slots[self.selected]:
            self.history.record(self.hat.slots);self.hat.slots[self.selected]=values;self.refresh()
            self.status.set("Raw bytes applied. Unknown and untouched pixels are preserved.")

    def add_effect(self,ident):
        before=list(self.hat.slots)
        try:self.selected=self.hat.add(ident,self.selected if self.hat.slots[self.selected][3] else -1)
        except ValueError as exc:
            messagebox.showerror("Cannot add modifier",str(exc),parent=self.root);return False
        self.history.record(before);self.refresh();return True

    def add_dialog(self):
        dialog=tk.Toplevel(self.root);dialog.title("Add a modifier");dialog.geometry("470x540");dialog.configure(bg=PANEL)
        dialog.transient(self.root);dialog.grab_set()
        frame=ttk.Frame(dialog,padding=16);frame.pack(fill="both",expand=True)
        ttk.Label(frame,text="Find an effect",font=(self.font,16,"bold")).pack(anchor="w",pady=(0,12))
        search=tk.StringVar();entry=ttk.Entry(frame,textvariable=search);entry.pack(fill="x");entry.focus_set()
        box=tk.Listbox(frame,bg=PANEL,fg=TEXT,selectbackground="#425a36",highlightthickness=0,activestyle="none",font=(self.font,11))
        box.pack(fill="both",expand=True,pady=12)
        shown=[]
        def populate(*args):
            shown.clear();box.delete(0,"end")
            for d in EFFECTS:
                if search.get().lower() in f"{d['id']} {d['group']} {d['name']}".lower():
                    shown.append(d["id"]);box.insert("end",f"{d['id']:3}   {d['group']} · {d['name']}")
            if shown:box.selection_set(0)
        def add(event=None):
            if box.curselection() and self.add_effect(shown[box.curselection()[0]]):dialog.destroy()
        search.trace_add("write",populate);populate();box.bind("<Double-Button-1>",add);dialog.bind("<Return>",add)
        ttk.Button(frame,text="Add modifier",command=add,style="Accent.TButton").pack(fill="x")

    def move(self,offset):
        target=self.selected+offset
        if 0<=target<self.hat.height:
            self.history.record(self.hat.slots)
            self.hat.slots[target],self.hat.slots[self.selected]=self.hat.slots[self.selected],self.hat.slots[target]
            self.selected=target;self.refresh()

    def remove(self):
        self.history.record(self.hat.slots);self.hat.slots[self.selected]=EMPTY;self.refresh()

    def undo(self):
        if self.history.undo(self.hat):self.refresh();self.status.set("Undid last metadata edit.")

    def redo(self):
        if self.history.redo(self.hat):self.refresh();self.status.set("Redid last metadata edit.")

    def confirm_replace(self):
        if not self.dirty:return True
        choice=messagebox.askyesnocancel("Unsaved edits","Export your current hat before continuing?",parent=self.root)
        if choice is None:return False
        return self.save_file() if choice else True

    def install_hat(self,hat):
        self.hat=hat;self.engine.set_hat(hat);self.history=History();self.saved_slots=list(hat.slots)
        self.selected=next((i for i,p in enumerate(hat.slots) if p[3]),0);self.refresh()

    def open_file(self):
        filename=filedialog.askopenfilename(parent=self.root,title="Open a Duck Game hat",filetypes=[("PNG hats","*.png")])
        if not filename:return
        try:hat=Hat.read(filename)
        except Exception as exc:
            messagebox.showerror("Could not open PNG",str(exc),parent=self.root);return
        if self.confirm_replace():
            self.install_hat(hat);self.status.set(f"Loaded {filename}. {'Existing metadata preserved.' if hat.had_meta else 'One metadata column will be added on export.'}")

    def save_file(self):
        filename=filedialog.asksaveasfilename(parent=self.root,title="Export hat PNG",initialfile=Path(self.hat.name).stem+"-meta.png",defaultextension=".png",filetypes=[("PNG hats","*.png")])
        if not filename:return False
        temp=None
        try:
            # Atomic replacement avoids truncating an existing hat on a write failure.
            with tempfile.NamedTemporaryFile(dir=Path(filename).parent,suffix=".tmp",delete=False) as stream:
                temp=Path(stream.name);stream.write(self.hat.png())
            os.replace(temp,filename)
        except Exception as exc:
            if temp:temp.unlink(missing_ok=True)
            messagebox.showerror("Could not export",str(exc),parent=self.root);return False
        self.saved_slots=list(self.hat.slots);self.refresh()
        self.status.set(f"Saved {filename} · {self.hat.width+1} × {self.hat.height} · artwork preserved.")
        return True

    def example(self):
        if self.confirm_replace():self.install_hat(Hat.example());self.status.set("Wizard example loaded.")

    def draw_sheet(self):
        raw=self.hat.image()
        factor=min(3,430/raw.width,180/raw.height)
        size=(max(1,round(raw.width*factor)),max(1,round(raw.height*factor)))
        checker=Image.new("RGBA",size,"#1c2828");draw=ImageDraw.Draw(checker)
        for y in range(0,size[1],8):
            for x in range(0,size[0],8):
                if (x//8+y//8)%2:draw.rectangle((x,y,x+7,y+7),fill="#2b3734")
        checker.alpha_composite(raw.resize(size,NEAREST))
        self.sheet_photo=ImageTk.PhotoImage(checker,master=self.root);self.sheet_label.configure(image=self.sheet_photo)

    def color_changed(self,event=None):
        self.engine.color=self.color.get();self.engine.rebuild()

    def zoom_changed(self,event=None):
        self.engine.zoom=int(self.zoom.get());self.engine.particles=[];self.engine.trail=[]

    def motion(self,running):
        self.engine.running=running;self.status.set("Running preview." if running else "Idle preview.")

    def flip(self):self.engine.facing*=-1

    def pause(self):
        self.engine.paused=not self.engine.paused;self.pause_button.configure(text="Resume" if self.engine.paused else "Pause")

    def key_down(self,event):
        if event.keysym in ("Left","Right"):self.engine.direction=-1 if event.keysym=="Left" else 1
        elif event.keysym=="space":self.engine.jump()
        elif event.keysym.lower()=="q":self.engine.quack()
        return "break"

    def key_up(self,event):
        if event.keysym in ("Left","Right"):self.engine.direction=0
        return "break"

    def animate(self):
        if self.closed:return
        now=time.monotonic();self.engine.advance(now-self.last_frame);self.last_frame=now
        image=self.engine.render()
        w,h=max(1,self.canvas.winfo_width()),max(1,self.canvas.winfo_height())
        factor=min(w/image.width,h/image.height)
        image=image.resize((max(1,round(image.width*factor)),max(1,round(image.height*factor))),NEAREST)
        self.frame_photo=ImageTk.PhotoImage(image,master=self.root)
        self.canvas.delete("frame");self.canvas.create_image(w//2,h//2,image=self.frame_photo,tags="frame")
        self.timer=self.root.after(33,self.animate)

    def help(self):
        dialog=tk.Toplevel(self.root);dialog.title("Duckmeta help and reference");dialog.geometry("700x650");dialog.configure(bg=PANEL)
        text=tk.Text(dialog,bg=PANEL,fg=TEXT,wrap="word",font=(self.font,11),padx=20,pady=20)
        scroll=ttk.Scrollbar(dialog,command=text.yview);scroll.pack(side="right",fill="y");text.configure(yscrollcommand=scroll.set);text.pack(fill="both",expand=True)
        intro=("DUCKMETA — PYTHON EDITION\n\nOpen a PNG, select a modifier, and adjust its sliders or raw bytes. Add modifiers from the searchable picker. Use Move up/down to place randomizers immediately after their target. Undo and Redo affect metadata edits. Export PNG to save.\n\nClick the preview for keyboard control: arrows move, Space jumps, Q quacks. You can also use the buttons. Preview settings are not written into the hat. IDs 70/71 export but sound playback is not included.\n\nThis is an independent simulation, not the Duck Game runtime. Movement, cape geometry, particles and defaults approximate the supplied reference. Non-particle randomizers use their midpoint; particle values are sampled per spawn. Rotation uses radians. Final hats need an in-game check.\n\nSheet layout: 32×32 idle and quack hats, third 32×32 cell cape, 24×24 particles at Y=32. Other artwork and unknown metadata are preserved.\n\nORIGINAL REFERENCE\n\n")
        text.insert("end",intro+(ASSETS/"metapixels-reference.txt").read_text(encoding="utf-8"));text.configure(state="disabled")

    def close(self):
        if self.confirm_replace():
            self.closed=True
            if self.timer:self.root.after_cancel(self.timer)
            self.root.destroy()
