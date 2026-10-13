"""The restore drill stays on SQLite and does not read production settings."""
import inspect

from app.services.restore_drill import run_restore_drill


def test_restore_drill_copies_a_row_without_production_credentials():
    source = inspect.getsource(run_restore_drill)
    assert "DATABASE_URL" not in source
    assert "neon.tech" not in source
    restored = run_restore_drill()
    assert restored == {
        "company_name": "Restore Drill",
        "country": "South Africa",
        "source_type": "PRIVATE",
        "active": True,
    }
