import reflex as rx
import logging
import sqlmodel

from app.models import Program, STATUSES
from app.scraper.extract import FIELDS, extract_program, normalize
from app.scraper.fetch import FetchError, fetch_page

FORM_FIELDS = FIELDS + ("url", "status", "notes")


def _empty_form() -> dict[str, str]:
    form = {name: "" for name in FORM_FIELDS}
    form["status"] = STATUSES[0]
    return form


class AddProgramState(rx.State):
    link: str = ""
    form: dict[str, str] = _empty_form()
    page_hash: str = ""
    parsing: bool = False
    parsed: bool = False
    error: str = ""
    saved_message: str = ""
    editing_id: int = 0

    @rx.event
    def load_page(self):
        """On load: `/add?edit=<id>` opens that program for editing; plain `/add` starts fresh."""
        self.error = ""
        self.saved_message = ""
        edit = self.router.url.query_parameters.get("edit", "")
        if not edit:
            if self.editing_id:
                self._reset_form()
            return
        with rx.session() as session:
            program = session.get(Program, int(edit)) if edit.isdigit() else None
            if program is None:
                self._reset_form()
                self.error = "That program no longer exists."
                return
            form = _empty_form()
            for name in FORM_FIELDS:
                value = getattr(program, name)
                if value is not None:
                    form[name] = value.isoformat() if hasattr(value, "isoformat") else str(value)
            self.form = form
            self.page_hash = program.page_hash
        self.editing_id = int(edit)
        self.link = ""
        self.parsed = True

    def _reset_form(self):
        self.form = _empty_form()
        self.page_hash = ""
        self.parsed = False
        self.error = ""
        self.editing_id = 0

    @rx.event
    def set_link(self, value: str):
        self.link = value

    @rx.event
    def set_form_field(self, name: str, value: str):
        self.form[name] = value

    @rx.event
    def start_manual(self):
        self._reset_form()
        self.form = _empty_form()
        self.form["url"] = self.link.strip()
        self.page_hash = ""
        self.parsed = True
        self.error = ""
        self.saved_message = ""

    @rx.event(background=True)
    async def parse_link(self):
        async with self:
            if self.parsing or not self.link.strip():
                return
            self.parsing = True
            self.error = ""
            self.saved_message = ""
            link = self.link.strip()
        try:
            page = await fetch_page(link)
            fields = await extract_program(page)
            form = _empty_form()
            for name, value in fields.items():
                form[name] = "" if value is None else str(value)
            form["url"] = page.final_url
            async with self:
                self.form = form
                self.page_hash = page.content_hash
                self.parsed = True
        except FetchError as e:
            async with self:
                self.error = str(e)
        except Exception as e:
            logging.exception("Parsing %s failed", link)
            async with self:
                self.error = f"Something went wrong while parsing that page: {e}"
        finally:
            async with self:
                self.parsing = False

    @rx.event
    def save(self):
        form = self.form
        if not (form["university_name"].strip() or form["program_name"].strip()):
            self.error = "Enter at least a university or program name."
            return
        values = normalize(form)
        if form["application_deadline"].strip() and values["application_deadline"] is None:
            self.error = "Couldn't read the deadline. Use a date like 2026-12-01."
            return
        for key in ("tuition_in_state", "tuition_out_of_state"):
            if form[key].strip() and values[key] is None:
                self.error = "Couldn't read a tuition amount. Use a number like 45000."
                return
        url = form["url"].strip()
        with rx.session() as session:
            existing = session.exec(sqlmodel.select(Program).where(Program.url == url)).first() if url else None
            if existing and existing.id != self.editing_id:
                self.error = "That link is already in your dashboard."
                return
            if self.editing_id:
                program = session.get(Program, self.editing_id)
                if program is None:
                    self.error = "That program no longer exists."
                    return
                if url != program.url:
                    program.page_hash = ""  # new page: re-extract on the next re-check
                for name, value in values.items():
                    setattr(program, name, value)
                program.url = url
                program.status = form["status"] or STATUSES[0]
                program.notes = form["notes"].strip()
                session.add(program)
                session.commit()
                self._reset_form()
                return rx.redirect("/")
            session.add(
                Program(
                    **values,
                    url=url,
                    status=form["status"] or STATUSES[0],
                    notes=form["notes"].strip(),
                    page_hash=self.page_hash,
                )
            )
            session.commit()
        label = values["program_name"] or values["university_name"]
        self.link = ""
        self._reset_form()
        self.saved_message = f"Saved “{label}” to your dashboard."

    @rx.event
    def cancel(self):
        was_editing = bool(self.editing_id)
        self._reset_form()
        if was_editing:
            return rx.redirect("/")
