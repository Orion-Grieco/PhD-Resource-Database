import reflex as rx
from app.states.program_state import ProgramState, PendingChange


def change_row(change: PendingChange) -> rx.Component:
    return rx.el.li(
        rx.el.div(
            rx.el.p(change["program_label"], class_name="text-sm font-medium text-gray-900"),
            rx.el.p(
                change["field_label"] + ": ",
                rx.el.span(change["old_value"], class_name="line-through text-gray-400"),
                " → ",
                rx.el.span(change["new_value"], class_name="font-medium text-gray-900"),
                class_name="text-sm text-gray-600",
            ),
            class_name="min-w-0",
        ),
        rx.el.div(
            rx.el.button(
                "Accept",
                on_click=ProgramState.resolve_change(change["id"], True),
                class_name="h-[32px] px-4 bg-blue-600 text-white text-sm font-medium hover:bg-blue-700",
            ),
            rx.el.button(
                "Dismiss",
                on_click=ProgramState.resolve_change(change["id"], False),
                class_name="h-[32px] px-4 bg-gray-200 text-gray-700 text-sm font-medium hover:bg-gray-300",
            ),
            class_name="flex gap-2 shrink-0",
        ),
        class_name="flex flex-wrap items-center justify-between gap-3 py-3",
    )


def toolbar() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                ProgramState.programs.length().to_string() + " saved program(s)",
                class_name="text-sm text-gray-600",
            ),
            rx.cond(
                ProgramState.recheck_message != "",
                rx.el.p(ProgramState.recheck_message, class_name="text-sm text-gray-500"),
            ),
            class_name="flex flex-col gap-1",
        ),
        rx.el.div(
            rx.el.button(
                rx.cond(ProgramState.rechecking, "Re-checking…", "Re-check now"),
                on_click=ProgramState.recheck_now,
                disabled=ProgramState.rechecking,
                title="Re-fetch every saved program's page and look for changed deadlines or tuition",
                class_name="h-[40px] px-4 bg-white border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-60",
            ),
            rx.el.a(
                "Add from link",
                href="/add",
                class_name="h-[40px] px-4 inline-flex items-center bg-blue-600 text-white text-sm font-medium hover:bg-blue-700",
            ),
            class_name="flex gap-2",
        ),
        class_name="flex flex-wrap items-center justify-between gap-3 mb-4",
    )


def pending_changes() -> rx.Component:
    return rx.cond(
        ProgramState.pending_changes.length() > 0,
        rx.el.section(
            rx.el.h2(
                "Updates found on program pages",
                class_name="text-sm font-semibold text-amber-900",
            ),
            rx.el.ul(
                rx.foreach(ProgramState.pending_changes, change_row),
                class_name="divide-y divide-amber-200",
            ),
            class_name="mb-4 p-4 bg-amber-50 border border-amber-200",
        ),
    )
