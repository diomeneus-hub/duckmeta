#!/usr/bin/env python3
"""Run the native Duckmeta editor, or render a headless preview for validation."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description="Duckmeta — native Duck Game hat editor")
    parser.add_argument("hat",nargs="?",help="Optional hat PNG to open")
    parser.add_argument("--render",metavar="PNG",help="Render a sample preview to PNG without a desktop display")
    args=parser.parse_args()
    try:
        from duckmeta.model import Hat
        from duckmeta.preview import Preview
    except ImportError as exc:
        print(f"Missing dependency: {exc}\nInstall with: python -m pip install -r requirements.txt",file=sys.stderr)
        return 1
    try:
        hat=Hat.read(args.hat) if args.hat else Hat.example()
    except Exception as exc:
        print(f"Could not open hat: {exc}",file=sys.stderr);return 1
    if args.render:
        preview=Preview(hat,seed=1);preview.quack()
        for _ in range(20):preview.advance(1/60)
        preview.render().resize((1152,720),resample=0).save(args.render)
        print(f"Preview saved to {Path(args.render).resolve()}");return 0
    try:
        import tkinter as tk
        from duckmeta.app import App
    except ImportError as exc:
        print(f"Tkinter is required: {exc}\nOn Debian/Ubuntu: sudo apt install python3-tk",file=sys.stderr);return 1
    try:root=tk.Tk()
    except tk.TclError as exc:
        print(f"A desktop display is required: {exc}\nRun this app on your desktop, or use --render preview.png for a headless preview.",file=sys.stderr);return 1
    App(root,hat)
    root.mainloop()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
