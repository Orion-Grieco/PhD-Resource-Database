import reflex as rx
import datetime
from typing import Optional
from sqlmodel import Field


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


STATUSES = ["Interested", "Researching", "Applying", "Applied", "Accepted", "Rejected", "Not a fit"]


class Program(rx.Model, table=True):
    university_name: str = ""
    program_name: str = ""
    department: str = ""
    degree_type: str = ""
    research_area: str = ""
    application_deadline: Optional[datetime.date] = None
    tuition_in_state: Optional[int] = None
    tuition_out_of_state: Optional[int] = None
    url: str = Field(default="", index=True)
    description: str = ""
    # Personal tracking
    status: str = "Interested"
    notes: str = ""
    added_at: datetime.datetime = Field(default_factory=_now)
    # Scraper bookkeeping
    last_checked: Optional[datetime.datetime] = None
    page_hash: str = ""


class ProgramChange(rx.Model, table=True):
    """A difference found by the re-check scraper, waiting for the user to accept or dismiss."""

    program_id: int = Field(foreign_key="program.id", index=True)
    field: str
    old_value: str = ""
    new_value: str = ""
    detected_at: datetime.datetime = Field(default_factory=_now)
    resolved: bool = False
