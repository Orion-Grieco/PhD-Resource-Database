import reflex as rx
from typing import TypedDict
from sqlalchemy import text
import asyncio
import logging


class Program(TypedDict):
    id: int
    university_name: str
    program_name: str
    department: str
    degree_type: str
    research_area: str
    application_deadline: str
    tuition_in_state: int
    tuition_out_of_state: int
    url: str
    description: str


class ProgramState(rx.State):
    programs: list[Program] = []
    loading: bool = False
    search_query: str = ""
    selected_degree: str = ""
    selected_research_area: str = ""

    @rx.event(background=True)
    async def get_all_programs(self):
        async with self:
            if not self.programs:
                self.loading = True
        try:
            async with rx.asession() as session:
                result = await session.execute(
                    text(
                        "SELECT id, university_name, program_name, department, degree_type, research_area, TO_CHAR(application_deadline, 'YYYY-MM-DD') as application_deadline, tuition_in_state, tuition_out_of_state, url, description FROM program ORDER BY university_name;"
                    )
                )
                rows = result.mappings().all()
                await asyncio.sleep(1.5)
                async with self:
                    self.programs = [dict(row) for row in rows]
        except Exception as e:
            logging.exception(f"Database query failed: {e}")
        finally:
            async with self:
                self.loading = False

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

    def clear_filters(self):
        self.search_query = ""
        self.selected_degree = ""
        self.selected_research_area = ""