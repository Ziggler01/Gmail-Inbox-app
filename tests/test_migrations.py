import os
from sqlalchemy import create_engine, inspect
from alembic import command
from alembic.config import Config

# Use a file DB so Alembic (async) and SQLAlchemy (sync) see the same DB
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

def _upgrade_head() -> None:
    cfg = Config("alembic.ini")  # at repo root
    # Ensure Alembic uses the same URL as tests
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")

def test_tables_exist_after_migration():
    # Run migrations for this test run
    _upgrade_head()

    # Use the sync driver to inspect the file DB created by Alembic
    eng = create_engine("sqlite:///./test.db")
    insp = inspect(eng)
    tables = set(insp.get_table_names())
    for t in ("audits", "action_plans", "undo_windows"):
        assert t in tables, f"Missing table: {t}"
