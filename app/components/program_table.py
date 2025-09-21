import reflex as rx
from app.states.program_state import ProgramState, Program


def table_header() -> rx.Component:
    headers = [
        "University",
        "Program",
        "Department",
        "Research Area",
        "Degree",
        "Deadline",
        "Tuition (Out-of-State)",
        "",
    ]
    return rx.el.thead(
        rx.el.tr(
            rx.foreach(
                headers,
                lambda header: rx.el.th(
                    header,
                    scope="col",
                    class_name="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider",
                ),
            ),
            class_name="bg-gray-50",
        )
    )


def table_row(program: Program) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            program["university_name"],
            class_name="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900",
        ),
        rx.el.td(
            program["program_name"],
            class_name="px-6 py-4 whitespace-nowrap text-sm text-gray-700",
        ),
        rx.el.td(
            program["department"],
            class_name="px-6 py-4 whitespace-nowrap text-sm text-gray-500",
        ),
        rx.el.td(
            program["research_area"],
            class_name="px-6 py-4 whitespace-nowrap text-sm text-gray-500",
        ),
        rx.el.td(
            rx.el.span(
                program["degree_type"],
                class_name="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800",
            ),
            class_name="px-6 py-4 whitespace-nowrap text-sm text-gray-500",
        ),
        rx.el.td(
            program["application_deadline"],
            class_name="px-6 py-4 whitespace-nowrap text-sm text-gray-500",
        ),
        rx.el.td(
            f"${program['tuition_out_of_state']}",
            class_name="px-6 py-4 whitespace-nowrap text-sm text-gray-500",
        ),
        rx.el.td(
            rx.el.a(
                "View",
                href=program["url"],
                is_external=True,
                class_name="text-blue-600 hover:text-blue-800 font-medium",
            ),
            class_name="px-6 py-4 whitespace-nowrap text-right text-sm font-medium",
        ),
        class_name="hover:bg-gray-50 transition-colors",
    )


def skeleton_row() -> rx.Component:
    return rx.el.tr(
        rx.foreach(
            list(range(8)),
            lambda i: rx.el.td(
                rx.el.div(class_name="h-4 bg-gray-200 rounded w-full"),
                class_name="px-6 py-4",
            ),
        )
    )


def program_table() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.table(
                table_header(),
                rx.el.tbody(
                    rx.cond(
                        ProgramState.loading,
                        rx.foreach(list(range(10)), lambda i: skeleton_row()),
                        rx.foreach(ProgramState.filtered_programs, table_row),
                    ),
                    class_name="bg-white divide-y divide-gray-200",
                ),
                class_name="min-w-full divide-y divide-gray-200",
            ),
            class_name="align-middle inline-block min-w-full",
        ),
        rx.cond(
            ~ProgramState.loading & (ProgramState.filtered_programs.length() == 0),
            rx.el.div(
                rx.icon("search_x", class_name="mx-auto text-gray-400", size=48),
                rx.el.h3(
                    "No Programs Found",
                    class_name="mt-4 text-lg font-medium text-gray-800",
                ),
                rx.el.p(
                    "Try adjusting your search or filter criteria.",
                    class_name="mt-1 text-sm text-gray-500",
                ),
                class_name="text-center p-16",
            ),
        ),
        class_name="shadow border-b border-gray-200 overflow-x-auto",
    )