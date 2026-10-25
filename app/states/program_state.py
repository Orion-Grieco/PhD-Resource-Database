import reflex as rx
from typing import TypedDict
import logging
import sqlmodel

from app import storage
from app.models import Program as ProgramModel, ProgramChange, STATUSES
from app.scraper.extract import FIELDS, normalize
from app.scraper.recheck import recheck_programs


class Program(TypedDict):
    id: int
    university_name: str
    program_name: str
    department: str
    degree_type: str
    research_area: str
    application_deadline: str
    tuition_in_state: str
    tuition_out_of_state: str
    url: str
    description: str
    status: str
    notes: str
    last_checked: str


class PendingChange(TypedDict):
    id: int
    program_id: int
    program_label: str
    field_label: str
    old_value: str
    new_value: str


FIELD_LABELS = {
    "application_deadline": "Deadline",
    "tuition_in_state": "Tuition (in-state)",
    "tuition_out_of_state": "Tuition (out-of-state)",
    "degree_type": "Degree",
    "program_name": "Program name",
}


def _money(value: int | None) -> str:
    return f"${value:,}" if value is not None else "—"


def _to_row(p: ProgramModel) -> Program:
    return {
        "id": p.id,
        "university_name": p.university_name,
        "program_name": p.program_name,
        "department": p.department,
        "degree_type": p.degree_type,
        "research_area": p.research_area,
        "application_deadline": p.application_deadline.isoformat() if p.application_deadline else "—",
        "tuition_in_state": _money(p.tuition_in_state),
        "tuition_out_of_state": _money(p.tuition_out_of_state),
        "url": p.url,
        "description": p.description,
        "status": p.status,
        "notes": p.notes,
        "last_checked": p.last_checked.strftime("%Y-%m-%d %H:%M") if p.last_checked else "never",
    }


def _display(field: str, value: str) -> str:
    if field.startswith("tuition") and value:
        return _money(int(value))
    return value or "—"


class ProgramState(rx.State):
    programs: list[Program] = []
    pending_changes: list[PendingChange] = []
    loading: bool = False
    search_query: str = ""
    selected_degree: str = ""
    selected_research_area: str = ""
    rechecking: bool = False
    recheck_message: str = ""

    @rx.var
    def statuses(self) -> list[str]:
        return STATUSES

    def _load(self):
        with rx.session() as session:
            rows = session.exec(
                sqlmodel.select(ProgramModel).order_by(ProgramModel.university_name)
            ).all()
            self.programs = [_to_row(p) for p in rows]
            labels = {p.id: f"{p.university_name} — {p.program_name}" for p in rows}
            changes = session.exec(
                sqlmodel.select(ProgramChange)
                .where(ProgramChange.resolved == False)  # noqa: E712
                .order_by(ProgramChange.detected_at)
            ).all()
            self.pending_changes = [
                {
                    "id": c.id,
                    "program_id": c.program_id,
                    "program_label": labels.get(c.program_id, f"Program {c.program_id}"),
                    "field_label": FIELD_LABELS.get(c.field, c.field),
                    "old_value": _display(c.field, c.old_value),
                    "new_value": _display(c.field, c.new_value),
                }
                for c in changes
            ]

    @rx.event
    def get_all_programs(self):
        try:
            self._load()
        except Exception as e:
            logging.exception(f"Database query failed: {e}")

    @rx.event
    def set_search_query(self, value: str):
        self.search_query = value

    @rx.event
    def set_selected_degree(self, value: str):
        self.selected_degree = value

    @rx.event
    def set_selected_research_area(self, value: str):
        self.selected_research_area = value

    @rx.event
    def set_status(self, program_id: int, status: str):
        with rx.session() as session:
            program = session.get(ProgramModel, program_id)
            if program:
                program.status = status
                session.add(program)
                session.commit()
        self._load()

    @rx.event
    def delete_program(self, program_id: int):
        with rx.session() as session:
            for change in session.exec(
                sqlmodel.select(ProgramChange).where(ProgramChange.program_id == program_id)
            ).all():
                session.delete(change)
            program = session.get(ProgramModel, program_id)
            if program:
                session.delete(program)
            session.commit()
        self._load()

    @rx.event
    def resolve_change(self, change_id: int, accept: bool):
        with rx.session() as session:
            change = session.get(ProgramChange, change_id)
            if change is None:
                return
            program = session.get(ProgramModel, change.program_id)
            if accept and program:
                value = normalize({change.field: change.new_value})[change.field]
                setattr(program, change.field, value)
                session.add(program)
            change.resolved = True
            session.add(change)
            session.commit()
            if program:
                # Accepting or dismissing confirms the program's values for the page as last fetched.
                storage.save_labels(
                    program.page_hash,
                    {**{name: getattr(program, name) for name in FIELDS}, "url": program.url},
                )
        self._load()

    @rx.event(background=True)
    async def recheck_now(self):
        async with self:
            if self.rechecking:
                return
            self.rechecking = True
            self.recheck_message = ""
        try:
            summary = await recheck_programs(only_due=False)
            msg = f"Checked {summary['checked']} program(s), {summary['changes']} new update(s)."
            if summary["errors"]:
                msg += f" {len(summary['errors'])} failed: " + "; ".join(summary["errors"][:3])
        except Exception as e:
            logging.exception("Re-check failed")
            msg = f"Re-check failed: {e}"
        async with self:
            self.rechecking = False
            self.recheck_message = msg
            self._load()

    @rx.var
    def filtered_programs(self) -> list[Program]:
        query = self.search_query.lower()
        filtered = self.programs
        if query:
            filtered = [
                p
                for p in filtered
                if query in p["university_name"].lower()
                or query in p["program_name"].lower()
                or query in p["department"].lower()
                or (query in p["research_area"].lower())
            ]
        if self.selected_degree:
            filtered = [p for p in filtered if p["degree_type"] == self.selected_degree]
        if self.selected_research_area:
            filtered = [
                p for p in filtered if p["research_area"] == self.selected_research_area
            ]
        return filtered

    @rx.var
    def unique_degrees(self) -> list[str]:
        if not self.programs:
            return []
        return sorted(
            list(set((p["degree_type"] for p in self.programs if p["degree_type"])))
        )

    @rx.var
    def unique_research_areas(self) -> list[str]:
        if not self.programs:
            return []
        return sorted(
            list(set((p["research_area"] for p in self.programs if p["research_area"])))
        )

    @rx.event
    def clear_filters(self):
        self.search_query = ""
        self.selected_degree = ""
        self.selected_research_area = ""
