import os
from pathlib import Path

import reflex as rx

# Local data folder (database + saved pages); see app/storage.py. Set DATA_DIR to move it.
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent / "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Dev mode hot-reloads on file changes in the project. Writes to the data folder
# (database journal, saved pages) and desktop build output must not restart the
# backend, so exclude them. Reflex splits this variable on ":", so use paths
# relative to the project root, and only existing ones (Reflex stats each).
_excludes = [
    p.relative_to(Path.cwd()).as_posix()
    for p in (DATA_DIR, Path.cwd() / "build", Path.cwd() / "dist")
    if p.exists() and p.is_relative_to(Path.cwd()) and p != Path.cwd()
]
_existing = os.environ.get("REFLEX_HOT_RELOAD_EXCLUDE_PATHS")
for _exclude in _excludes:
    if _existing is None or _exclude not in _existing.split(":"):
        _existing = f"{_existing}:{_exclude}" if _existing else _exclude
if _existing:
    os.environ["REFLEX_HOT_RELOAD_EXCLUDE_PATHS"] = _existing

# Local SQLite by default; set REFLEX_DB_URL (e.g. a Postgres URL) to override.
config = rx.Config(
    app_name="app",
    db_url=f"sqlite:///{DATA_DIR.as_posix()}/programs.db",
    plugins=[rx.plugins.TailwindV3Plugin()],
)
