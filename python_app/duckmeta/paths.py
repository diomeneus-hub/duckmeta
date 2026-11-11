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
    """Prefer modern game save roots; use Documents only for legacy installs.

    An existing DuckGame root is required. Merely having a Proton Documents
    directory does not establish that the game stores its saves there.
    """
    home = Path.home() if home is None else Path(home)
    platform = os.name if platform is None else platform
    modern, legacy = [], []
    if platform == "nt":
        modern.append(Path(os.environ.get("APPDATA", home / "AppData/Roaming")))
        legacy.extend([home / "Documents", home / "OneDrive/Documents"])
    else:
        for library in steam_libraries(home):
            users = library / "steamapps/compatdata" / APP_ID / "pfx/drive_c/users"
            try:
                profiles = [users / "steamuser"]
                if users.is_dir():
                    profiles.extend(p for p in sorted(users.iterdir())
                                    if p.is_dir() and p.name not in ("steamuser", "Public"))
                for profile in profiles:
                    modern.append(profile / "AppData/Roaming")
                    legacy.extend([profile / "Documents", profile / "My Documents"])
            except OSError:
                continue
        modern.append(Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")))
    for locations in (modern, legacy):
        candidates = [base / HATS for base in locations if (base / "DuckGame").is_dir()]
        if candidates:
            return next((p for p in candidates if p.is_dir()), candidates[0])
    return None


def fallback_directory() -> Path:
    home = Path.home()
    return home / "Documents" if (home / "Documents").is_dir() else home


def steam_libraries(home: Path | None = None) -> list[Path]:
    home=Path.home() if home is None else Path(home)
    roots=[home/".local/share/Steam",home/".steam/steam",home/".steam/root",
           home/".var/app/com.valvesoftware.Steam/.local/share/Steam",
           home/".var/app/com.valvesoftware.Steam/data/Steam"]
    if os.name=="nt":
        for key in ("PROGRAMFILES(X86)","PROGRAMFILES"):
            if os.environ.get(key):roots.append(Path(os.environ[key])/"Steam")
    libraries=list(roots)
    for root in roots:
        for vdf in (root/"steamapps/libraryfolders.vdf",root/"config/libraryfolders.vdf"):
            libraries.extend(_library_paths(vdf))
    unique=[];seen=set()
    for path in libraries:
        try:
            real=path.resolve()
            if real not in seen:unique.append(path);seen.add(real)
        except OSError:continue
    return unique


def find_content_directory(home: Path | None = None) -> Path | None:
    for library in steam_libraries(home):
        base=library/"steamapps/common"
        for name in ("Duck Game","DuckGame"):
            content=base/name/"Content"
            if content.is_dir():return content
    return None


def find_duck_textures(content: Path) -> tuple[Path | None, Path | None]:
    """Find exact duck/duckQuack stems, avoiding similarly named icons or hats."""
    matches={"duck":[],"duckquack":[]}
    for index,path in enumerate(content.rglob("*")):
        if index>=30000:raise ValueError("Content folder has too many files to scan. Load the duck texture manually.")
        stem=path.stem.lower().replace("_","").replace("-","")
        if stem in matches and path.suffix.lower() in (".xnb",".png") and path.is_file():
            matches[stem].append(path)
    result=[]
    for key in ("duck","duckquack"):
        choices=sorted(matches[key],key=lambda p:(len(p.parts),str(p).lower()))
        result.append(choices[0] if choices else None)
    return tuple(result)
