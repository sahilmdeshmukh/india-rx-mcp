import logging
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from platformdirs import user_cache_dir

from india_rx_mcp.cache.db import get_meta, init_db, set_meta
from india_rx_mcp.cache.repo import upsert_approvals, upsert_formulations
from india_rx_mcp.scrapers.cdsco_scraper import scrape_all_years as scrape_cdsco_all
from india_rx_mcp.scrapers.nppa_scraper import COMPENDIUM_URL_2022, scrape_compendium

log = logging.getLogger(__name__)

CDSCO_REFRESH_INTERVAL = timedelta(hours=24)
NPPA_REFRESH_INTERVAL = timedelta(days=7)


def _is_stale(last: str | None, interval: timedelta) -> bool:
    if not last:
        return True
    last_dt = datetime.fromisoformat(last)
    # Handle naive timestamps from older versions by treating as UTC
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=UTC)
    return datetime.now(UTC) - last_dt > interval


def should_refresh_cdsco(conn: sqlite3.Connection) -> bool:
    return _is_stale(get_meta(conn, "cdsco_last_refresh"), CDSCO_REFRESH_INTERVAL)


def should_refresh_nppa(conn: sqlite3.Connection) -> bool:
    return _is_stale(get_meta(conn, "nppa_last_refresh"), NPPA_REFRESH_INTERVAL)


def _log_error(conn: sqlite3.Connection, source: str, url: str | None, err: Exception) -> None:
    conn.execute(
        "INSERT INTO scraper_errors(source, url, error_message, occurred_at) VALUES (?,?,?,?)",
        (source, url, str(err), datetime.now(UTC).isoformat()),
    )
    conn.commit()


def refresh_cdsco() -> int:
    # Each scrape opens its own connection (background-thread-safe).
    conn = init_db()
    n = 0
    try:
        cache_dir = Path(user_cache_dir("india-rx-mcp")) / "cdsco_pdfs"
        cache_dir.mkdir(parents=True, exist_ok=True)
        approvals = list(scrape_cdsco_all(cache_dir))
        n = upsert_approvals(conn, approvals)
        set_meta(conn, "cdsco_last_refresh", datetime.now(UTC).isoformat())
        log.info("CDSCO refresh: %d approvals upserted", n)
    except Exception as e:
        log.exception("CDSCO refresh failed: %s", e)
        _log_error(conn, "cdsco", None, e)
    finally:
        conn.close()
    return n


def refresh_nppa() -> int:
    conn = init_db()
    n = 0
    try:
        pdf_dir = Path(user_cache_dir("india-rx-mcp")) / "nppa_pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        dest = pdf_dir / "compendium_2022.pdf"
        formulations = scrape_compendium(COMPENDIUM_URL_2022, dest)
        n = upsert_formulations(conn, formulations)
        set_meta(conn, "nppa_last_refresh", datetime.now(UTC).isoformat())
        log.info("NPPA refresh: %d formulations upserted", n)
    except Exception as e:
        log.exception("NPPA refresh failed: %s", e)
        _log_error(conn, "nppa", None, e)
    finally:
        conn.close()
    return n


def refresh_if_stale_in_background() -> None:
    conn = init_db()
    cdsco_due = should_refresh_cdsco(conn)
    nppa_due = should_refresh_nppa(conn)
    conn.close()

    def _run() -> None:
        if cdsco_due:
            refresh_cdsco()
        if nppa_due:
            refresh_nppa()

    if cdsco_due or nppa_due:
        threading.Thread(target=_run, daemon=True, name="india-rx-refresh").start()
