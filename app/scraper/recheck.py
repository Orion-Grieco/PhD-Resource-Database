"""Re-fetch saved programs and record what changed as pending updates.

Runs on a schedule inside the app (see `recheck_loop`), from the dashboard's
"Re-check now" button, or from the command line:

    python -m app.scraper.recheck          # programs not checked in RECHECK_INTERVAL_HOURS
    python -m app.scraper.recheck --all    # every saved program
"""

import asyncio
import datetime
import logging
import os

import reflex as rx
import sqlmodel

from app.models import Program, ProgramChange, _now
from app.scraper.extract import extract_program
from app.scraper.fetch import FetchError, fetch_page

# Fields compared on re-check. Values the extractor couldn't find are ignored,
# so a page that fails to parse doesn't wipe out data.
TRACKED_FIELDS = (
    "application_deadline",
    "tuition_in_state",
    "tuition_out_of_state",
    "degree_type",
    "program_name",
)
DELAY_BETWEEN_REQUESTS = 2.0  # seconds; be polite to university servers


def interval_hours() -> float:
    return float(os.getenv("RECHECK_INTERVAL_HOURS", "24"))


def _as_text(value) -> str:
    return "" if value is None else str(value)


async def recheck_program(program_id: int) -> int:
    """Re-check one program. Returns the number of new pending changes."""
    with rx.session() as session:
        program = session.get(Program, program_id)
        if program is None or not program.url:
            return 0
        url, old_hash = program.url, program.page_hash

    page = await fetch_page(url)
    new_hash = page.content_hash
    fields = None if new_hash == old_hash else await extract_program(page)

    with rx.session() as session:
        program = session.get(Program, program_id)
        if program is None:
            return 0
        program.last_checked = _now()
        program.page_hash = new_hash
        new_changes = 0
        if fields:
            pending = session.exec(
                sqlmodel.select(ProgramChange).where(
                    ProgramChange.program_id == program_id,
                    ProgramChange.resolved == False,  # noqa: E712
                )
            ).all()
            for name in TRACKED_FIELDS:
                new, old = _as_text(fields.get(name)), _as_text(getattr(program, name))
                if not new or new == old:
                    continue
                if any(c.field == name and c.new_value == new for c in pending):
                    continue
                for c in pending:  # supersede an older suggestion for the same field
                    if c.field == name:
                        c.resolved = True
                        session.add(c)
                session.add(ProgramChange(program_id=program_id, field=name, old_value=old, new_value=new))
                new_changes += 1
        session.add(program)
        session.commit()
    return new_changes


async def recheck_programs(only_due: bool = True) -> dict:
    """Re-check saved programs one at a time. Returns a summary."""
    cutoff = _now() - datetime.timedelta(hours=interval_hours())
    with rx.session() as session:
        query = sqlmodel.select(Program.id).where(Program.url != "")
        if only_due:
            query = query.where(
                (Program.last_checked == None) | (Program.last_checked < cutoff)  # noqa: E711
            )
        ids = list(session.exec(query).all())

    summary = {"checked": 0, "changes": 0, "errors": []}
    for i, program_id in enumerate(ids):
        if i:
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
        try:
            summary["changes"] += await recheck_program(program_id)
            summary["checked"] += 1
        except FetchError as e:
            summary["errors"].append(f"Program {program_id}: {e}")
        except Exception as e:
            logging.exception("Re-check failed for program %s", program_id)
            summary["errors"].append(f"Program {program_id}: {e}")
    return summary


async def recheck_loop():
    """Lifespan task: periodically re-check programs that are due."""
    rx.Model.create_all()
    if interval_hours() <= 0:
        return
    # Let the app finish starting (and avoid hammering sites on every dev reload).
    await asyncio.sleep(60)
    while True:
        try:
            summary = await recheck_programs(only_due=True)
            if summary["checked"]:
                logging.info("Scheduled re-check: %s", summary)
        except Exception:
            logging.exception("Scheduled re-check failed")
        await asyncio.sleep(3600)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    rx.Model.create_all()
    print(asyncio.run(recheck_programs(only_due="--all" not in sys.argv)))
