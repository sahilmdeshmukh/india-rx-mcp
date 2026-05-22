from datetime import date

import pytest

from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.models import Approval, Formulation
from india_rx_mcp.cache.repo import upsert_approvals, upsert_formulations
from india_rx_mcp.resources.catalogs import approved_drugs_catalog, scheduled_formulations_catalog


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "t.db")
    upsert_approvals(conn, [
        Approval("X-1", "Atorvastatin", "Sun Pharma", date(2024, 6, 1),
                 "Hyperlipidemia", None, None, "http://x"),
    ])
    upsert_formulations(conn, [
        Formulation("NPPA-1", "Atorvastatin", "10mg", "tablet", 2.34,
                    date(2026, 4, 1), "http://x"),
    ])
    from india_rx_mcp.resources import catalogs
    monkeypatch.setattr(catalogs, "_get_conn", lambda: conn)
    yield conn
    conn.close()


def test_approved_drugs_catalog_returns_browseable_list(seeded):
    out = approved_drugs_catalog()
    assert "Atorvastatin" in out
    assert "Sun Pharma" in out


def test_scheduled_formulations_catalog_returns_browseable_list(seeded):
    out = scheduled_formulations_catalog()
    assert "Atorvastatin" in out
    assert "10mg" in out
