from pathlib import Path
from india_rx_mcp.cache.db import get_db_path, init_db


def test_get_db_path_is_under_user_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    p = get_db_path()
    assert p.parent.name == "india-rx-mcp"
    assert p.name == "cache.db"


def test_init_db_creates_all_tables(tmp_path):
    db_path = tmp_path / "test.db"
    conn = init_db(db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert {"approvals", "formulations", "price_changes", "meta", "scraper_errors"} <= tables
    conn.close()


def test_init_db_is_idempotent(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path).close()
    init_db(db_path).close()
