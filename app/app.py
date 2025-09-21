import reflex as rx
from app.components.header import header_component
from app.components.filter_bar import filter_bar
from app.components.program_table import program_table
from app.states.program_state import ProgramState


def index() -> rx.Component:
    return rx.el.div(
        header_component(),
        rx.el.main(
            filter_bar(),
            rx.el.div(program_table(), class_name="p-4 md:p-6"),
            class_name="flex-1",
        ),
        class_name="font-['IBM_Plex_Sans'] bg-white min-h-screen flex flex-col",
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(index, on_load=ProgramState.get_all_programs)