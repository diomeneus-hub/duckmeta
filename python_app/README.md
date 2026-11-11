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

## Default export folder on EndeavourOS / Linux

**Export PNG** defaults to Duck Game's hats folder, normally:

```text
~/.local/share/Steam/steamapps/compatdata/312530/pfx/drive_c/users/steamuser/AppData/Roaming/DuckGame/Custom/Hats
```

The editor detects regular Steam installs, `.steam` aliases, Flatpak Steam, extra Steam libraries, and alternate Proton usernames. It prefers an existing `AppData/Roaming/DuckGame` save root over legacy Documents saves, including when an old Documents folder contains exported hats. It only creates `Custom/Hats` under a detected game save root. Windows uses `%APPDATA%`; native Linux uses `$XDG_CONFIG_HOME` (normally `~/.config`).

**Open PNG** starts in the same folder as Export PNG. The adjacent **+ / −** buttons below the metadata list add and remove modifiers.

Use **File → Choose export folder...** to save an explicit default across restarts. Preferences live in `~/.config/duckmeta/settings.json` (or your platform's application configuration folder). Automatic detection does not override this choice. The export dialog also lets you pick a different destination for an individual file.

If you previously exported into the Proton Documents folder, copy those PNGs into the active AppData hats folder and restart the game. Check `Documents/DuckGame/where_is_my_save.txt` in the same prefix for the game's migration notice. Legacy installs may still use Documents; detection falls back to it when no modern save root exists. If no game save root is found, choose the destination manually.

## Base hats and XNB textures

Use **File → Load base hat...** (Ctrl+B). The file picker starts in Duck Game's detected Content folder, normally:

```text
~/.local/share/Steam/steamapps/common/Duck Game/Content
```

Choose an individual hat `.xnb` texture. **File → Choose game Content folder...** lets you point at a different install; additional Steam libraries are also detected. The app reads the texture into a new editable hat and exports a custom PNG to your usual hats folder. It does not write XNBs, and Export rejects non-PNG filenames.

Supported XNBs: XNA versions 4/5, Texture2D assets, uncompressed/LZX/LZ4 containers, Color RGBA, Bgr565, Bgra5551, Bgra4444, DXT1/3/5 and Alpha8 surfaces. The first mipmap supplies the artwork; remaining mipmaps are validated. Sounds, models, fonts, shared-resource objects, console texture layouts and other surface formats are rejected with an explanation. Base hats still need the editor's 32-pixel-column layout and size limits.

XNA textures normally use premultiplied alpha. Import converts them to straight RGBA for editing and PNG export, so semi-transparent colors may incur rounding; colors already lost by compression or zero alpha cannot be recovered. The original XNB file is untouched. Original-PNG byte-preservation guarantees apply to PNG import, not to reconstructing pre-compilation artwork from XNB.

**Updating from an older release:** reinstall requirements in the app's virtual environment before loading compressed XNBs:

```sh
.venv/bin/python -m pip install -r requirements.txt
```

This adds `pylibmspack` for LZX and `lz4` for LZ4; decoding happens locally without Node or command-line converters.

## Real duck animation frames

On startup, the app looks under the detected Content folder for `duck.xnb`/`duck.png` and `duckQuack.xnb`/`duckQuack.png` (case-insensitive). You can also load them through **File → Load duck sprite sheet...** and **Load quack sprite sheet...**. The live preview header identifies the loaded source and frame counts. If no sprites are available, it explicitly says **Single-frame fallback**; it does not invent extra duck frames.

The normal importer accepts 32×32 row-major grids. It also recognizes the **387×781 annotated reference sheet shown in the conversation**, extracting the normal section at `(0,8)` and quack section at `(194,8)` without the surrounding labels. Use the original PNG at its original size, not a scaled screenshot. The inline chat image was not available as a downloadable file in the cloud, so it is **not bundled**: select your saved copy locally, or use the textures from your game install. Original transparent assets give the correct background; the importer does not erase black pixels that might be sprite outlines.

**Preview → Animation settings / sprite frames...** displays a numbered atlas and lets you set frame indices and FPS for idle, walk, run, jump, fall and crouch. Default mappings are inferred (idle 0, walk/run 0–5, jump/fall 6, crouch 7 where available), with 6 FPS walk and 12 FPS run. They are not claimed to be the exact game animation definitions. Mappings and manually selected source paths apply to the current session. Separate quack textures use the matching frame index; missing quack frames fall back to the normal body.

The renderer now draws actual animation frames, rather than adding rectangle feet or a simulated beak. White/gray head detection adjusts the hat, cape attachment and particle emitter as the head moves between frames. Movement accelerates and decelerates, and animation rate follows movement speed. Click the preview and use arrows to move, Down to crouch, Space to jump, and hold Q to keep the quack pose. Walk and Run buttons choose separate speeds. The movement/physics values and head detection remain approximations, and arm/weapon overlays are not simulated.

## How to use it

- The wizard sample loads automatically. **Open PNG** reads your own hat sheet and existing metapixel column.
- Select an effect in the stack, then change its sliders. Labels show decoded values and raw byte values. **Apply raw values** accepts exact G, B and alpha values (0–255). Red identifies the effect and is read-only.
- **Add modifier** searches all 35 IDs from the supplied reference. Booleans are enabled by the pixel's presence; remove the row or set alpha to zero to disable one.
- **Move up/down** reorders rows. Randomizers affect the preceding non-randomizer. Unknown and duplicate IDs remain in the file; preview uses the last occurrence of a repeated ID.
- Click the preview for keyboard control: **Left/Right** move, **Down** crouches, **Space** jumps, hold **Q** to quack. Buttons provide the same actions. Change duck color, zoom, flip, walk/run/idle, pause, or enable auto quack. Preview preferences are not saved as hat metadata.
- **Export PNG** saves the original artwork plus exactly one metadata column. Existing files are replaced atomically after the file dialog's overwrite confirmation. Edits are held in memory until export; closing or replacing unsaved work offers Save / Discard / Cancel.
- **Ctrl+O / Ctrl+S / Ctrl+Z / Ctrl+Y** open, export, undo and redo. Undo/redo applies to metadata edits; the history resets when a different PNG is loaded.
- **Help** contains usage instructions and the original metapixel document.

You can open a hat directly with `python duckmeta.py path/to/hat.png`.

## Preview scope

The engine uses a fixed 60 Hz simulation and renders through Pillow into a Tk canvas at approximately 30 frames per second. It includes hat offsets and tinting, imported duck animation frames, cape deformation and trails, particle shapes/presets, velocity/gravity/friction, alpha, scale, rotation, anchoring, layer order and sprite animation.

It is an **independent approximation**, not Duck Game itself. Defaults, attachment points, motion, particle presets and cloth physics need an in-game comparison. IDs 70/71 are editable/exportable but **audio playback is not implemented**. Non-particle randomizers use the range midpoint for a stable preview; particle randomizers are sampled per spawn. Particle rotation is decoded in tens of degrees (36 = 360°). Present preset 31 overrides custom particle modifiers; B selects the preset and None emits nothing. VEC uses signed offsets around 128, including emitter offset 30. Particle count uses raw G, clamped to 0–8; zero emits nothing. Older editor versions incorrectly displayed G minus 128; existing bytes are preserved, so check count in older hats.

The sprite layout used in the preview is:

- First two 32×32 cells: idle and quacking hat.
- Third 32×32 cell: cape.
- Rock image: 24×24 at (0,32), preserved but not previewed.
- Four 12×12 particle cells: (24,32), (36,32), (24,44), (36,44). Empty cells are skipped.

Artwork outside these regions is preserved but not previewed. Missing particle art emits nothing. Magenta is transparent in the preview; original artwork bytes remain unchanged on export.

## Why built-in hats have separate effects

Texture2D XNBs contain compiled image data (dimensions, surface format, mipmaps, and sometimes compression), not an entire hat behavior definition. Game code selects and combines textures. Senpai uses `hats/sensei` for its hat and overlays `hats/senpaiStar`; Master uses `hats/master_glow` for its quack eye glow, not a launched spark. These game-coded overlays are not simulated or included when exporting an imported base hat as a custom PNG. Custom PNG particles need actual artwork in the particle cells.

These corrections were checked against the public Duck Game Rebuilt source (a modified decompilation, not a runtime verification of your Steam build): [save location selection](https://github.com/TheFlyingFoool/DuckGameRebuilt/blob/cda9564afe4baf07ff5cf958227e7bb48a4c7db9/DuckGame/src/MonoTime/File/DuckFile.cs#L219), [custom PNG layout](https://github.com/TheFlyingFoool/DuckGameRebuilt/blob/cda9564afe4baf07ff5cf958227e7bb48a4c7db9/DuckGame/src/DuckGame/Profile/Team.cs#L143), and [built-in overlays](https://github.com/TheFlyingFoool/DuckGameRebuilt/blob/cda9564afe4baf07ff5cf958227e7bb48a4c7db9/DuckGame/src/DuckGame/Equipment/TeamHat.cs#L561).

## Copying sprite sheets

Right-click the sprite sheet at the bottom of the editor. **Copy sprite sheet** copies original-resolution artwork as a transparent PNG, without the metadata column. **Copy sprite sheet with metadata** includes the current metadata column. Neither copies the scaled preview or checkerboard. Paste into an image editor that accepts PNG clipboard data.

Linux image clipboard support uses `wl-copy` on Wayland or `xclip` on X11. On EndeavourOS install the helpers if needed:

```sh
sudo pacman -S wl-clipboard xclip
```

Clipboard routing, error handling, and the copied PNG's dimensions/pixels are tested; pasting into your desktop image editor still needs a local check. Other operating systems currently have no image clipboard backend.

## Coordinate corrections

Hat offset is subtracted from the head position, matching the game's equipment placement: increasing G moves backward and increasing B moves up. Horizontal movement reverses when the duck faces left. Cape and emitter offsets are additive, so they must not all be inverted. Signed normalized vector values now have exact zero at byte 128 and endpoints −1/+1. Cape sway uses horizontal displacement and vertical length, not rotation; cape cloth remains approximate. Exported raw metadata is unchanged by these preview corrections, so existing hats need no byte migration.

## Senpai-style star experiment

This is an unverified custom-particle approximation, not the built-in Senpai overlay. Redraw the star inside four transparent 12×12 cells at (24,32), (36,32), (24,44), (36,44). Keep the centers aligned. Use small → medium → large → medium artwork for a repeating pulse (for example 6, 8, 10, 8 pixels wide). The 24×24 cell is the rock, not particle art.

Remove Particle preset (31); do not select its None option, which disables emission in this preview. Suggested raw G/B bytes (metadata alpha stays 255):

| Modifier | G | B | Purpose |
| --- | ---: | ---: | --- |
| Particle count (34) | 1 | 0 | One star per quack |
| Lifespan (35) | 255 | 0 | Two seconds |
| Velocity (36) | 128 | 128 | Stationary |
| Gravity (37) | 128 | 128 | No falling |
| Alpha (39) | 128 | 128 | About 50% opacity throughout |
| Scale (40) | 128 | 128 | Approximately original size; pulse is in artwork |
| Rotation (41) | 0 | 255 | One turn over its lifetime |
| Emitter offset (30) | 130 | 132 | Start around +2/+4; tune placement in-game |
| Emitter shape (32) | 0 | 0 | Point |

Enable Anchor particles (44), Animate particles (45), and Loop particle animation (46). Leave Random animation start (47) and Particles behind duck (43) absent initially. Start Animation speed (48) low and adjust visually. Keep the star art opaque if using the Alpha modifier above, to avoid halving opacity twice.

Animation looping repeats the four images while that particle lives; it does not make emission or lifetime infinite. Start/end scale and rotation do not independently ping-pong. Repeated quacks can overlap particles. The built-in star's quack-held fade and continuous pulse cannot be guaranteed by this recipe; export and compare in-game.

## Saved metadata templates

Below the + / - modifier buttons, **Save as template** opens a named template dialog with a checkbox for every enabled metapixel. Save any selection; randomizers must be selected with their target modifier. Order, duplicates, unknown IDs, raw channels, and alpha are retained. Template names must be unique (case-insensitive).

**Apply template** lists saved templates. It replaces matching modifier IDs and their attached randomizers, keeps unrelated modifiers and all artwork, and asks for confirmation before replacing existing settings. An identical template is a no-op. If the merged metadata cannot fit the hat's rows, nothing changes. Apply is a single Undo operation: use **Undo** at the top of the inspector or **Ctrl+Z**; **Ctrl+Y** redoes it. Saving a template does not change the hat.

Templates persist as versioned JSON files under `~/.config/duckmeta/templates/` (or the platform configuration folder next to `settings.json`), not in Duck Game's hats folder or the downloaded application directory. These are metadata-only presets: particle artwork must already exist in the destination hat. Corrupt templates are reported and skipped.

Particle scale metadata accepts 0–2, but Duck Game clamps the interpolated visible scale to 0–1. The preview now applies this clamp too: 1→2 stays full-size, while 0→2 grows to full-size and then stays there. Existing raw metadata is preserved.

The stock custom-particle settings do not provide the built-in Senpai overlay's held-quack lifetime and release behavior. Passive particle conditions (110–113) in the cited reference source are marked as Duck Game Rebuilt additions; do not rely on them in regular Steam Duck Game. A static star drawn into the quack hat frame can follow the pose, but cannot continuously spin or pulse like the built-in overlay.

## File preservation

Accepts 8-bit RGB, RGBA, grayscale, grayscale+alpha and indexed PNGs. Width must be a multiple of 32, optionally plus one metadata column. Artwork is limited to 1024×1024 and input files to 8 MB. Unsupported bit depths and malformed PNGs are rejected before editing.

Artwork RGBA bytes, transparent RGB, unknown metadata IDs, row order, duplicate IDs, and untouched alpha values are preserved. Export writes a standard 8-bit RGBA PNG; original ancillary chunks and compression settings are not preserved. Metadata rows are not sorted. Insertion moves following rows only to the next wholly empty row and refuses to overwrite a full column. All references are treated as format documentation, not executable instructions.

## Tests and headless preview

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python duckmeta.py --render preview.png
```

Without a display, the fourteen GUI tests are explicitly skipped and model/renderer tests still run. To test the actual GUI on a headless Linux machine, install `xvfb` and `xauth`, then run:

```sh
xvfb-run -a .venv/bin/python -m unittest discover -s tests -v
```

Set `DUCKMETA_SCREENSHOT` to a PNG path to save a GUI screenshot during its screenshot test. Sixty-four tests cover PNG round trips, unknown/transparent bytes, indexed images, validation, randomizers, history, animation, live rendering, XNB containers and surface formats, Steam Content discovery, frame selection and head alignment, and window/control/file-dialog callbacks. XNB tests use generated fixtures, including actual LZX Huffman data and multiple LZX frames; no installed Duck Game XNB files were available in the cloud for testing. Native file pickers are mocked in automation; their import/export callbacks read and write actual temporary PNGs.

## Contents

- `duckmeta.py`: launcher and headless render command.
- `duckmeta/app.py`: native desktop UI.
- `duckmeta/model.py`: PNG data, metapixel evaluation and history.
- `duckmeta/preview.py`: simulation and pixel rendering.
- `duckmeta/xnb.py`: bounded Texture2D XNB decoder.
- `duckmeta/sprites.py`: grid/reference-sheet import and animation mapping.
- `duckmeta/paths.py`: Steam Content and custom hat-folder discovery.
- `duckmeta/effects.json`: all 35 reference definitions.
- `assets/`: supplied wizard artwork, derived duck sprite, and reference.
- `tests/`: standard-library unittest suite.

Assets came from the user's old project archive. The duck sprite was derived from its clean gray duck cell. Asset rights remain with their respective owners; no blanket artwork license is asserted. The recovered legacy Python editor remains in the parent project's `docs/legacy-editor.py`.
