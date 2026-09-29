"""Licenčné texty softvéru tretích strán pre inštalátor (THIRD-PARTY-NOTICES.txt).

MIT, BSD aj Apache dovoľujú šíriť program, len keď nesie ich text. Zoznam sa
skladá bez siete: balíky Pythonu ako uzáver závislostí projektu medzi
nainštalovanými (so zohľadnením extra aj podmienok platformy, takže balíky
pre macOS či Linux tu nie sú), k tomu bootloader PyInstaller, ktorý je
v každom .exe, a balíky frontendu z `package-lock.json` bez vývojových.

Použitie (v prostredí backendu):  uv run python ../packaging/notices.py <výstup>
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

LICENSE_FILE = re.compile(r"^(licen[cs]e|copying|notice)", re.IGNORECASE)
RULE = "=" * 78


@dataclass(frozen=True)
class Entry:
    name: str
    version: str
    license: str
    text: str


def _license_name(meta) -> str:
    """Krátky názov licencie: SPDX výraz, klasifikátor, alebo prvý riadok poľa License."""
    if meta.get("License-Expression"):
        return meta["License-Expression"]
    for classifier in meta.get_all("Classifier") or []:
        if classifier.startswith("License ::"):
            return classifier.split("::")[-1].strip()
    first = (meta.get("License") or "").strip().splitlines()
    return first[0][:60] if first else "neuvedená"


def _dist_text(dist: metadata.Distribution) -> str:
    texts = []
    for f in dist.files or []:
        parts = Path(str(f)).parts
        if LICENSE_FILE.match(f.name) or "licenses" in parts[:-1]:
            path = Path(dist.locate_file(f))
            if path.is_file():
                texts.append(path.read_text(encoding="utf-8", errors="replace").strip())
    if texts:
        return "\n\n".join(dict.fromkeys(texts))
    meta = dist.metadata
    urls = [u.split(",", 1)[-1].strip() for u in meta.get_all("Project-URL") or []]
    home = meta.get("Home-page") or (urls[0] if urls else "")
    return f"Licencia: {_license_name(meta)}. Balík text licencie neobsahuje; {home}".rstrip("; ")


def python_entries(project: str) -> list[Entry]:
    """Uzáver závislostí `project` medzi nainštalovanými balíkmi, bez neho samého."""
    seen: dict[str, Entry] = {}
    queue: list[tuple[str, frozenset[str]]] = [(project, frozenset())]
    while queue:
        name, extras = queue.pop()
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue  # podmienená závislosť pre iný systém
        key = canonicalize_name(dist.metadata["Name"])
        if key in seen and not extras:
            continue
        if key != canonicalize_name(project):
            seen[key] = Entry(
                dist.metadata["Name"], dist.version, _license_name(dist.metadata), _dist_text(dist)
            )
        for raw in dist.requires or []:
            req = Requirement(raw)
            envs = [{"extra": e} for e in extras] or [{"extra": ""}]
            if req.marker and not any(req.marker.evaluate(env) for env in envs):
                continue
            queue.append((req.name, frozenset(req.extras)))
    return sorted(seen.values(), key=lambda e: e.name.lower())


def pyinstaller_entry() -> Entry:
    """Bootloader PyInstaller je súčasťou .exe; jeho GPL má výnimku pre takéto programy."""
    dist = metadata.distribution("pyinstaller")
    return Entry("PyInstaller", dist.version, "GPL-2.0 s výnimkou pre bootloader", _dist_text(dist))


def _resolve(frontend: Path, parent: Path, name: str) -> Path | None:
    """Rozlíšenie ako v Node: node_modules pri balíku, potom vyššie až po frontend."""
    here = parent
    while True:
        candidate = here / "node_modules" / name
        if (candidate / "package.json").is_file():
            return candidate
        if here == frontend:
            return None
        here = here.parent
        if here.name == "node_modules":
            here = here.parent


def npm_entries(frontend: Path) -> list[Entry]:
    """Uzáver `dependencies` z package.json (bez vývojových a voliteľných)."""
    root = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    queue = [(frontend, name) for name in root.get("dependencies", {})]
    visited: set[Path] = set()
    found: dict[tuple[str, str], Entry] = {}
    while queue:
        parent, dep = queue.pop()
        folder = _resolve(frontend, parent, dep)
        if folder is None or folder in visited:
            continue
        visited.add(folder)
        pkg = json.loads((folder / "package.json").read_text(encoding="utf-8"))
        queue.extend((folder, name) for name in pkg.get("dependencies", {}))
        key = folder.relative_to(frontend).as_posix()
        name, version = pkg.get("name", key.rsplit("node_modules/", 1)[-1]), pkg.get("version", "")
        texts = [
            p.read_text(encoding="utf-8", errors="replace").strip()
            for p in sorted(folder.iterdir())
            if p.is_file() and LICENSE_FILE.match(p.name)
        ]
        lic = pkg.get("license")
        if isinstance(lic, dict):
            lic = lic.get("type")
        repo = pkg.get("repository")
        home = pkg.get("homepage") or (repo.get("url") if isinstance(repo, dict) else repo) or ""
        text = "\n\n".join(texts) or (
            f"Licencia: {lic or 'neuvedená'}. Balík text licencie neobsahuje; {home}".rstrip("; ")
        )
        found[(name, version)] = Entry(name, version, lic or "neuvedená", text)
    return sorted(found.values(), key=lambda e: e.name.lower())


def _block(entry: Entry) -> str:
    return f"{RULE}\n{entry.name} {entry.version} ({entry.license})\n{RULE}\n\n{entry.text}\n"


def render(root: Path) -> str:
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    python = Entry(
        "Python",
        sys.version.split()[0],
        "PSF-2.0",
        python_license.read_text(encoding="utf-8", errors="replace").strip(),
    )
    parts = [
        "Moje kocky Desktop – licencie softvéru tretích strán\n"
        "Moje kocky Desktop – third-party software notices\n\n"
        "Program obsahuje nasledujúci softvér. Každý patrí svojim autorom a šíri sa\n"
        "podľa svojej licencie, ktorej text je uvedený nižšie.\n\n"
        "Inštalátor je zostavený programom Inno Setup (Jordan Russell, Martijn Laan,\n"
        "https://jrsoftware.org/isinfo.php). Microsoft Edge WebView2 nie je súčasťou\n"
        "programu, je súčasťou Windows.\n",
        _block(
            Entry(
                "Moje kocky Desktop",
                "",
                "MIT",
                (root / "LICENSE").read_text(encoding="utf-8").strip(),
            )
        ),
        _block(python),
        *(_block(e) for e in python_entries("lego-api")),
        _block(pyinstaller_entry()),
        *(_block(e) for e in npm_entries(root / "frontend")),
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(Path(__file__).resolve().parents[1]), encoding="utf-8")
    print(f"{out} ({out.stat().st_size // 1024} kB)")
