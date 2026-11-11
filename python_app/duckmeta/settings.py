"""Local editor preferences, separate from Duck Game's files."""
import json
import os
import tempfile
from pathlib import Path


def settings_path():
    base = os.environ.get('APPDATA') if os.name == 'nt' else os.environ.get('XDG_CONFIG_HOME')
    return (Path(base) if base else Path.home()/'.config')/'duckmeta/settings.json'


def read_export_folder(path):
    try:
        value = json.loads(path.read_text()).get('export_folder')
        if isinstance(value, str) and Path(value).is_absolute():
            return Path(value)
    except (OSError, ValueError, AttributeError):
        pass
    return None


def write_export_folder(path, folder):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({'export_folder': str(folder)}, stream)
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
