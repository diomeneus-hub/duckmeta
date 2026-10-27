# Duckmeta — Python desktop edition

A native **Tkinter + Pillow** app for editing Duck Game hat metapixels with a live duck preview. No browser, Node.js, or web server is needed. All image editing takes place on your computer.

## Start on Linux

Use Python 3.10 or newer with Tkinter. On Debian/Ubuntu, install the desktop prerequisites if missing:

```sh
sudo apt install python3 python3-venv python3-tk
```

Open a terminal **inside this folder**, then run:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python duckmeta.py
```

On later launches, run `./start-duckmeta.sh` or `.venv/bin/python duckmeta.py`. The shell launcher finds its own folder, so it can also be run from elsewhere. A desktop session is needed to show the window.

## Start on Windows

Install Python 3.10+ from python.org, including Tcl/Tk and the Python launcher. Extract the **entire** app folder, open a terminal inside it, then run:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe duckmeta.py
```

On later launches, double-click `Start-Duckmeta.bat`. It uses the local virtual environment when present. This package contains Python source, not a standalone Windows executable. Linux GUI tests have been run; Windows has not been tested on a Windows machine.

## How to use it

- The wizard sample loads automatically. **Open PNG** reads your own hat sheet and existing metapixel column.
- Select an effect in the stack, then change its sliders. Labels show decoded values and raw byte values. **Apply raw values** accepts exact G, B and alpha values (0–255). Red identifies the effect and is read-only.
- **Add modifier** searches all 35 IDs from the supplied reference. Booleans are enabled by the pixel's presence; remove the row or set alpha to zero to disable one.
- **Move up/down** reorders rows. Randomizers affect the preceding non-randomizer. Unknown and duplicate IDs remain in the file; preview uses the last occurrence of a repeated ID.
- Click the preview for keyboard control: **Left/Right** move, **Space** jumps, **Q** quacks. Buttons provide the same actions. Change duck color, zoom, flip, run/idle, pause, or enable auto quack. Preview preferences are not saved as hat metadata.
- **Export PNG** saves the original artwork plus exactly one metadata column. Existing files are replaced atomically after the file dialog's overwrite confirmation. Edits are held in memory until export; closing or replacing unsaved work offers Save / Discard / Cancel.
- **Ctrl+O / Ctrl+S / Ctrl+Z / Ctrl+Y** open, export, undo and redo. Undo/redo applies to metadata edits; the history resets when a different PNG is loaded.
- **Help** contains usage instructions and the original metapixel document.

You can open a hat directly with `python duckmeta.py path/to/hat.png`.

## Preview scope

The engine uses a fixed 60 Hz simulation and renders through Pillow into a Tk canvas at approximately 30 frames per second. It includes hat offsets and tinting, approximate run/jump animation, cape deformation and trails, particle shapes/presets, velocity/gravity/friction, alpha, scale, rotation, anchoring, layer order and sprite animation.

It is an **independent approximation**, not Duck Game itself. Defaults, attachment points, motion, particle presets and cloth physics need an in-game comparison. IDs 70/71 are editable/exportable but **audio playback is not implemented**. Non-particle randomizers use the range midpoint for a stable preview; particle randomizers are sampled per spawn. Rotation is treated as radians because the reference doesn't specify units. Present preset 31 overrides custom particle modifiers; B selects the preset and None emits nothing. VEC uses signed offsets around 128, including emitter offset 30. INT particle counts use G minus 128, clamped to ±8; negative counts emit nothing.

The sprite layout used in the preview is:

- First two 32×32 cells: idle and quacking hat.
- Third 32×32 cell: cape.
- Row beginning at Y=32: 24×24 particle frames, with empty trailing cells trimmed.

Artwork outside these regions is preserved but not previewed. Missing particle art in a short sheet gets a placeholder square.

## File preservation

Accepts 8-bit RGB, RGBA, grayscale, grayscale+alpha and indexed PNGs. Width must be a multiple of 32, optionally plus one metadata column. Artwork is limited to 1024×1024 and input files to 8 MB. Unsupported bit depths and malformed PNGs are rejected before editing.

Artwork RGBA bytes, transparent RGB, unknown metadata IDs, row order, duplicate IDs, and untouched alpha values are preserved. Export writes a standard 8-bit RGBA PNG; original ancillary chunks and compression settings are not preserved. Metadata rows are not sorted. Insertion moves following rows only to the next wholly empty row and refuses to overwrite a full column. All references are treated as format documentation, not executable instructions.

## Tests and headless preview

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python duckmeta.py --render preview.png
```

Without a display, the five GUI tests are explicitly skipped and model/renderer tests still run. To test the actual GUI on a headless Linux machine, install `xvfb` and `xauth`, then run:

```sh
xvfb-run -a .venv/bin/python -m unittest discover -s tests -v
```

Set `DUCKMETA_SCREENSHOT` to a PNG path to save a GUI screenshot during its screenshot test. Twenty tests cover PNG round trips, unknown/transparent bytes, indexed images, validation, randomizers, history, animation, live rendering, and window/control/file-dialog callbacks. Native file pickers are mocked in automation; their import/export callbacks read and write actual temporary PNGs.

## Contents

- `duckmeta.py`: launcher and headless render command.
- `duckmeta/app.py`: native desktop UI.
- `duckmeta/model.py`: PNG data, metapixel evaluation and history.
- `duckmeta/preview.py`: simulation and pixel rendering.
- `duckmeta/effects.json`: all 35 reference definitions.
- `assets/`: supplied wizard artwork, derived duck sprite, and reference.
- `tests/`: standard-library unittest suite.

Assets came from the user's old project archive. The duck sprite was derived from its clean gray duck cell. Asset rights remain with their respective owners; no blanket artwork license is asserted. The recovered legacy Python editor remains in the parent project's `docs/legacy-editor.py`.
