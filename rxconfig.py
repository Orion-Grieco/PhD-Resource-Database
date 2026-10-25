import os
from pathlib import Path

import reflex as rx

# Local data folder (database + saved pages); see app/storage.py. Set DATA_DIR to move it.
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent / "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Dev mode hot-reloads on file changes in the project. Writes to the data folder
# (database journal, saved pages) must not restart the backend, so exclude it.
# Reflex splits this variable on ":", so use a path relative to the project root.
if DATA_DIR.is_relative_to(Path.cwd()):
    _exclude = DATA_DIR.relative_to(Path.cwd()).as_posix()
    _existing = os.environ.get("REFLEX_HOT_RELOAD_EXCLUDE_PATHS")
    os.environ["REFLEX_HOT_RELOAD_EXCLUDE_PATHS"] = f"{_existing}:{_exclude}" if _existing else _exclude

# Local SQLite by default; set REFLEX_DB_URL (e.g. a Postgres URL) to override.
config = rx.Config(
    app_name="app",
    db_url=f"sqlite:///{DATA_DIR.as_posix()}/programs.db",
    plugins=[rx.plugins.TailwindV3Plugin()],
)
