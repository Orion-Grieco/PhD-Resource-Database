import reflex as rx
from app.components.header import header_component
from app.states.add_program_state import AddProgramState
from app.states.program_state import ProgramState

INPUT_CLASS = "w-full h-[40px] px-3 bg-white border border-gray-300 rounded-none focus:outline-none focus:ring-2 focus:ring-blue-500"


def field(label: str, name: str, placeholder: str = "", wide: bool = False) -> rx.Component:
    return rx.el.label(
        rx.el.span(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.el.input(
            value=AddProgramState.form[name],
            on_change=lambda v: AddProgramState.set_form_field(name, v),
            placeholder=placeholder,
            name=name,
            class_name=INPUT_CLASS,
        ),
        class_name="md:col-span-2" if wide else "",
    )


def review_form() -> rx.Component:
    return rx.el.form(
        rx.el.h2(
            rx.cond(AddProgramState.editing_id != 0, "Program details", "Check the details"),
            class_name="text-lg font-semibold text-gray-800",
        ),
        rx.el.p(
            rx.cond(
                AddProgramState.editing_id != 0,
                "Changes are saved to your dashboard. Re-checks will compare the page against these values.",
                rx.cond(
                    AddProgramState.page_hash != "",
                "Fields were filled in automatically and may be wrong or missing. Fix anything before saving.",
                    "Enter what you know; only a university or program name is required.",
                ),
            ),
            class_name="text-sm text-gray-500 mt-1",
        ),
        rx.el.div(
            field("University", "university_name"),
            field("Program", "program_name"),
            field("Department", "department"),
            field("Degree", "degree_type", "PhD, MS, MA…"),
            field("Research area", "research_area"),
            field("Application deadline", "application_deadline", "2026-12-01"),
            field("Tuition (in-state)", "tuition_in_state", "45000"),
            field("Tuition (out-of-state)", "tuition_out_of_state", "60000"),
            field("Link", "url", "https://…", wide=True),
            field("Description", "description", wide=True),
            rx.el.label(
                rx.el.span("Status", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.select(
                    rx.foreach(ProgramState.statuses, lambda s: rx.el.option(s, value=s)),
                    value=AddProgramState.form["status"],
                    on_change=lambda v: AddProgramState.set_form_field("status", v),
                    class_name=INPUT_CLASS,
                ),
            ),
            rx.el.label(
                rx.el.span("Notes", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.textarea(
                    value=AddProgramState.form["notes"],
                    on_change=lambda v: AddProgramState.set_form_field("notes", v),
                    rows=3,
                    class_name="w-full px-3 py-2 bg-white border border-gray-300 rounded-none focus:outline-none focus:ring-2 focus:ring-blue-500",
                ),
                class_name="md:col-span-2",
            ),
            class_name="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6",
        ),
        rx.el.div(
            rx.el.button(
                rx.cond(AddProgramState.editing_id != 0, "Save changes", "Save to dashboard"),
                type="submit",
                class_name="h-[40px] px-6 bg-blue-600 text-white font-medium hover:bg-blue-700",
            ),
            rx.el.button(
                "Cancel",
                type="button",
                on_click=AddProgramState.cancel,
                class_name="h-[40px] px-6 bg-gray-200 text-gray-700 font-medium hover:bg-gray-300",
            ),
            class_name="flex gap-2 mt-6",
        ),
        on_submit=lambda _: AddProgramState.save,
        reset_on_submit=False,
        class_name="mt-6 p-6 bg-white border border-gray-200",
    )


def link_section() -> rx.Component:
    return rx.el.div(
        rx.el.h1("Add a program from a link", class_name="text-2xl font-semibold text-gray-900"),
        rx.el.p(
            "Paste the URL of a program's page. It will be fetched and parsed so you can review the details.",
            class_name="text-sm text-gray-500 mt-1",
        ),
        rx.el.form(
            rx.el.input(
                value=AddProgramState.link,
                on_change=AddProgramState.set_link,
                placeholder="https://university.edu/graduate/program",
                type="url",
                name="link",
                aria_label="Program page URL",
                class_name=INPUT_CLASS + " flex-1 min-w-0",
            ),
            rx.el.button(
                rx.cond(AddProgramState.parsing, "Parsing…", "Parse link"),
                type="submit",
                disabled=AddProgramState.parsing,
                class_name="h-[40px] px-6 bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-60",
            ),
            on_submit=lambda _: AddProgramState.parse_link,
            reset_on_submit=False,
            class_name="flex flex-wrap gap-2 mt-4",
        ),
        rx.el.button(
            "or enter details manually",
            on_click=AddProgramState.start_manual,
            class_name="mt-2 text-sm text-blue-600 hover:text-blue-800",
        ),
    )


def add_program() -> rx.Component:
    return rx.el.div(
        header_component(),
        rx.el.main(
            rx.el.div(
                rx.cond(
                    AddProgramState.editing_id != 0,
                    rx.el.div(
                        rx.el.a("← Back to dashboard", href="/", class_name="text-sm text-blue-600 hover:text-blue-800"),
                        rx.el.h1("Edit program", class_name="mt-2 text-2xl font-semibold text-gray-900"),
                    ),
                    link_section(),
                ),
                rx.cond(
                    AddProgramState.error != "",
                    rx.el.p(
                        AddProgramState.error,
                        role="alert",
                        class_name="mt-4 p-3 text-sm text-red-800 bg-red-50 border border-red-200",
                    ),
                ),
                rx.cond(
                    AddProgramState.saved_message != "",
                    rx.el.p(
                        AddProgramState.saved_message,
                        " ",
                        rx.el.a("View dashboard", href="/", class_name="underline"),
                        role="status",
                        class_name="mt-4 p-3 text-sm text-green-800 bg-green-50 border border-green-200",
                    ),
                ),
                rx.cond(AddProgramState.parsed, review_form()),
                class_name="max-w-3xl mx-auto p-4 md:p-6",
            ),
            class_name="flex-1",
        ),
        class_name="font-['IBM_Plex_Sans'] bg-gray-50 min-h-screen flex flex-col",
    )
