from datetime import date

import pytest

from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.models import Approval, Formulation, PriceChange
from india_rx_mcp.cache.repo import (
    find_approvals,
    find_formulations,
    find_price_changes,
    upsert_approvals,
    upsert_formulations,
    upsert_price_changes,
)


@pytest.fixture
def db(tmp_path):
    conn = init_db(tmp_path / "t.db")
    yield conn
    conn.close()


def test_upsert_and_find_approvals(db):
    a = Approval(
        approval_id="X-1", drug_name="Atorvastatin", sponsor="Sun Pharma",
        approval_date=date(2024, 6, 1), indication="Hyperlipidemia",
        formulation="10mg tablet", conditions=None, source_url="http://x",
    )
    upsert_approvals(db, [a])
    results = find_approvals(db, drug_query="ator")
    assert len(results) == 1
    assert results[0].sponsor == "Sun Pharma"


def test_find_approvals_filters_by_sponsor_substring(db):
    upsert_approvals(db, [
        Approval("X-1", "DrugA", "Sun Pharmaceutical Industries Ltd.",
                 date(2024, 1, 1), None, None, None, "http://x"),
        Approval("X-2", "DrugB", "Cipla Ltd.",
                 date(2024, 1, 1), None, None, None, "http://x"),
    ])
    results = find_approvals(db, sponsor="sun pharma")
    assert len(results) == 1
    assert results[0].drug_name == "DrugA"


def test_find_approvals_date_range(db):
    upsert_approvals(db, [
        Approval("X-1", "DrugA", None, date(2023, 6, 1), None, None, None, "http://x"),
        Approval("X-2", "DrugB", None, date(2024, 6, 1), None, None, None, "http://x"),
    ])
    results = find_approvals(db, from_date=date(2024, 1, 1))
    assert len(results) == 1
    assert results[0].drug_name == "DrugB"


def test_find_formulations_by_drug(db):
    upsert_formulations(db, [
        Formulation("NPPA-1", "Atorvastatin", "10mg", "tablet", 2.34,
                    date(2026, 4, 1), "http://x"),
    ])
    results = find_formulations(db, drug_name="atorvastatin")
    assert len(results) == 1
    assert results[0].ceiling_price_inr == 2.34


def test_upsert_is_idempotent(db):
    a = Approval("X-1", "A", "S", date(2024, 1, 1), None, None, None, "http://x")
    upsert_approvals(db, [a, a])
    assert len(find_approvals(db)) == 1


def test_find_price_changes_by_date_range(db):
    upsert_price_changes(db, [
        PriceChange(None, "NPPA-1", 2.0, 2.34, date(2026, 4, 1), "WPI", "http://x"),
        PriceChange(None, "NPPA-1", 2.34, 2.40, date(2025, 4, 1), "WPI", "http://x"),
    ])
    results = find_price_changes(db, from_date=date(2026, 1, 1))
    assert len(results) == 1
    assert results[0].new_price_inr == 2.34
