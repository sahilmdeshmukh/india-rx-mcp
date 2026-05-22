from india_rx_mcp.cache.db import get_db_path, get_meta, init_db, set_meta


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
    conn1 = init_db(db_path)
    set_meta(conn1, "marker", "from_first_init")
    conn1.close()

    conn2 = init_db(db_path)
    assert get_meta(conn2, "marker") == "from_first_init"
    conn2.close()


def test_set_meta_and_get_meta_round_trip(tmp_path):
    conn = init_db(tmp_path / "t.db")
    set_meta(conn, "cdsco_last_refresh", "2026-05-22T10:00:00")
    assert get_meta(conn, "cdsco_last_refresh") == "2026-05-22T10:00:00"
    conn.close()


def test_get_meta_returns_none_for_unknown_key(tmp_path):
    conn = init_db(tmp_path / "t.db")
    assert get_meta(conn, "does_not_exist") is None
    conn.close()


def test_set_meta_updates_existing_value(tmp_path):
    conn = init_db(tmp_path / "t.db")
    set_meta(conn, "key", "v1")
    set_meta(conn, "key", "v2")
    assert get_meta(conn, "key") == "v2"
    conn.close()
