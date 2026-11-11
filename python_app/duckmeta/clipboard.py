"""Copy original PNG bytes to Linux image clipboards."""
import os
import shutil
import subprocess


def copy_png(data):
    if os.environ.get('WAYLAND_DISPLAY') and shutil.which('wl-copy'):
        command = ['wl-copy', '--type', 'image/png']
    elif os.environ.get('DISPLAY') and shutil.which('xclip'):
        command = ['xclip', '-selection', 'clipboard', '-t', 'image/png', '-i']
    else:
        raise RuntimeError('Image copying needs wl-clipboard on Wayland or xclip on X11. '
                           'On EndeavourOS install with: sudo pacman -S wl-clipboard xclip')
    # The helper retains clipboard ownership. Do not inherit output pipes.
    try:
        subprocess.run(command, input=data, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError('Could not copy the PNG to the desktop clipboard. Check that your clipboard helper can access the desktop.') from exc
