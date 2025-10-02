import reflex as rx
from typing import TypedDict


class Project(TypedDict):
    title: str
    description: str
    technologies: list[str]
    link: str


class ProjectIdea(TypedDict):
    title: str
    description: str
    relevant_fields: list[str]


class Resource(TypedDict):
    name: str
    description: str
    link: str


class ProjectState(rx.State):
    projects: list[Project] = [
        {
            "title": "Real-time Data Visualization for IoT Sensor Networks",
            "description": "A web-based dashboard that visualizes sensor data from IoT devices in real-time. The project focuses on efficient data handling and interactive visualizations to monitor environmental conditions.",
            "technologies": ["Python", "Reflex", "WebSocket", "Plotly"],
            "link": "#",
        },
        {
            "title": "Machine Learning Model for Predictive Maintenance",
            "description": "Developing a predictive maintenance model for industrial machinery using machine learning techniques. The goal is to predict equipment failures before they happen, reducing downtime.",
            "technologies": ["Python", "scikit-learn", "Pandas", "FastAPI"],
            "link": "#",
        },
    ]
    project_ideas: list[ProjectIdea] = [
        {
            "title": "AI-Powered Tutoring System for Computer Science",
            "description": "Create an intelligent tutoring system that adapts to a student's learning pace and provides personalized exercises and feedback for core computer science concepts.",
            "relevant_fields": [
                "Artificial Intelligence",
                "Education Technology",
                "Natural Language Processing",
            ],
        },
        {
            "title": "Blockchain-based Supply Chain Management",
            "description": "Design a decentralized application for tracking goods in a supply chain, ensuring transparency and security using blockchain technology.",
            "relevant_fields": ["Blockchain", "Logistics", "Cybersecurity"],
        },
    ]
    resources: list[Resource] = [
        {
            "name": "Papers with Code",
            "description": "A free and open resource with Machine Learning papers, code and evaluation tables.",
            "link": "https://paperswithcode.com/",
        },
        {
            "name": "Google Scholar",
            "description": "A freely accessible web search engine that indexes the full text or metadata of scholarly literature across an array of publishing formats and disciplines.",
            "link": "https://scholar.google.com/",
        },
    ]