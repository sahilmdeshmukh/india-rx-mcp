from datetime import UTC, datetime, timedelta

from india_rx_mcp.cache.db import init_db, set_meta
from india_rx_mcp.refresh import should_refresh_cdsco, should_refresh_nppa


def test_should_refresh_cdsco_when_never_refreshed(tmp_path):
    conn = init_db(tmp_path / "t.db")
    assert should_refresh_cdsco(conn) is True
    conn.close()


def test_should_refresh_cdsco_when_older_than_24h(tmp_path):
    conn = init_db(tmp_path / "t.db")
    old = (datetime.now(UTC) - timedelta(hours=30)).isoformat()
    set_meta(conn, "cdsco_last_refresh", old)
    assert should_refresh_cdsco(conn) is True
    conn.close()


def test_should_not_refresh_cdsco_when_recent(tmp_path):
    conn = init_db(tmp_path / "t.db")
    recent = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    set_meta(conn, "cdsco_last_refresh", recent)
    assert should_refresh_cdsco(conn) is False
    conn.close()


def test_should_refresh_nppa_threshold_is_7_days(tmp_path):
    conn = init_db(tmp_path / "t.db")
    older_than_week = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    set_meta(conn, "nppa_last_refresh", older_than_week)
    assert should_refresh_nppa(conn) is True
    fresh = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    set_meta(conn, "nppa_last_refresh", fresh)
    assert should_refresh_nppa(conn) is False
    conn.close()
