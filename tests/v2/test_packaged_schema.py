from importlib.resources import files

from agent_os.storage.database import Database


def test_schema_is_available_as_package_resource():
    schema = files("agent_os.data").joinpath("schema.sql")

    assert schema.is_file()
    assert "CREATE TABLE" in schema.read_text(encoding="utf-8")


def test_database_uses_packaged_schema():
    with Database() as database:
        tables = {
            row["name"]
            for row in database.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert "memory_items" in tables
    assert "task_runs" in tables
