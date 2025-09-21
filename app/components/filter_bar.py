import reflex as rx
from app.states.program_state import ProgramState


def filter_bar() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(
                    "search",
                    class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400",
                ),
                rx.el.input(
                    placeholder="Search programs, universities...",
                    on_change=ProgramState.set_search_query,
                    class_name="w-full h-[40px] pl-10 pr-4 bg-white border border-gray-300 rounded-none focus:outline-none focus:ring-2 focus:ring-blue-500",
                    default_value=ProgramState.search_query,
                ),
                class_name="relative w-full lg:w-1/3",
            ),
            rx.el.div(
                rx.el.select(
                    rx.el.option("All Degrees", value=""),
                    rx.foreach(
                        ProgramState.unique_degrees,
                        lambda degree: rx.el.option(degree, value=degree),
                    ),
                    value=ProgramState.selected_degree,
                    on_change=ProgramState.set_selected_degree,
                    class_name="w-full h-[40px] bg-white border border-gray-300 rounded-none focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none px-4",
                ),
                rx.el.select(
                    rx.el.option("All Research Areas", value=""),
                    rx.foreach(
                        ProgramState.unique_research_areas,
                        lambda area: rx.el.option(area, value=area),
                    ),
                    value=ProgramState.selected_research_area,
                    on_change=ProgramState.set_selected_research_area,
                    class_name="w-full h-[40px] bg-white border border-gray-300 rounded-none focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none px-4",
                ),
                rx.el.button(
                    "Clear",
                    on_click=ProgramState.clear_filters,
                    class_name="h-[40px] px-6 bg-gray-200 text-gray-700 font-medium hover:bg-gray-300 rounded-none transition-colors",
                ),
                class_name="grid grid-cols-1 md:grid-cols-3 gap-4 w-full lg:w-2/3",
            ),
            class_name="flex flex-col lg:flex-row gap-4 w-full",
        ),
        class_name="p-4 md:p-6 bg-gray-50 border-b border-gray-200",
    )