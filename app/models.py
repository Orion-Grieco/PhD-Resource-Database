import reflex as rx
import datetime


class Program(rx.Model, table=True):
    university_name: str
    program_name: str
    department: str
    degree_type: str
    research_area: str
    application_deadline: datetime.date
    tuition_in_state: int
    tuition_out_of_state: int
    url: str
    description: str