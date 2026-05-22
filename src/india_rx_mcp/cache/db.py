import os
import sqlite3
from pathlib import Path

from platformdirs import user_cache_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    drug_name TEXT NOT NULL,
    sponsor TEXT,
    approval_date TEXT,           -- ISO 8601
    indication TEXT,
    formulation TEXT,
    conditions TEXT,
    source_url TEXT NOT NULL,
    scraped_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_approvals_sponsor ON approvals(sponsor);
CREATE INDEX IF NOT EXISTS idx_approvals_date ON approvals(approval_date);
CREATE INDEX IF NOT EXISTS idx_approvals_drug ON approvals(drug_name);

CREATE TABLE IF NOT EXISTS formulations (
    formulation_id TEXT PRIMARY KEY,
    drug_name TEXT NOT NULL,
    strength TEXT,
    form TEXT,                    -- tablet, injection, etc.
    ceiling_price_inr REAL,
    price_effective_date TEXT,
    source_url TEXT NOT NULL,
    scraped_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_formulations_drug ON formulations(drug_name);

CREATE TABLE IF NOT EXISTS price_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    formulation_id TEXT NOT NULL,
    old_price_inr REAL,
    new_price_inr REAL NOT NULL,
    effective_date TEXT NOT NULL,
    reason TEXT,
    source_url TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    CONSTRAINT uq_price_change UNIQUE(formulation_id, effective_date),
    FOREIGN KEY (formulation_id) REFERENCES formulations(formulation_id)
);
CREATE INDEX IF NOT EXISTS idx_price_changes_date ON price_changes(effective_date);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scraper_errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,         -- 'cdsco' or 'nppa'
    url TEXT,
    error_message TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);
"""


def get_db_path() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    cache_dir = Path(xdg) / "india-rx-mcp" if xdg else Path(user_cache_dir("india-rx-mcp"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "cache.db"


def init_db(path: Path | None = None) -> sqlite3.Connection:
    if path is None:
        path = get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # allow concurrent readers during refresh writes
    # executescript() issues an implicit COMMIT; DDL is already durable.
    # NOTE: check_same_thread=True by default. Background threads (e.g. refresh worker)
    # must open their own connection.
    conn.executescript(SCHEMA)
    return conn


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None
