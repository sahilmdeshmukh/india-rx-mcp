from datetime import date

from india_rx_mcp.cache.models import Approval, Formulation
from india_rx_mcp.formatting import (
    approval_detail,
    approvals_table,
    citations_block,
    formulations_table,
)


def test_approvals_table_includes_header_and_row():
    rows = [Approval("X-1", "Atorvastatin", "Sun Pharma", date(2024, 6, 1),
                     "Hyperlipidemia", "10mg tablet", None, "http://x")]
    md = approvals_table(rows)
    assert "| Drug |" in md
    assert "Atorvastatin" in md
    assert "Sun Pharma" in md


def test_approvals_table_empty_returns_helpful_message():
    md = approvals_table([])
    assert "No approvals" in md


def test_approval_detail_includes_all_fields():
    a = Approval("X-1", "Atorvastatin", "Sun Pharma", date(2024, 6, 1),
                 "Hyperlipidemia", "10mg tablet", "Phase IV required", "http://x")
    md = approval_detail(a)
    assert "Atorvastatin" in md
    assert "Sun Pharma" in md
    assert "Phase IV required" in md
    assert "http://x" in md


def test_formulations_table_shows_price_with_inr_symbol():
    rows = [Formulation("NPPA-1", "Atorvastatin", "10mg", "tablet", 2.34,
                        date(2026, 4, 1), "http://x")]
    md = formulations_table(rows)
    assert "₹" in md or "INR" in md
    assert "2.34" in md


def test_citations_block_dedupes_urls():
    md = citations_block(["http://a", "http://b", "http://a"])
    assert md.count("http://a") == 1
    assert "http://b" in md
