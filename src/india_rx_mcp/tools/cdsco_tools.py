import sqlite3
from datetime import date

from india_rx_mcp.cache.db import init_db
from india_rx_mcp.formatting import approval_detail, approvals_table
from india_rx_mcp.services.approvals_service import ApprovalsService

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = init_db()
    return _conn


def _parse_iso(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def search_cdsco_approvals(
    query: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    therapeutic_area: str | None = None,
    sponsor: str | None = None,
    limit: int = 20,
) -> str:
    """Search CDSCO-approved drugs by drug name, date range, therapeutic area, or sponsor.

    Note (v1 limitation): The CDSCO data source (yearly PDFs) does not include sponsor
    information, so the `sponsor` filter will return no results for CDSCO-sourced data.
    """
    svc = ApprovalsService(_get_conn())
    results = svc.search(
        query=query, from_date=_parse_iso(from_date), to_date=_parse_iso(to_date),
        therapeutic_area=therapeutic_area, sponsor=sponsor, limit=limit,
    )
    return approvals_table(results)


def get_cdsco_approval(approval_id: str | None = None, drug_name: str | None = None) -> str:
    """Get full record for one CDSCO approval. Provide either approval_id or drug_name."""
    if not approval_id and not drug_name:
        return "_Error: provide either `approval_id` or `drug_name`._"
    svc = ApprovalsService(_get_conn())
    a = svc.get(approval_id=approval_id, drug_name=drug_name)
    if not a:
        return f"_No approval found for {approval_id or drug_name!r}._"
    return approval_detail(a)


def list_recent_cdsco_approvals(since_date: str | None = None, limit: int = 20) -> str:
    """List CDSCO approvals since a date (default: 30 days ago)."""
    svc = ApprovalsService(_get_conn())
    results = svc.recent(since_date=_parse_iso(since_date), limit=limit)
    return approvals_table(results)


def cdsco_sponsor_pipeline(sponsor_name: str) -> str:
    """Get all CDSCO approvals for a sponsor (company), grouped chronologically.

    Note (v1 limitation): The CDSCO data source (yearly PDFs) does not include sponsor
    information. This tool will return empty results for CDSCO-sourced data in v1.
    Sponsor data may be added in v1.1.
    """
    svc = ApprovalsService(_get_conn())
    results = svc.sponsor_pipeline(sponsor_name)
    if not results:
        return f"_No approvals found for sponsor matching {sponsor_name!r}._"
    return approvals_table(results)
