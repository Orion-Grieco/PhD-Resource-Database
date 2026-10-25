# PyInstaller spec for the desktop app. Built by build.ps1; run from the project root:
#   pyinstaller desktop/PhDProgramFinder.spec --distpath dist --workpath build
# Requires the frontend to be exported first (build.ps1 does this).
import json
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).parent
INFO = json.loads((ROOT / "desktop" / "app_info.json").read_text(encoding="utf-8"))

for required in (ROOT / ".web" / "build" / "client" / "index.html", ROOT / ".web" / "backend"):
    if not required.exists():
        raise SystemExit(f"Missing {required}; export the frontend first (see build.ps1).")

reflex_datas, reflex_binaries, reflex_hidden = collect_all("reflex")

datas = [
    (str(ROOT / "desktop" / "app_info.json"), "desktop"),
    (str(ROOT / ".web" / "build" / "client"), ".web/build/client"),
    (str(ROOT / ".web" / "backend"), ".web/backend"),
    (str(ROOT / "rxconfig.py"), "."),
    (str(ROOT / "app"), "app"),
    (str(ROOT / "assets"), "assets"),
    *reflex_datas,
]

hiddenimports = [
    "rxconfig",
    *collect_submodules("app"),
    *collect_submodules("uvicorn"),
    "aiosqlite",
    "sqlalchemy.dialects.sqlite",
    *reflex_hidden,
]

# Installed for other tools in requirements.txt but never imported by the app.
# (redis stays: Reflex imports it unconditionally.)
excludes = [
    "pandas", "numpy", "plotly", "boto3", "botocore", "s3transfer", "databricks",
    "openai", "psycopg", "psycopg2", "pgvector", "tkinter", "matplotlib", "IPython",
]

a = Analysis(
    [str(ROOT / "desktop" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=reflex_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)
icon = ROOT / "desktop" / "icon.ico"
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=INFO["exe_name"],
    console=False,
    icon=str(icon) if icon.exists() else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name=INFO["exe_name"])
