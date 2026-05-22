import sqlite3
from datetime import date

from india_rx_mcp.cache.db import init_db
from india_rx_mcp.formatting import formulations_table, price_changes_table
from india_rx_mcp.services.pricing_service import PricingService

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = init_db()
    return _conn


def _parse_iso(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def get_nppa_ceiling_price(
    drug_name: str, strength: str | None = None, form: str | None = None
) -> str:
    """Get the NPPA ceiling price for a drug. Optionally narrow by strength and form."""
    svc = PricingService(_get_conn())
    results = svc.get_ceiling_price(drug_name=drug_name, strength=strength, form=form)
    return formulations_table(results)


def search_nppa_scheduled_formulations(
    query: str | None = None, therapeutic_area: str | None = None, limit: int = 20
) -> str:
    """Search NPPA-controlled (scheduled) formulations by free text or therapeutic area.

    Note (v1 limitation): NPPA formulations don't carry indication; the `therapeutic_area`
    filter is a best-effort substring match on drug name. For richer therapeutic-area
    filtering, use `search_cdsco_approvals(therapeutic_area=...)` which has keyword expansion.
    """
    svc = PricingService(_get_conn())
    results = svc.search_scheduled(query=query, therapeutic_area=therapeutic_area, limit=limit)
    return formulations_table(results)


def list_nppa_price_changes(since_date: str | None = None, limit: int = 50) -> str:
    """List recent NPPA price revisions (default: last 180 days).

    Note (v1 limitation): The v1 NPPA scraper sources data from the 2022 Compendium of Prices,
    which is a snapshot, not a change log. PriceChange data is empty in v1 unless populated
    externally. Future versions will derive changes from comparing successive compendiums or
    parsing WPI revision notifications.
    """
    svc = PricingService(_get_conn())
    results = svc.price_changes(since_date=_parse_iso(since_date), limit=limit)
    return price_changes_table(results)
