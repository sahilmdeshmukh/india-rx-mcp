import sqlite3

from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.repo import find_approvals, find_formulations
from india_rx_mcp.formatting import approvals_table, formulations_table

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = init_db()
    return _conn


def approved_drugs_catalog() -> str:
    """The full list of CDSCO-approved drugs as a browseable resource."""
    results = find_approvals(_get_conn(), limit=100000)
    return "# CDSCO Approved Drugs — Full Catalog\n\n" + approvals_table(results)


def scheduled_formulations_catalog() -> str:
    """The full list of NPPA scheduled formulations as a browseable resource."""
    results = find_formulations(_get_conn(), limit=100000)
    return "# NPPA Scheduled Formulations — Full Catalog\n\n" + formulations_table(results)
