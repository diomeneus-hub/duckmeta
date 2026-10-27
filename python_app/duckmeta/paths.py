"""Locate Duck Game's hats under native Windows or Linux Steam/Proton."""
from __future__ import annotations

import os
import re
from pathlib import Path

APP_ID = "312530"
HATS = Path("DuckGame") / "Custom" / "Hats"


def _library_paths(vdf: Path):
    try:
        contents = vdf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    paths = []
    # Both modern nested "path" entries and old numbered library entries.
    for key, value in re.findall(r'"((?:[^"\\]|\\.)*)"\s*"((?:[^"\\]|\\.)*)"', contents):
        if key == "path" or key.isdigit():
            value = re.sub(r'\\([\\"])', r'\1', value)
            path = Path(value).expanduser()
            if path.is_absolute():
                paths.append(path)
    return paths


def find_hats_directory(home: Path | None = None, platform: str | None = None) -> Path | None:
    """Return a detected hats folder without creating anything.

    Existing hats folders win over empty-prefix candidates. If a verified game's
    Documents folder exists, its missing Custom/Hats folder can be created on export.
    """
    home = Path.home() if home is None else Path(home)
    platform = os.name if platform is None else platform
    documents = []
    if platform == "nt":
        documents.extend([home / "Documents", home / "OneDrive" / "Documents"])
    else:
        roots = [home / ".local/share/Steam", home / ".steam/steam", home / ".steam/root",
                 home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
                 home / ".var/app/com.valvesoftware.Steam/data/Steam"]
        libraries = list(roots)
        for root in roots:
            for vdf in [root / "steamapps/libraryfolders.vdf", root / "config/libraryfolders.vdf"]:
                libraries.extend(_library_paths(vdf))
        seen = set()
        for library in libraries:
            try:
                resolved = library.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                users = library / "steamapps/compatdata" / APP_ID / "pfx/drive_c/users"
                profiles = [users / "steamuser"]
                if users.is_dir():
                    profiles.extend(p for p in sorted(users.iterdir()) if p.is_dir() and p.name not in ("steamuser", "Public"))
                for profile in profiles:
                    documents.extend([profile / "Documents", profile / "My Documents"])
            except OSError:
                continue
    candidates = [directory / HATS for directory in documents if directory.is_dir()]
    return next((p for p in candidates if p.is_dir()), candidates[0] if candidates else None)


def fallback_directory() -> Path:
    home = Path.home()
    return home / "Documents" if (home / "Documents").is_dir() else home
