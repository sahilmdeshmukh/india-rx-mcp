from datetime import date

import pytest

from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.models import Formulation, PriceChange
from india_rx_mcp.cache.repo import upsert_formulations, upsert_price_changes
from india_rx_mcp.tools.nppa_tools import (
    get_nppa_ceiling_price,
    list_nppa_price_changes,
    search_nppa_scheduled_formulations,
)


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "t.db")
    upsert_formulations(conn, [
        Formulation("NPPA-1", "Atorvastatin", "10mg", "tablet", 2.34,
                    date(2026, 4, 1), "http://x"),
        Formulation("NPPA-2", "Metformin", "500mg", "tablet", 1.10,
                    date(2026, 4, 1), "http://x"),
    ])
    upsert_price_changes(conn, [
        PriceChange(None, "NPPA-1", 2.20, 2.34, date(2026, 4, 1),
                    "WPI 2026", "http://x"),
    ])
    from india_rx_mcp.tools import nppa_tools as mod
    monkeypatch.setattr(mod, "_get_conn", lambda: conn)
    yield conn
    conn.close()


def test_get_nppa_ceiling_price(seeded):
    md = get_nppa_ceiling_price("atorvastatin", strength="10mg")
    assert "₹2.34" in md
    assert "tablet" in md


def test_search_nppa_scheduled_formulations(seeded):
    md = search_nppa_scheduled_formulations(query="metformin")
    assert "Metformin" in md
    assert "Atorvastatin" not in md


def test_list_nppa_price_changes(seeded):
    md = list_nppa_price_changes(since_date="2026-01-01")
    assert "₹2.20" in md
    assert "₹2.34" in md
    assert "WPI 2026" in md
