"""Local data folder: the SQLite database plus a copy of every fetched page.

Layout (DATA_DIR defaults to ./data in the project; set DATA_DIR to move it):

    data/
      programs.db
      pages/<content hash>/
        page.html        raw HTML as fetched
        page.txt         cleaned text the extractor saw
        meta.json        url, final url, title, every time this exact content was fetched
        extracted.json   what the extractor returned (and which extractor)
        saved.json       the values you saved after review or editing

Pages are stored by content hash, so an unchanged page is stored once. A page
with both extracted.json and saved.json is an (input, corrected output) pair.
"""

import datetime
import json
import logging
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data")).resolve()
PAGES_DIR = DATA_DIR / "pages"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def page_dir(content_hash: str) -> Path:
    return PAGES_DIR / content_hash[:16]


def save_page(page, fields: dict, extractor: str) -> None:
    """Store a fetched page and the extractor's output. Never raises."""
    try:
        folder = page_dir(page.content_hash)
        folder.mkdir(parents=True, exist_ok=True)
        meta_path = folder / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {
            "url": page.url,
            "final_url": page.final_url,
            "title": page.title,
            "content_hash": page.content_hash,
            "fetched_at": [],
        }
        meta["fetched_at"].append(_now())
        if not (folder / "page.html").exists():
            (folder / "page.html").write_text(page.html, encoding="utf-8")
            (folder / "page.txt").write_text(page.text, encoding="utf-8")
        _write_json(meta_path, meta)
        _write_json(folder / "extracted.json", {"extractor": extractor, "extracted_at": _now(), "fields": fields})
    except OSError:
        logging.exception("Could not save page snapshot")


def save_labels(content_hash: str, values: dict) -> None:
    """Record the values the user saved for a stored page. Never raises."""
    if not content_hash:
        return
    try:
        folder = page_dir(content_hash)
        if folder.is_dir():
            _write_json(folder / "saved.json", {"saved_at": _now(), "fields": values})
    except OSError:
        logging.exception("Could not save labels")
