from datetime import date

import pytest

from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.models import Approval
from india_rx_mcp.cache.repo import upsert_approvals
from india_rx_mcp.tools.cdsco_tools import (
    cdsco_sponsor_pipeline,
    get_cdsco_approval,
    search_cdsco_approvals,
)


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "t.db")
    upsert_approvals(conn, [
        Approval("X-1", "Atorvastatin", "Sun Pharma", date(2024, 6, 1),
                 "Hyperlipidemia", "10mg tab", None, "http://x"),
        Approval("X-2", "Pembrolizumab", "MSD", date(2024, 8, 15),
                 "Cancer (oncology)", "Vial", None, "http://x"),
    ])
    from india_rx_mcp.tools import cdsco_tools as mod
    monkeypatch.setattr(mod, "_get_conn", lambda: conn)
    yield conn
    conn.close()


def test_search_cdsco_approvals_returns_markdown_table(seeded):
    md = search_cdsco_approvals(query="ator")
    assert "Atorvastatin" in md
    assert "| Drug |" in md
    assert "Sources" in md


def test_get_cdsco_approval_by_drug_name(seeded):
    md = get_cdsco_approval(drug_name="atorvastatin")
    assert "Sun Pharma" in md
    assert "Hyperlipidemia" in md


def test_get_cdsco_approval_missing_returns_message(seeded):
    md = get_cdsco_approval(drug_name="nonexistent")
    assert "not found" in md.lower() or "no " in md.lower()


def test_cdsco_sponsor_pipeline(seeded):
    md = cdsco_sponsor_pipeline("sun pharma")
    assert "Atorvastatin" in md
    assert "MSD" not in md


def test_search_cdsco_approvals_by_therapeutic_area(seeded):
    md = search_cdsco_approvals(therapeutic_area="oncology")
    assert "Pembrolizumab" in md
