import reflex as rx

# Local SQLite by default; set REFLEX_DB_URL (e.g. a Postgres URL) to override.
config = rx.Config(app_name="app", db_url="sqlite:///programs.db", plugins=[rx.plugins.TailwindV3Plugin()])
