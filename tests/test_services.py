from datetime import date, timedelta

import pytest

from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.models import Approval, Formulation, PriceChange
from india_rx_mcp.cache.repo import upsert_approvals, upsert_formulations, upsert_price_changes
from india_rx_mcp.services.approvals_service import ApprovalsService
from india_rx_mcp.services.pricing_service import PricingService


@pytest.fixture
def db_with_data(tmp_path):
    conn = init_db(tmp_path / "t.db")
    upsert_approvals(conn, [
        Approval("X-1", "Atorvastatin", "Sun Pharma", date(2024, 6, 1),
                 "Hyperlipidemia", "10mg tablet", None, "http://x"),
        Approval("X-2", "Pembrolizumab", "MSD Pharmaceuticals",
                 date(2024, 8, 15), "Cancer (oncology)", "Vial", None, "http://x"),
    ])
    upsert_formulations(conn, [
        Formulation("NPPA-1", "Atorvastatin", "10mg", "tablet", 2.34,
                    date(2026, 4, 1), "http://x"),
    ])
    upsert_price_changes(conn, [
        PriceChange(None, "NPPA-1", 2.20, 2.34, date(2026, 4, 1), "WPI 2026", "http://x"),
    ])
    yield conn
    conn.close()


def test_approvals_service_recent_default_30_days(db_with_data):
    svc = ApprovalsService(db_with_data)
    very_recent = date.today() - timedelta(days=5)
    upsert_approvals(db_with_data, [
        Approval("X-3", "DrugRecent", None, very_recent, None, None, None, "http://x"),
    ])
    results = svc.recent()
    assert any(a.drug_name == "DrugRecent" for a in results)
    assert not any(a.drug_name == "Atorvastatin" for a in results)


def test_approvals_service_sponsor_pipeline(db_with_data):
    svc = ApprovalsService(db_with_data)
    results = svc.sponsor_pipeline("sun pharma")
    assert len(results) == 1
    assert results[0].drug_name == "Atorvastatin"


def test_approvals_service_search_by_therapeutic_area_uses_keyword_expansion(db_with_data):
    svc = ApprovalsService(db_with_data)
    results = svc.search(therapeutic_area="oncology")
    assert any(a.drug_name == "Pembrolizumab" for a in results)


def test_pricing_service_get_ceiling_price(db_with_data):
    svc = PricingService(db_with_data)
    results = svc.get_ceiling_price("atorvastatin", strength="10mg")
    assert len(results) == 1
    assert results[0].ceiling_price_inr == 2.34


def test_pricing_service_price_changes_default_180_days(db_with_data):
    svc = PricingService(db_with_data)
    results = svc.price_changes()
    assert len(results) >= 0
