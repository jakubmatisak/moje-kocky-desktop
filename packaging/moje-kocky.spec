# PyInstaller: Moje kocky Desktop ako priečinok s MojeKocky.exe (onedir).
# Zostavenie: scripts\build.ps1 (najprv frontend: npm run build-desktop).
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent
BACKEND = ROOT / "backend"

datas = [
    (str(ROOT / "frontend" / "dist-desktop"), "web"),
    (str(BACKEND / "alembic"), "backend/alembic"),
    (str(BACKEND / "alembic.ini"), "backend"),
    (str(ROOT / "packaging" / "icon.ico"), "."),
]
datas += collect_data_files("webview")

hiddenimports = (
    collect_submodules("lego_api")
    + collect_submodules("lego_desktop")
    + collect_submodules("aiosqlite")
    + collect_submodules("alembic")
    + collect_submodules("sqlalchemy.dialects.sqlite")
    # Migrácie (alembic/env.py a versions/*.py) sa načítavajú zo súborov,
    # PyInstaller ich importy nevidí.
    + ["logging.config", "email_validator", "clr"]
)

a = Analysis(
    [str(ROOT / "packaging" / "run.py")],
    pathex=[str(BACKEND / "src")],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "respx", "mypy", "ruff"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MojeKocky",
    icon=str(ROOT / "packaging" / "icon.ico"),
    console=False,
    version=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="MojeKocky")
