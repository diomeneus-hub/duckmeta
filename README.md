# Duckmeta — the hat workshop

## Download the Python app

[**Download Duckmeta-Python.zip**](https://github.com/diomeneus-hub/duckmeta/raw/refs/heads/main/downloads/Duckmeta-Python.zip)

Extract the entire ZIP, then follow its `README.md` to install Pillow and launch the desktop editor. Python 3.10+ with Tkinter is required. Linux and Windows launch scripts are included. This is Python source, not a standalone executable.

**Native Python app:** see [python_app/README.md](python_app/README.md). It uses Tkinter and Pillow, with a native animated preview and all 35 metapixel definitions. Launch from that folder with `python duckmeta.py` after installing its requirements. The rest of this document describes the browser edition.

A browser-based Duck Game hat metapixel editor with a small, independent preview engine. Import a hat, edit its ordered metadata pixels, run/jump/quack in the preview, and export a PNG. All image processing happens locally in the browser; no account, backend, or API key is needed.

## Run it

**Simplest option:** open the packaged `Duckmeta.html` in Chrome, Firefox, or Edge. It includes the sprites, example hat, and reference; no server or internet connection is needed. Import/export still use your browser’s file picker and downloads.

For development, requires Node.js 22.12+ (Node 24 recommended) and npm.

```sh
npm ci
npm run dev
```

Open the address printed by Vite in your local browser. On a computer without Node, the `dist` folder from a build can be served by any static web server. For example: `python3 -m http.server 8080 --directory dist`. JavaScript modules require serving over HTTP rather than double-clicking the HTML file.

```sh
npm run build       # TypeScript check, production bundle, and standalone dist/Duckmeta.html
npm test            # Format, preservation, ordering, and decoding tests
npm run test:browser # Chromium integration and responsive layout tests
```

Browser tests default to `/usr/bin/chromium`. Set `CHROMIUM_PATH` to your Chromium/Chrome executable on another machine. The tests start and stop their own Vite server when one is not already running. Screenshots go in ignored `test-results/`.

In the Codex cloud environment, use `npm --cache /tmp/duckmeta-npm ci` if the default npm cache directory is not writable. Work in `/workspace/duckmeta`; no worktree is needed.

## Use it

1. The wizard example starts with a working metadata stack. Import your own PNG with **Import PNG**.
2. Choose a stack row to inspect it. **Add modifier** includes all 35 IDs in the supplied reference. Sliders show decoded units; the raw G/B inputs let you enter any byte, including values beyond a vector’s clamped range.
3. Change duck color, switch Idle/Run, jump, flip, or quack to emit particles. Focus the preview for arrow-key movement, Space to jump, and Q to quack. Auto quack repeatedly emits particles. Pause freezes simulation but still lets you inspect changes. Optional sound is synthesized.
4. Use the row arrows to reorder effects, particularly randomizers. Multiple randomizers target the preceding non-randomizer. Undo/redo covers metadata edits, insertion, movement, and removal.
5. **Export hat** downloads a PNG containing the original artwork and exactly one metadata column. Importing an exported file reads that column back. Edits are held in memory, so export before closing the tab. Replacing unsaved work asks for confirmation.

## PNG layout and preservation

- Input artwork widths are multiples of 32, optionally plus one metadata column. Height must be 32–1024 pixels; artwork width at most 1024. Maximum input file size: 8 MB.
- Supports 8-bit RGB, RGBA, grayscale, grayscale+alpha and indexed PNGs. Unsupported high-bit-depth images are rejected rather than silently quantized.
- The preview interprets the first 32×32 cell as idle, the next as quack, and the third as a cape. The row at Y=32 contains 24×24 particle frames. Only wholly empty trailing particle cells are trimmed for animation. Artwork elsewhere is preserved but not rendered by this initial preview layout.
- `fast-png` decodes and encodes raw image bytes. Canvas is used only for display, avoiding alpha premultiplication damage to exported metadata or artwork. PNG CRC checking is enabled.
- Original artwork RGBA values, unknown metadata IDs, duplicate IDs, transparent metadata, and untouched row positions are preserved. Export standardizes the file to an 8-bit RGBA PNG; original PNG ancillary chunks/compression are not preserved.
- A boolean is active whenever its metadata pixel has nonzero alpha. Remove the modifier or set alpha to zero to disable it. Raw alpha values are preserved, although fully opaque metadata is recommended for in-game validation.
- Duplicate IDs remain in the file; the preview uses the last occurrence. Insertions shift rows only as far as the next entirely empty row, and cannot overwrite a full column. Remove clears one row. No automatic sorting is performed.

## Preview accuracy

This is **not the Duck Game runtime**. It uses supplied artwork and a fixed 60 Hz simulation with approximate movement, cape deformation/trails, particle presets, emitter shapes, gravity, friction, opacity, scale, rotation, anchoring, and sprite animation. Metadata byte conversions follow the supplied reference. Exact game timing, origins, default values, and some rendering details are not specified there and need comparison with the game. Hat placement/color and exported bytes are directly inspectable; final behavior still needs an in-game check.

Known interpretation choices:

- The reference labels particle emitter offset `VEC(16)` but also mentions 0–16. The editor uses its general signed VEC definition (G/B minus 128, clamped to ±16).
- Particle preset behavior uses **B**, as specified by the document; the legacy Python description incorrectly said G. A present preset of None emits nothing; other presets override custom particle modifiers.
- Particle count uses the stated `INT(8)` conversion. Negative counts emit zero particles.
- Normalized negative values use `raw / 255 * 2 - 1`; 128 therefore is near, not exactly, zero. The reference’s randomizer example has inconsistent values and an ID typo; the editor follows its type definitions.
- Particle rotation units are unspecified in the reference; preview uses radians. Gravity/velocity units and preset formulas are approximations. Defaults for omitted effects are chosen for preview usability, not claimed game defaults.
- Cape attachment, width, weight and wind motion are approximations. Non-particle randomizers use the range midpoint for a stable preview; particle randomizers are sampled on each spawn.
- IDs 70/71 export normally. Synth sound is illustrative and does not reproduce original game audio. Missing particle art in a short sheet uses a small placeholder square. No original game binaries or runtime are included.

## Recovered files and provenance

The uploaded archive **did contain the old Python source**, at `DuckGameMeta/Scripts/DuckGameMeta.py`. A recovered copy is in `docs/legacy-editor.py`; it is reference material and is not executed by the app. The uploaded metapixel document is in `docs/metapixels-reference.txt` and is treated as a format reference, not setup instructions.

The example wizard sheet and original duck sheet came from the user-supplied archive. `public/assets/duck.png` is the clean gray duck cell, with its body colors converted to white/157-gray for tinting. Asset rights remain with their respective owners. No blanket license is asserted for the supplied artwork.

## Project map

- `src/document.ts`: PNG import/export, metadata rows, ordered randomizer evaluation.
- `src/meta.ts`: effect definitions and numeric conversions.
- `src/preview.ts`: canvas rendering and fixed-step preview simulation.
- `src/main.ts`: editor interactions and history.
- `src/style.css`: responsive workshop UI.
- `tests/`: format and real-browser validation.
