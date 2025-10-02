import reflex as rx
from app.components.header import header_component
from app.states.project_state import ProjectState, Project, ProjectIdea, Resource


def project_card(project: Project) -> rx.Component:
    return rx.el.div(
        rx.el.h3(project["title"], class_name="font-semibold text-lg text-gray-800"),
        rx.el.p(project["description"], class_name="text-sm text-gray-600 mt-2"),
        rx.el.div(
            rx.foreach(
                project["technologies"],
                lambda tech: rx.el.span(
                    tech,
                    class_name="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full",
                ),
            ),
            class_name="flex flex-wrap gap-2 mt-4",
        ),
        rx.el.a(
            "View Project",
            href=project["link"],
            is_external=True,
            class_name="mt-4 inline-block text-blue-600 hover:text-blue-800 font-medium text-sm",
        ),
        class_name="bg-white p-6 rounded-lg border border-gray-200 shadow-sm",
    )


def project_idea_card(idea: ProjectIdea) -> rx.Component:
    return rx.el.div(
        rx.el.h3(idea["title"], class_name="font-semibold text-lg text-gray-800"),
        rx.el.p(idea["description"], class_name="text-sm text-gray-600 mt-2"),
        rx.el.div(
            rx.foreach(
                idea["relevant_fields"],
                lambda field: rx.el.span(
                    field,
                    class_name="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full",
                ),
            ),
            class_name="flex flex-wrap gap-2 mt-4",
        ),
        class_name="bg-white p-6 rounded-lg border border-gray-200 shadow-sm",
    )


def resource_card(resource: Resource) -> rx.Component:
    return rx.el.a(
        rx.el.h3(resource["name"], class_name="font-semibold text-lg text-blue-700"),
        rx.el.p(resource["description"], class_name="text-sm text-gray-600 mt-1"),
        href=resource["link"],
        is_external=True,
        class_name="block bg-white p-6 rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow",
    )


def projects() -> rx.Component:
    return rx.el.div(
        header_component(),
        rx.el.main(
            rx.el.div(
                rx.el.h2(
                    "Projects", class_name="text-2xl font-semibold text-gray-900 mb-4"
                ),
                rx.el.div(
                    rx.foreach(ProjectState.projects, project_card),
                    class_name="grid md:grid-cols-2 gap-6",
                ),
                class_name="mb-12",
            ),
            rx.el.div(
                rx.el.h2(
                    "Project Ideas",
                    class_name="text-2xl font-semibold text-gray-900 mb-4",
                ),
                rx.el.div(
                    rx.foreach(ProjectState.project_ideas, project_idea_card),
                    class_name="grid md:grid-cols-2 gap-6",
                ),
                class_name="mb-12",
            ),
            rx.el.div(
                rx.el.h2(
                    "Resources", class_name="text-2xl font-semibold text-gray-900 mb-4"
                ),
                rx.el.div(
                    rx.foreach(ProjectState.resources, resource_card),
                    class_name="grid md:grid-cols-2 gap-6",
                ),
            ),
            class_name="p-4 md:p-6 lg:p-8",
        ),
        class_name="font-['IBM_Plex_Sans'] bg-gray-50 min-h-screen flex flex-col",
    )