import reflex as rx


def header_component() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            rx.el.div(
                rx.icon(tag="database", class_name="text-blue-500", size=32),
                rx.el.h1(
                    "PhD Program Finder",
                    class_name="text-xl md:text-2xl font-semibold text-gray-800",
                ),
                class_name="flex items-center gap-4",
            ),
            class_name="flex items-center justify-between w-full",
        ),
        class_name="bg-white p-4 border-b border-gray-200 sticky top-0 z-10",
    )