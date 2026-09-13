import sqlite3
from importlib.resources import files


SCHEMA = files("agent_os.data").joinpath("schema.sql")


class Database:
    """Own one SQLite connection and its schema lifecycle."""

    def __init__(self, path: str = ":memory:"):
        if not path.strip():
            raise ValueError("path must not be empty")

        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

        schema = SCHEMA.read_text(encoding="utf-8")
        self.conn.executescript(schema)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
