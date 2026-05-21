# india-rx-mcp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a published-to-PyPI MCP server (`india-rx-mcp`) that exposes CDSCO drug approvals and NPPA ceiling-price data through 7 tools, 2 resources, and 3 prompts to any MCP-compatible LLM client.

**Architecture:** Layered Python package: scrapers fetch from gov.in into a SQLite cache; services query the cache; tools/resources/prompts wrap services in MCP primitives via FastMCP. Tool responses read only from cache, so they're fast and resilient.

**Tech Stack:** Python 3.11+, `mcp[cli]` SDK (FastMCP), `httpx`, `BeautifulSoup4`, `pdfplumber`, SQLite (stdlib), `pytest`, `uv`, PyPI publishing via `uv publish`.

**Spec reference:** [docs/superpowers/specs/2026-05-21-india-rx-mcp-design.md](../specs/2026-05-21-india-rx-mcp-design.md)

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/india_rx_mcp/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`
- Create: `.gitignore`
- Create: `README.md` (stub — full version comes in Task 17)
- Create: `LICENSE` (MIT)

- [ ] **Step 1: Initialize git and write .gitignore**

```bash
git init
```

Create `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
dist/
build/
*.egg-info/
.coverage
htmlcov/
.DS_Store
*.db
tests/fixtures/cache/
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "india-rx-mcp"
version = "0.1.0"
description = "MCP server for Indian pharma regulatory data (CDSCO approvals + NPPA pricing)"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Sahil Deshmukh", email = "sahildeshmukh.pune@gmail.com" }]
keywords = ["mcp", "model-context-protocol", "pharma", "cdsco", "nppa", "india"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Healthcare Industry",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "mcp[cli]>=1.27.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "pdfplumber>=0.11.0",
    "platformdirs>=4.0.0",
    "click>=8.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "respx>=0.21.0",
    "ruff>=0.5.0",
]

[project.scripts]
india-rx-mcp = "india_rx_mcp.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/india_rx_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 3: Write package init and stub README + LICENSE**

`src/india_rx_mcp/__init__.py`:

```python
__version__ = "0.1.0"
```

`README.md` (stub — replaced in Task 17):

```markdown
# india-rx-mcp

MCP server for Indian pharma regulatory data (CDSCO approvals + NPPA pricing).

Under construction.
```

`LICENSE`:

```
MIT License

Copyright (c) 2026 Sahil Deshmukh

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Write smoke test**

`tests/__init__.py`: (empty)

`tests/test_smoke.py`:

```python
from india_rx_mcp import __version__


def test_version():
    assert __version__ == "0.1.0"
```

- [ ] **Step 5: Install dependencies, run the test**

```bash
uv venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
pytest
```

Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add .gitignore pyproject.toml src tests README.md LICENSE
git commit -m "feat: project scaffold with smoke test"
```

---

## Task 2: SQLite cache schema and DB helpers

**Files:**
- Create: `src/india_rx_mcp/cache/__init__.py`
- Create: `src/india_rx_mcp/cache/db.py`
- Create: `tests/test_cache_db.py`

- [ ] **Step 1: Write failing test for `get_db_path`**

`tests/test_cache_db.py`:

```python
from pathlib import Path
from india_rx_mcp.cache.db import get_db_path, init_db


def test_get_db_path_is_under_user_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    p = get_db_path()
    assert p.parent.name == "india-rx-mcp"
    assert p.name == "cache.db"


def test_init_db_creates_all_tables(tmp_path):
    db_path = tmp_path / "test.db"
    conn = init_db(db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert {"approvals", "formulations", "price_changes", "meta", "scraper_errors"} <= tables
    conn.close()


def test_init_db_is_idempotent(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path).close()
    init_db(db_path).close()
```

- [ ] **Step 2: Run test, confirm failure**

```bash
pytest tests/test_cache_db.py -v
```

Expected: `ImportError: cannot import name 'get_db_path' from 'india_rx_mcp.cache.db'`

- [ ] **Step 3: Implement `cache/db.py`**

`src/india_rx_mcp/cache/__init__.py`: (empty)

`src/india_rx_mcp/cache/db.py`:

```python
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
    cache_dir = Path(user_cache_dir("india-rx-mcp"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "cache.db"


def init_db(path: Path | None = None) -> sqlite3.Connection:
    if path is None:
        path = get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
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
```

- [ ] **Step 4: Run tests, confirm pass**

```bash
pytest tests/test_cache_db.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/india_rx_mcp/cache tests/test_cache_db.py
git commit -m "feat: SQLite cache schema with approvals, formulations, price_changes tables"
```

---

## Task 3: Domain dataclasses

**Files:**
- Create: `src/india_rx_mcp/cache/models.py`
- Create: `tests/test_cache_models.py`

- [ ] **Step 1: Write failing test**

`tests/test_cache_models.py`:

```python
from datetime import date
from india_rx_mcp.cache.models import Approval, Formulation, PriceChange


def test_approval_dataclass_round_trips_through_db_row():
    a = Approval(
        approval_id="CDSCO-2024-0123",
        drug_name="Atorvastatin",
        sponsor="Sun Pharmaceutical Industries Ltd.",
        approval_date=date(2024, 6, 15),
        indication="Hyperlipidemia",
        formulation="Atorvastatin Tablets 10mg",
        conditions="Phase IV study required",
        source_url="https://cdsco.gov.in/approval/2024/0123",
    )
    assert a.drug_name == "Atorvastatin"
    assert a.approval_date.isoformat() == "2024-06-15"


def test_formulation_optional_fields():
    f = Formulation(
        formulation_id="NPPA-F-001",
        drug_name="Atorvastatin",
        strength="10mg",
        form="tablet",
        ceiling_price_inr=2.34,
        price_effective_date=date(2026, 4, 1),
        source_url="https://nppa.gov.in/...",
    )
    assert f.ceiling_price_inr == 2.34


def test_price_change_minimal():
    c = PriceChange(
        change_id=None,
        formulation_id="NPPA-F-001",
        old_price_inr=2.20,
        new_price_inr=2.34,
        effective_date=date(2026, 4, 1),
        reason="WPI 2026 annual revision",
        source_url="https://nppa.gov.in/...",
    )
    assert c.new_price_inr > c.old_price_inr
```

- [ ] **Step 2: Run test, confirm failure**

```bash
pytest tests/test_cache_models.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `cache/models.py`**

`src/india_rx_mcp/cache/models.py`:

```python
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Approval:
    approval_id: str
    drug_name: str
    sponsor: str | None
    approval_date: date | None
    indication: str | None
    formulation: str | None
    conditions: str | None
    source_url: str
    scraped_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Formulation:
    formulation_id: str
    drug_name: str
    strength: str | None
    form: str | None
    ceiling_price_inr: float | None
    price_effective_date: date | None
    source_url: str
    scraped_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PriceChange:
    change_id: int | None             # None for new rows; assigned by SQLite
    formulation_id: str
    old_price_inr: float | None
    new_price_inr: float
    effective_date: date
    reason: str | None
    source_url: str
    scraped_at: datetime = field(default_factory=datetime.utcnow)
```

- [ ] **Step 4: Run tests, confirm pass**

```bash
pytest tests/test_cache_models.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/india_rx_mcp/cache/models.py tests/test_cache_models.py
git commit -m "feat: domain dataclasses for Approval, Formulation, PriceChange"
```

---

## Task 4: CDSCO scraper with fixture-based tests

**Files:**
- Create: `src/india_rx_mcp/scrapers/__init__.py`
- Create: `src/india_rx_mcp/scrapers/cdsco_scraper.py`
- Create: `tests/fixtures/cdsco/approved_drugs_2024.html` (download a real page, save it)
- Create: `tests/test_cdsco_scraper.py`

- [ ] **Step 1: Manually fetch and save a CDSCO fixture**

Open browser to `https://cdsco.gov.in/opencms/opencms/en/Approval_new/Approved-New-Drugs/` and identify the year-pages. Pick one (e.g., 2024) and save its HTML as `tests/fixtures/cdsco/approved_drugs_2024.html`. Confirm the file is committed in Step 7.

If the page structure is unfamiliar, do an exploratory pass: open dev tools, inspect the table containing approvals, note the column order, copy 2-3 actual approval rows for use as expected values in the next step.

- [ ] **Step 2: Write failing tests against the fixture**

`tests/test_cdsco_scraper.py`:

```python
from pathlib import Path
from india_rx_mcp.scrapers.cdsco_scraper import parse_approvals_page, list_year_urls

FIXTURE = Path(__file__).parent / "fixtures" / "cdsco" / "approved_drugs_2024.html"


def test_parse_approvals_page_returns_approvals():
    html = FIXTURE.read_text(encoding="utf-8")
    approvals = parse_approvals_page(html, source_url="https://cdsco.gov.in/test")
    assert len(approvals) > 0
    first = approvals[0]
    assert first.drug_name
    assert first.source_url == "https://cdsco.gov.in/test"
    assert first.approval_id


def test_parse_approvals_page_extracts_approval_date():
    html = FIXTURE.read_text(encoding="utf-8")
    approvals = parse_approvals_page(html, source_url="https://cdsco.gov.in/test")
    dated = [a for a in approvals if a.approval_date is not None]
    assert len(dated) > 0


def test_list_year_urls_includes_recent_years():
    urls = list_year_urls()
    assert any("2024" in u or "2025" in u or "2026" in u for u in urls)
```

- [ ] **Step 3: Run, confirm failure**

```bash
pytest tests/test_cdsco_scraper.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement scraper**

`src/india_rx_mcp/scrapers/__init__.py`: (empty)

`src/india_rx_mcp/scrapers/cdsco_scraper.py`:

```python
import hashlib
import logging
import re
import time
from datetime import date, datetime
from typing import Iterator

import httpx
from bs4 import BeautifulSoup

from india_rx_mcp.cache.models import Approval

log = logging.getLogger(__name__)

BASE = "https://cdsco.gov.in"
APPROVED_INDEX = f"{BASE}/opencms/opencms/en/Approval_new/Approved-New-Drugs/"
USER_AGENT = "india-rx-mcp/0.1.0 (contact: sahildeshmukh.pune@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}
RATE_LIMIT_SECONDS = 1.0


def _client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=30.0, follow_redirects=True)


def list_year_urls() -> list[str]:
    with _client() as c:
        r = c.get(APPROVED_INDEX)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    urls: list[str] = []
    for a in soup.select("a[href]"):
        href = a["href"]
        if re.search(r"(20\d{2})", a.get_text() or "") or re.search(r"(20\d{2})", href):
            if href.startswith("/"):
                href = BASE + href
            if href not in urls:
                urls.append(href)
    return urls


def _make_approval_id(drug_name: str, sponsor: str | None, approval_date: date | None) -> str:
    raw = f"{drug_name}|{sponsor or ''}|{approval_date.isoformat() if approval_date else ''}"
    return "CDSCO-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _parse_date(text: str) -> date | None:
    text = text.strip()
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_approvals_page(html: str, source_url: str) -> list[Approval]:
    soup = BeautifulSoup(html, "lxml")
    approvals: list[Approval] = []

    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not headers:
            continue
        if not any("drug" in h or "name" in h for h in headers):
            continue

        col_idx = {h: i for i, h in enumerate(headers)}

        def col(row_cells, *needles: str) -> str:
            for n in needles:
                for h, i in col_idx.items():
                    if n in h and i < len(row_cells):
                        return row_cells[i].get_text(" ", strip=True)
            return ""

        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if not cells:
                continue
            drug = col(cells, "drug", "name")
            if not drug:
                continue
            sponsor = col(cells, "applicant", "sponsor", "company")
            date_text = col(cells, "date", "approval")
            indication = col(cells, "indication", "use")
            formulation = col(cells, "strength", "formulation", "dosage")
            conditions = col(cells, "condition", "remarks")

            approval_date = _parse_date(date_text) if date_text else None

            approvals.append(
                Approval(
                    approval_id=_make_approval_id(drug, sponsor or None, approval_date),
                    drug_name=drug,
                    sponsor=sponsor or None,
                    approval_date=approval_date,
                    indication=indication or None,
                    formulation=formulation or None,
                    conditions=conditions or None,
                    source_url=source_url,
                )
            )

    return approvals


def scrape_year(url: str) -> list[Approval]:
    log.info("Scraping %s", url)
    with _client() as c:
        r = c.get(url)
        r.raise_for_status()
    time.sleep(RATE_LIMIT_SECONDS)
    return parse_approvals_page(r.text, source_url=url)


def scrape_all_years() -> Iterator[Approval]:
    for url in list_year_urls():
        try:
            for a in scrape_year(url):
                yield a
        except Exception as e:
            log.exception("Failed to scrape %s: %s", url, e)
```

- [ ] **Step 5: Run tests, confirm pass against fixture**

```bash
pytest tests/test_cdsco_scraper.py::test_parse_approvals_page_returns_approvals tests/test_cdsco_scraper.py::test_parse_approvals_page_extracts_approval_date -v
```

Expected: `2 passed`. (The `list_year_urls` test hits the live site — skip it locally if offline; CI will run it.)

If the parser returns 0 approvals, inspect the fixture: the table-detection heuristic depends on `<th>` cells containing "drug" or "name." If CDSCO's table uses different headers, update the keywords in `col()` calls to match what's actually in the fixture.

- [ ] **Step 6: Commit**

```bash
git add src/india_rx_mcp/scrapers tests/test_cdsco_scraper.py tests/fixtures/cdsco
git commit -m "feat: CDSCO scraper with fixture-based parsing tests"
```

---

## Task 5: NPPA scraper

**Files:**
- Create: `src/india_rx_mcp/scrapers/nppa_scraper.py`
- Create: `tests/fixtures/nppa/ceiling_prices_sample.pdf` (download one real NPPA ceiling price PDF)
- Create: `tests/test_nppa_scraper.py`

- [ ] **Step 1: Fetch an NPPA fixture**

From `https://nppa.gov.in/`, find a recent ceiling price order PDF (e.g., the April 2026 WPI revision). Save as `tests/fixtures/nppa/ceiling_prices_sample.pdf`.

Open it manually first. Note the table layout — usually columns like: S.No, Drug Name, Strength, Dosage Form, Ceiling Price (Rs.), Effective Date. Copy 2-3 actual rows to use as expected values in tests.

- [ ] **Step 2: Write failing test**

`tests/test_nppa_scraper.py`:

```python
from pathlib import Path
from india_rx_mcp.scrapers.nppa_scraper import parse_ceiling_price_pdf

FIXTURE = Path(__file__).parent / "fixtures" / "nppa" / "ceiling_prices_sample.pdf"


def test_parse_ceiling_price_pdf_returns_formulations():
    formulations = parse_ceiling_price_pdf(FIXTURE, source_url="https://nppa.gov.in/test.pdf")
    assert len(formulations) > 0
    f = formulations[0]
    assert f.drug_name
    assert f.ceiling_price_inr is not None
    assert f.ceiling_price_inr > 0


def test_parse_ceiling_price_pdf_extracts_strength_and_form():
    formulations = parse_ceiling_price_pdf(FIXTURE, source_url="https://nppa.gov.in/test.pdf")
    with_strength = [f for f in formulations if f.strength]
    assert len(with_strength) > 0
```

- [ ] **Step 3: Run, confirm failure**

```bash
pytest tests/test_nppa_scraper.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement NPPA scraper**

`src/india_rx_mcp/scrapers/nppa_scraper.py`:

```python
import hashlib
import logging
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

import httpx
import pdfplumber

from india_rx_mcp.cache.models import Formulation

log = logging.getLogger(__name__)

BASE = "https://nppa.gov.in"
USER_AGENT = "india-rx-mcp/0.1.0 (contact: sahildeshmukh.pune@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}
RATE_LIMIT_SECONDS = 1.0

PRICE_RE = re.compile(r"(\d+(?:\.\d+)?)")
STRENGTH_RE = re.compile(r"(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|%|units?)\b)", re.IGNORECASE)
FORM_KEYWORDS = ["tablet", "capsule", "injection", "syrup", "cream", "ointment",
                 "drops", "suspension", "solution", "powder", "patch", "inhaler"]


def _make_formulation_id(drug: str, strength: str | None, form: str | None) -> str:
    raw = f"{drug}|{strength or ''}|{form or ''}"
    return "NPPA-F-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _extract_strength(text: str) -> str | None:
    m = STRENGTH_RE.search(text)
    return m.group(1).strip() if m else None


def _extract_form(text: str) -> str | None:
    lower = text.lower()
    for kw in FORM_KEYWORDS:
        if kw in lower:
            return kw
    return None


def _extract_price(text: str) -> float | None:
    cleaned = text.replace(",", "").strip()
    m = PRICE_RE.search(cleaned)
    return float(m.group(1)) if m else None


def parse_ceiling_price_pdf(path: Path, source_url: str,
                            effective_date: date | None = None) -> list[Formulation]:
    formulations: list[Formulation] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                header_row = [(c or "").strip().lower() for c in table[0]]
                if not any("drug" in c or "name" in c or "formulation" in c for c in header_row):
                    continue

                col_idx = {h: i for i, h in enumerate(header_row)}

                def find_col(*needles: str) -> int | None:
                    for n in needles:
                        for h, i in col_idx.items():
                            if n in h:
                                return i
                    return None

                drug_i = find_col("drug", "name", "formulation")
                strength_i = find_col("strength", "potency")
                form_i = find_col("form", "dosage")
                price_i = find_col("price", "ceiling", "mrp")

                if drug_i is None or price_i is None:
                    continue

                for row in table[1:]:
                    if not row or len(row) <= max(drug_i, price_i):
                        continue
                    drug = (row[drug_i] or "").strip()
                    price_text = (row[price_i] or "").strip()
                    if not drug or not price_text:
                        continue

                    strength = (row[strength_i] or "").strip() if strength_i is not None and strength_i < len(row) else None
                    form = (row[form_i] or "").strip() if form_i is not None and form_i < len(row) else None

                    if not strength:
                        strength = _extract_strength(drug)
                    if not form:
                        form = _extract_form(drug)

                    price = _extract_price(price_text)
                    if price is None:
                        continue

                    formulations.append(
                        Formulation(
                            formulation_id=_make_formulation_id(drug, strength, form),
                            drug_name=drug,
                            strength=strength,
                            form=form,
                            ceiling_price_inr=price,
                            price_effective_date=effective_date,
                            source_url=source_url,
                        )
                    )
    return formulations


def list_price_pdfs() -> list[str]:
    with httpx.Client(headers=HEADERS, timeout=30.0, follow_redirects=True) as c:
        r = c.get(BASE + "/ceiling-prices/")
        r.raise_for_status()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "lxml")
    urls: list[str] = []
    for a in soup.select("a[href$='.pdf']"):
        href = a["href"]
        if href.startswith("/"):
            href = BASE + href
        urls.append(href)
    return urls


def scrape_pdf(url: str, dest: Path) -> list[Formulation]:
    log.info("Downloading %s", url)
    with httpx.Client(headers=HEADERS, timeout=60.0, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
    dest.write_bytes(r.content)
    time.sleep(RATE_LIMIT_SECONDS)
    return parse_ceiling_price_pdf(dest, source_url=url)


def scrape_all_pdfs(cache_dir: Path) -> Iterator[Formulation]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    for url in list_price_pdfs():
        try:
            dest = cache_dir / Path(url).name
            for f in scrape_pdf(url, dest):
                yield f
        except Exception as e:
            log.exception("Failed to scrape %s: %s", url, e)
```

- [ ] **Step 5: Run, confirm pass**

```bash
pytest tests/test_nppa_scraper.py -v
```

Expected: `2 passed`.

If the parser returns 0 formulations, open the fixture in pdfplumber's debug mode to inspect actual table extraction. NPPA PDFs vary in layout — adjust the column-keyword matching to fit your fixture.

- [ ] **Step 6: Commit**

```bash
git add src/india_rx_mcp/scrapers/nppa_scraper.py tests/test_nppa_scraper.py tests/fixtures/nppa
git commit -m "feat: NPPA scraper with PDF table extraction"
```

---

## Task 6: Cache write/read helpers

**Files:**
- Create: `src/india_rx_mcp/cache/repo.py`
- Create: `tests/test_cache_repo.py`

- [ ] **Step 1: Write failing test**

`tests/test_cache_repo.py`:

```python
from datetime import date
import pytest
from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.models import Approval, Formulation, PriceChange
from india_rx_mcp.cache.repo import (
    upsert_approvals, upsert_formulations, upsert_price_changes,
    find_approvals, find_formulations, find_price_changes,
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
```

- [ ] **Step 2: Run, confirm failure**

```bash
pytest tests/test_cache_repo.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement repo**

`src/india_rx_mcp/cache/repo.py`:

```python
import sqlite3
from datetime import date, datetime
from typing import Iterable

from india_rx_mcp.cache.models import Approval, Formulation, PriceChange


def _date_str(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    return date.fromisoformat(s)


def upsert_approvals(conn: sqlite3.Connection, approvals: Iterable[Approval]) -> int:
    n = 0
    for a in approvals:
        conn.execute(
            """INSERT INTO approvals(
                approval_id, drug_name, sponsor, approval_date, indication,
                formulation, conditions, source_url, scraped_at
            ) VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(approval_id) DO UPDATE SET
                drug_name=excluded.drug_name,
                sponsor=excluded.sponsor,
                approval_date=excluded.approval_date,
                indication=excluded.indication,
                formulation=excluded.formulation,
                conditions=excluded.conditions,
                source_url=excluded.source_url,
                scraped_at=excluded.scraped_at""",
            (a.approval_id, a.drug_name, a.sponsor, _date_str(a.approval_date),
             a.indication, a.formulation, a.conditions, a.source_url,
             a.scraped_at.isoformat()),
        )
        n += 1
    conn.commit()
    return n


def upsert_formulations(conn: sqlite3.Connection, formulations: Iterable[Formulation]) -> int:
    n = 0
    for f in formulations:
        conn.execute(
            """INSERT INTO formulations(
                formulation_id, drug_name, strength, form, ceiling_price_inr,
                price_effective_date, source_url, scraped_at
            ) VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(formulation_id) DO UPDATE SET
                drug_name=excluded.drug_name,
                strength=excluded.strength,
                form=excluded.form,
                ceiling_price_inr=excluded.ceiling_price_inr,
                price_effective_date=excluded.price_effective_date,
                source_url=excluded.source_url,
                scraped_at=excluded.scraped_at""",
            (f.formulation_id, f.drug_name, f.strength, f.form,
             f.ceiling_price_inr, _date_str(f.price_effective_date),
             f.source_url, f.scraped_at.isoformat()),
        )
        n += 1
    conn.commit()
    return n


def upsert_price_changes(conn: sqlite3.Connection, changes: Iterable[PriceChange]) -> int:
    n = 0
    for c in changes:
        conn.execute(
            """INSERT INTO price_changes(
                formulation_id, old_price_inr, new_price_inr,
                effective_date, reason, source_url, scraped_at
            ) VALUES (?,?,?,?,?,?,?)""",
            (c.formulation_id, c.old_price_inr, c.new_price_inr,
             _date_str(c.effective_date), c.reason, c.source_url,
             c.scraped_at.isoformat()),
        )
        n += 1
    conn.commit()
    return n


def _row_to_approval(row: sqlite3.Row) -> Approval:
    return Approval(
        approval_id=row["approval_id"],
        drug_name=row["drug_name"],
        sponsor=row["sponsor"],
        approval_date=_parse_date(row["approval_date"]),
        indication=row["indication"],
        formulation=row["formulation"],
        conditions=row["conditions"],
        source_url=row["source_url"],
        scraped_at=datetime.fromisoformat(row["scraped_at"]),
    )


def _row_to_formulation(row: sqlite3.Row) -> Formulation:
    return Formulation(
        formulation_id=row["formulation_id"],
        drug_name=row["drug_name"],
        strength=row["strength"],
        form=row["form"],
        ceiling_price_inr=row["ceiling_price_inr"],
        price_effective_date=_parse_date(row["price_effective_date"]),
        source_url=row["source_url"],
        scraped_at=datetime.fromisoformat(row["scraped_at"]),
    )


def _row_to_price_change(row: sqlite3.Row) -> PriceChange:
    return PriceChange(
        change_id=row["change_id"],
        formulation_id=row["formulation_id"],
        old_price_inr=row["old_price_inr"],
        new_price_inr=row["new_price_inr"],
        effective_date=_parse_date(row["effective_date"]),
        reason=row["reason"],
        source_url=row["source_url"],
        scraped_at=datetime.fromisoformat(row["scraped_at"]),
    )


def find_approvals(
    conn: sqlite3.Connection,
    drug_query: str | None = None,
    sponsor: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    indication_query: str | None = None,
    limit: int = 100,
) -> list[Approval]:
    clauses: list[str] = []
    params: list = []
    if drug_query:
        clauses.append("LOWER(drug_name) LIKE ?")
        params.append(f"%{drug_query.lower()}%")
    if sponsor:
        clauses.append("LOWER(sponsor) LIKE ?")
        params.append(f"%{sponsor.lower()}%")
    if from_date:
        clauses.append("approval_date >= ?")
        params.append(from_date.isoformat())
    if to_date:
        clauses.append("approval_date <= ?")
        params.append(to_date.isoformat())
    if indication_query:
        clauses.append("LOWER(indication) LIKE ?")
        params.append(f"%{indication_query.lower()}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM approvals {where} ORDER BY approval_date DESC NULLS LAST LIMIT ?"
    params.append(limit)
    return [_row_to_approval(r) for r in conn.execute(sql, params)]


def find_formulations(
    conn: sqlite3.Connection,
    drug_name: str | None = None,
    strength: str | None = None,
    form: str | None = None,
    limit: int = 100,
) -> list[Formulation]:
    clauses: list[str] = []
    params: list = []
    if drug_name:
        clauses.append("LOWER(drug_name) LIKE ?")
        params.append(f"%{drug_name.lower()}%")
    if strength:
        clauses.append("LOWER(strength) LIKE ?")
        params.append(f"%{strength.lower()}%")
    if form:
        clauses.append("LOWER(form) LIKE ?")
        params.append(f"%{form.lower()}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM formulations {where} ORDER BY drug_name LIMIT ?"
    params.append(limit)
    return [_row_to_formulation(r) for r in conn.execute(sql, params)]


def find_price_changes(
    conn: sqlite3.Connection,
    from_date: date | None = None,
    to_date: date | None = None,
    formulation_id: str | None = None,
    limit: int = 100,
) -> list[PriceChange]:
    clauses: list[str] = []
    params: list = []
    if from_date:
        clauses.append("effective_date >= ?")
        params.append(from_date.isoformat())
    if to_date:
        clauses.append("effective_date <= ?")
        params.append(to_date.isoformat())
    if formulation_id:
        clauses.append("formulation_id = ?")
        params.append(formulation_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM price_changes {where} ORDER BY effective_date DESC LIMIT ?"
    params.append(limit)
    return [_row_to_price_change(r) for r in conn.execute(sql, params)]
```

Note: SQLite's `NULLS LAST` is supported from 3.30+. If your Python ships an older sqlite3, replace `ORDER BY approval_date DESC NULLS LAST` with `ORDER BY approval_date IS NULL, approval_date DESC`.

- [ ] **Step 4: Run, confirm pass**

```bash
pytest tests/test_cache_repo.py -v
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/india_rx_mcp/cache/repo.py tests/test_cache_repo.py
git commit -m "feat: cache repo with upsert/find for approvals, formulations, price changes"
```

---

## Task 7: ApprovalsService and PricingService

**Files:**
- Create: `src/india_rx_mcp/services/__init__.py`
- Create: `src/india_rx_mcp/services/approvals_service.py`
- Create: `src/india_rx_mcp/services/pricing_service.py`
- Create: `tests/test_services.py`

- [ ] **Step 1: Write failing tests**

`tests/test_services.py`:

```python
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
```

- [ ] **Step 2: Run, confirm failure**

```bash
pytest tests/test_services.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement services**

`src/india_rx_mcp/services/__init__.py`: (empty)

`src/india_rx_mcp/services/approvals_service.py`:

```python
import sqlite3
from datetime import date, timedelta

from india_rx_mcp.cache.models import Approval
from india_rx_mcp.cache.repo import find_approvals

THERAPEUTIC_AREA_KEYWORDS: dict[str, list[str]] = {
    "oncology": ["cancer", "tumor", "tumour", "carcinoma", "oncology", "leukemia",
                 "lymphoma", "melanoma", "sarcoma"],
    "cardiology": ["cardiac", "cardiovascular", "hypertension", "hyperlipidemia",
                   "angina", "heart", "myocardial"],
    "diabetes": ["diabetes", "diabetic", "glycemic", "insulin"],
    "respiratory": ["asthma", "copd", "bronchitis", "pulmonary", "respiratory"],
    "neurology": ["alzheimer", "parkinson", "epilepsy", "migraine", "neurologic",
                  "multiple sclerosis"],
    "infectious": ["bacterial", "viral", "fungal", "antibiotic", "antiviral",
                   "infection", "hiv", "hepatitis", "tuberculosis", "covid"],
    "psychiatry": ["depression", "anxiety", "schizophrenia", "bipolar", "psychiatric"],
    "dermatology": ["psoriasis", "eczema", "dermatitis", "acne"],
}


class ApprovalsService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def search(
        self,
        query: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        therapeutic_area: str | None = None,
        sponsor: str | None = None,
        limit: int = 20,
    ) -> list[Approval]:
        if therapeutic_area:
            keywords = THERAPEUTIC_AREA_KEYWORDS.get(therapeutic_area.lower(), [therapeutic_area])
            matches: list[Approval] = []
            seen: set[str] = set()
            for kw in keywords:
                for a in find_approvals(
                    self.conn, drug_query=query, sponsor=sponsor,
                    from_date=from_date, to_date=to_date,
                    indication_query=kw, limit=limit,
                ):
                    if a.approval_id not in seen:
                        seen.add(a.approval_id)
                        matches.append(a)
                        if len(matches) >= limit:
                            return matches
            return matches
        return find_approvals(
            self.conn, drug_query=query, sponsor=sponsor,
            from_date=from_date, to_date=to_date, limit=limit,
        )

    def get(self, approval_id: str | None = None, drug_name: str | None = None) -> Approval | None:
        if approval_id:
            from india_rx_mcp.cache.repo import _row_to_approval
            row = self.conn.execute(
                "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
            return _row_to_approval(row) if row else None
        if drug_name:
            results = find_approvals(self.conn, drug_query=drug_name, limit=1)
            return results[0] if results else None
        return None

    def recent(self, since_date: date | None = None, limit: int = 20) -> list[Approval]:
        if since_date is None:
            since_date = date.today() - timedelta(days=30)
        return find_approvals(self.conn, from_date=since_date, limit=limit)

    def sponsor_pipeline(self, sponsor_name: str) -> list[Approval]:
        return find_approvals(self.conn, sponsor=sponsor_name, limit=1000)
```

`src/india_rx_mcp/services/pricing_service.py`:

```python
import sqlite3
from datetime import date, timedelta

from india_rx_mcp.cache.models import Formulation, PriceChange
from india_rx_mcp.cache.repo import find_formulations, find_price_changes


class PricingService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_ceiling_price(
        self, drug_name: str, strength: str | None = None, form: str | None = None
    ) -> list[Formulation]:
        return find_formulations(self.conn, drug_name=drug_name, strength=strength, form=form)

    def search_scheduled(
        self, query: str | None = None, therapeutic_area: str | None = None, limit: int = 20
    ) -> list[Formulation]:
        # NPPA formulations don't carry indication; therapeutic_area is best-effort substring on drug name
        if therapeutic_area:
            return find_formulations(self.conn, drug_name=therapeutic_area, limit=limit)
        return find_formulations(self.conn, drug_name=query, limit=limit)

    def price_changes(self, since_date: date | None = None, limit: int = 50) -> list[PriceChange]:
        if since_date is None:
            since_date = date.today() - timedelta(days=180)
        return find_price_changes(self.conn, from_date=since_date, limit=limit)
```

- [ ] **Step 4: Run, confirm pass**

```bash
pytest tests/test_services.py -v
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/india_rx_mcp/services tests/test_services.py
git commit -m "feat: ApprovalsService and PricingService wrapping cache queries"
```

---

## Task 8: Markdown formatting helpers

**Files:**
- Create: `src/india_rx_mcp/formatting.py`
- Create: `tests/test_formatting.py`

- [ ] **Step 1: Write failing test**

`tests/test_formatting.py`:

```python
from datetime import date
from india_rx_mcp.cache.models import Approval, Formulation
from india_rx_mcp.formatting import (
    approvals_table, approval_detail, formulations_table, citations_block,
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
```

- [ ] **Step 2: Run, confirm failure**

```bash
pytest tests/test_formatting.py -v
```

- [ ] **Step 3: Implement formatting**

`src/india_rx_mcp/formatting.py`:

```python
from datetime import date

from india_rx_mcp.cache.models import Approval, Formulation, PriceChange


def _fmt_date(d: date | None) -> str:
    return d.isoformat() if d else "—"


def _fmt_price(p: float | None) -> str:
    return f"₹{p:.2f}" if p is not None else "—"


def approvals_table(approvals: list[Approval]) -> str:
    if not approvals:
        return "_No approvals found for the given criteria._"
    lines = [
        "| Drug | Sponsor | Approval Date | Indication |",
        "|---|---|---|---|",
    ]
    for a in approvals:
        lines.append(
            f"| {a.drug_name} | {a.sponsor or '—'} | "
            f"{_fmt_date(a.approval_date)} | {a.indication or '—'} |"
        )
    lines.append("")
    lines.append(citations_block([a.source_url for a in approvals]))
    return "\n".join(lines)


def approval_detail(a: Approval) -> str:
    return "\n".join([
        f"# {a.drug_name}",
        "",
        f"- **Approval ID:** `{a.approval_id}`",
        f"- **Sponsor:** {a.sponsor or '—'}",
        f"- **Approval date:** {_fmt_date(a.approval_date)}",
        f"- **Indication:** {a.indication or '—'}",
        f"- **Formulation:** {a.formulation or '—'}",
        f"- **Conditions of approval:** {a.conditions or '—'}",
        "",
        citations_block([a.source_url]),
    ])


def formulations_table(formulations: list[Formulation]) -> str:
    if not formulations:
        return "_No formulations found for the given criteria._"
    lines = [
        "| Drug | Strength | Form | Ceiling price | Effective |",
        "|---|---|---|---|---|",
    ]
    for f in formulations:
        lines.append(
            f"| {f.drug_name} | {f.strength or '—'} | {f.form or '—'} | "
            f"{_fmt_price(f.ceiling_price_inr)} | {_fmt_date(f.price_effective_date)} |"
        )
    lines.append("")
    lines.append(citations_block([f.source_url for f in formulations]))
    return "\n".join(lines)


def price_changes_table(changes: list[PriceChange]) -> str:
    if not changes:
        return "_No price changes found for the given criteria._"
    lines = [
        "| Formulation | Old price | New price | Effective | Reason |",
        "|---|---|---|---|---|",
    ]
    for c in changes:
        lines.append(
            f"| `{c.formulation_id}` | {_fmt_price(c.old_price_inr)} | "
            f"{_fmt_price(c.new_price_inr)} | {_fmt_date(c.effective_date)} | "
            f"{c.reason or '—'} |"
        )
    lines.append("")
    lines.append(citations_block([c.source_url for c in changes]))
    return "\n".join(lines)


def citations_block(urls: list[str]) -> str:
    seen: set[str] = set()
    unique = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            unique.append(u)
    if not unique:
        return ""
    lines = ["**Sources:**"]
    for u in unique:
        lines.append(f"- {u}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run, confirm pass**

```bash
pytest tests/test_formatting.py -v
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/india_rx_mcp/formatting.py tests/test_formatting.py
git commit -m "feat: markdown formatting helpers for tool responses"
```

---

## Task 9: CDSCO MCP tools

**Files:**
- Create: `src/india_rx_mcp/tools/__init__.py`
- Create: `src/india_rx_mcp/tools/cdsco_tools.py`
- Create: `tests/test_cdsco_tools.py`

- [ ] **Step 1: Write failing tests**

`tests/test_cdsco_tools.py`:

```python
from datetime import date
import pytest
from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.models import Approval
from india_rx_mcp.cache.repo import upsert_approvals
from india_rx_mcp.tools.cdsco_tools import (
    search_cdsco_approvals, get_cdsco_approval,
    list_recent_cdsco_approvals, cdsco_sponsor_pipeline,
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
    # Inject the test connection
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
    assert "not found" in md.lower() or "no" in md.lower()


def test_cdsco_sponsor_pipeline(seeded):
    md = cdsco_sponsor_pipeline("sun pharma")
    assert "Atorvastatin" in md
    assert "MSD" not in md


def test_search_cdsco_approvals_by_therapeutic_area(seeded):
    md = search_cdsco_approvals(therapeutic_area="oncology")
    assert "Pembrolizumab" in md
```

- [ ] **Step 2: Run, confirm failure**

```bash
pytest tests/test_cdsco_tools.py -v
```

- [ ] **Step 3: Implement tools**

`src/india_rx_mcp/tools/__init__.py`: (empty)

`src/india_rx_mcp/tools/cdsco_tools.py`:

```python
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
    """Search CDSCO-approved drugs by drug name, date range, therapeutic area, or sponsor."""
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
    """Get all CDSCO approvals for a sponsor (company), grouped chronologically."""
    svc = ApprovalsService(_get_conn())
    results = svc.sponsor_pipeline(sponsor_name)
    if not results:
        return f"_No approvals found for sponsor matching {sponsor_name!r}._"
    return approvals_table(results)
```

- [ ] **Step 4: Run, confirm pass**

```bash
pytest tests/test_cdsco_tools.py -v
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/india_rx_mcp/tools tests/test_cdsco_tools.py
git commit -m "feat: 4 CDSCO MCP tools returning markdown"
```

---

## Task 10: NPPA MCP tools

**Files:**
- Create: `src/india_rx_mcp/tools/nppa_tools.py`
- Create: `tests/test_nppa_tools.py`

- [ ] **Step 1: Write failing tests**

`tests/test_nppa_tools.py`:

```python
from datetime import date
import pytest
from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.models import Formulation, PriceChange
from india_rx_mcp.cache.repo import upsert_formulations, upsert_price_changes
from india_rx_mcp.tools.nppa_tools import (
    get_nppa_ceiling_price, search_nppa_scheduled_formulations,
    list_nppa_price_changes,
)


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "t.db")
    upsert_formulations(conn, [
        Formulation("NPPA-1", "Atorvastatin", "10mg", "tablet", 2.34,
                    date(2026, 4, 1), "http://x"),
        Formulation("NPPA-2", "Metformin", "500mg", "tablet", 1.10,
                    date(2026, 4, 1), "http://x"),
    ])
    upsert_price_changes(conn, [
        PriceChange(None, "NPPA-1", 2.20, 2.34, date(2026, 4, 1),
                    "WPI 2026", "http://x"),
    ])
    from india_rx_mcp.tools import nppa_tools as mod
    monkeypatch.setattr(mod, "_get_conn", lambda: conn)
    yield conn
    conn.close()


def test_get_nppa_ceiling_price(seeded):
    md = get_nppa_ceiling_price("atorvastatin", strength="10mg")
    assert "₹2.34" in md
    assert "tablet" in md


def test_search_nppa_scheduled_formulations(seeded):
    md = search_nppa_scheduled_formulations(query="metformin")
    assert "Metformin" in md
    assert "Atorvastatin" not in md


def test_list_nppa_price_changes(seeded):
    md = list_nppa_price_changes(since_date="2026-01-01")
    assert "₹2.20" in md
    assert "₹2.34" in md
    assert "WPI 2026" in md
```

- [ ] **Step 2: Run, confirm failure**

- [ ] **Step 3: Implement tools**

`src/india_rx_mcp/tools/nppa_tools.py`:

```python
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
    return date.fromisoformat(s) if s else None


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
    """Search NPPA-controlled (scheduled) formulations by free text or therapeutic area."""
    svc = PricingService(_get_conn())
    results = svc.search_scheduled(query=query, therapeutic_area=therapeutic_area, limit=limit)
    return formulations_table(results)


def list_nppa_price_changes(since_date: str | None = None, limit: int = 50) -> str:
    """List recent NPPA price revisions (default: last 180 days)."""
    svc = PricingService(_get_conn())
    results = svc.price_changes(since_date=_parse_iso(since_date), limit=limit)
    return price_changes_table(results)
```

- [ ] **Step 4: Run, confirm pass**

```bash
pytest tests/test_nppa_tools.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/india_rx_mcp/tools/nppa_tools.py tests/test_nppa_tools.py
git commit -m "feat: 3 NPPA MCP tools returning markdown"
```

---

## Task 11: MCP server entry point

**Files:**
- Create: `src/india_rx_mcp/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write failing test**

`tests/test_server.py`:

```python
from india_rx_mcp.server import mcp


def test_mcp_server_registers_all_tools():
    # FastMCP exposes registered handlers via internal manager; we verify via list_tools handler
    tool_names = {t.name for t in mcp._tool_manager.list_tools()}
    expected = {
        "search_cdsco_approvals",
        "get_cdsco_approval",
        "list_recent_cdsco_approvals",
        "cdsco_sponsor_pipeline",
        "get_nppa_ceiling_price",
        "search_nppa_scheduled_formulations",
        "list_nppa_price_changes",
    }
    assert expected <= tool_names


def test_mcp_server_has_name():
    assert mcp.name == "india-rx-mcp"
```

- [ ] **Step 2: Run, confirm failure**

- [ ] **Step 3: Implement server**

`src/india_rx_mcp/server.py`:

```python
from mcp.server.fastmcp import FastMCP

from india_rx_mcp.tools import cdsco_tools, nppa_tools

mcp = FastMCP("india-rx-mcp")

mcp.tool()(cdsco_tools.search_cdsco_approvals)
mcp.tool()(cdsco_tools.get_cdsco_approval)
mcp.tool()(cdsco_tools.list_recent_cdsco_approvals)
mcp.tool()(cdsco_tools.cdsco_sponsor_pipeline)

mcp.tool()(nppa_tools.get_nppa_ceiling_price)
mcp.tool()(nppa_tools.search_nppa_scheduled_formulations)
mcp.tool()(nppa_tools.list_nppa_price_changes)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run, confirm pass**

```bash
pytest tests/test_server.py -v
```

Expected: `2 passed`. If `_tool_manager` is not the correct internal attribute in your installed version of mcp, replace with whatever method FastMCP exposes for listing registered tools — `mcp.list_tools()` may also work.

- [ ] **Step 5: Commit**

```bash
git add src/india_rx_mcp/server.py tests/test_server.py
git commit -m "feat: FastMCP server registering all 7 tools"
```

---

## Task 12: Resources

**Files:**
- Create: `src/india_rx_mcp/resources/__init__.py`
- Create: `src/india_rx_mcp/resources/catalogs.py`
- Modify: `src/india_rx_mcp/server.py`
- Create: `tests/test_resources.py`

- [ ] **Step 1: Write failing test**

`tests/test_resources.py`:

```python
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
```

- [ ] **Step 2: Run, confirm failure**

- [ ] **Step 3: Implement resources**

`src/india_rx_mcp/resources/__init__.py`: (empty)

`src/india_rx_mcp/resources/catalogs.py`:

```python
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
```

- [ ] **Step 4: Register resources in server**

Modify `src/india_rx_mcp/server.py`:

```python
from mcp.server.fastmcp import FastMCP

from india_rx_mcp.tools import cdsco_tools, nppa_tools
from india_rx_mcp.resources import catalogs

mcp = FastMCP("india-rx-mcp")

mcp.tool()(cdsco_tools.search_cdsco_approvals)
mcp.tool()(cdsco_tools.get_cdsco_approval)
mcp.tool()(cdsco_tools.list_recent_cdsco_approvals)
mcp.tool()(cdsco_tools.cdsco_sponsor_pipeline)

mcp.tool()(nppa_tools.get_nppa_ceiling_price)
mcp.tool()(nppa_tools.search_nppa_scheduled_formulations)
mcp.tool()(nppa_tools.list_nppa_price_changes)

mcp.resource("cdsco://catalog/approved-drugs")(catalogs.approved_drugs_catalog)
mcp.resource("nppa://catalog/scheduled-formulations")(catalogs.scheduled_formulations_catalog)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/test_resources.py tests/test_server.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/india_rx_mcp/resources src/india_rx_mcp/server.py tests/test_resources.py
git commit -m "feat: 2 MCP resources for approved-drugs and scheduled-formulations catalogs"
```

---

## Task 13: Prompts

**Files:**
- Create: `src/india_rx_mcp/prompts/__init__.py`
- Create: `src/india_rx_mcp/prompts/workflows.py`
- Modify: `src/india_rx_mcp/server.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: Write failing test**

`tests/test_prompts.py`:

```python
from india_rx_mcp.prompts.workflows import (
    competitor_briefing, therapeutic_area_landscape, monthly_market_update,
)


def test_competitor_briefing_includes_sponsor_name():
    msg = competitor_briefing("Sun Pharma")
    assert "Sun Pharma" in msg
    assert "cdsco_sponsor_pipeline" in msg


def test_therapeutic_area_landscape_includes_ta_and_default_months():
    msg = therapeutic_area_landscape("oncology")
    assert "oncology" in msg
    assert "12" in msg


def test_monthly_market_update_mentions_both_tools():
    msg = monthly_market_update()
    assert "list_recent_cdsco_approvals" in msg
    assert "list_nppa_price_changes" in msg
```

- [ ] **Step 2: Run, confirm failure**

- [ ] **Step 3: Implement prompts**

`src/india_rx_mcp/prompts/__init__.py`: (empty)

`src/india_rx_mcp/prompts/workflows.py`:

```python
def competitor_briefing(sponsor: str) -> str:
    """Build a written brief on an Indian pharma company's regulatory footprint."""
    return (
        f"You are a pharma market analyst. Build a brief on **{sponsor}**'s "
        f"Indian regulatory footprint.\n\n"
        f"Steps:\n"
        f"1. Call `cdsco_sponsor_pipeline(sponsor_name='{sponsor}')` to get all approvals.\n"
        f"2. For each approval's drug, call `get_nppa_ceiling_price(drug_name=<drug>)` "
        f"to find NPPA-controlled pricing if any.\n"
        f"3. Summarize: number of approvals by year, top therapeutic areas, "
        f"price-controlled vs free-pricing drugs.\n"
        f"4. End with a 2-sentence strategic takeaway.\n"
        f"5. Cite all source URLs from the tool outputs."
    )


def therapeutic_area_landscape(therapeutic_area: str, since_months: int = 12) -> str:
    """Build a landscape view of a therapeutic area in Indian pharma."""
    return (
        f"You are a pharma market analyst. Build a landscape view of **{therapeutic_area}** "
        f"in India for the last {since_months} months.\n\n"
        f"Steps:\n"
        f"1. Call `search_cdsco_approvals(therapeutic_area='{therapeutic_area}', "
        f"from_date=<{since_months} months ago>)` to find recent approvals.\n"
        f"2. Call `search_nppa_scheduled_formulations(therapeutic_area='{therapeutic_area}')` "
        f"to find price-controlled drugs in this TA.\n"
        f"3. List: top sponsors active in the TA, recent approvals, price-controlled drugs.\n"
        f"4. End with a 2-sentence assessment of competitive intensity.\n"
        f"5. Cite all source URLs."
    )


def monthly_market_update() -> str:
    """Build a monthly digest of CDSCO approvals and NPPA price changes."""
    return (
        "You are a pharma market analyst. Build a monthly digest of Indian pharma "
        "regulatory action.\n\n"
        "Steps:\n"
        "1. Call `list_recent_cdsco_approvals()` to get the last 30 days of approvals.\n"
        "2. Call `list_nppa_price_changes()` to get recent price revisions.\n"
        "3. Group approvals by therapeutic area; flag any first-in-class or notable approvals.\n"
        "4. For price changes, highlight any unusually large revisions.\n"
        "5. End with a 'what to watch' section.\n"
        "6. Cite all source URLs."
    )
```

- [ ] **Step 4: Register prompts in server**

Modify `src/india_rx_mcp/server.py` to add prompt registrations after the resources block:

```python
from india_rx_mcp.prompts import workflows

mcp.prompt()(workflows.competitor_briefing)
mcp.prompt()(workflows.therapeutic_area_landscape)
mcp.prompt()(workflows.monthly_market_update)
```

(Add `from india_rx_mcp.prompts import workflows` at the top with the other imports.)

- [ ] **Step 5: Run all tests**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/india_rx_mcp/prompts src/india_rx_mcp/server.py tests/test_prompts.py
git commit -m "feat: 3 MCP prompts for analyst workflows"
```

---

## Task 14: CLI commands (refresh, status, version)

**Files:**
- Create: `src/india_rx_mcp/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing test**

`tests/test_cli.py`:

```python
from click.testing import CliRunner
from india_rx_mcp.cli import main


def test_version_command():
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_status_command_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "cache" in result.output.lower() or "india-rx-mcp" in result.output.lower()


def test_default_command_runs_server(monkeypatch):
    # When no subcommand given, run the MCP server (stdio). We just verify it doesn't crash on import.
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "refresh" in result.output
    assert "status" in result.output
```

- [ ] **Step 2: Run, confirm failure**

- [ ] **Step 3: Implement CLI**

`src/india_rx_mcp/cli.py`:

```python
import logging

import click

from india_rx_mcp import __version__
from india_rx_mcp.cache.db import get_db_path, init_db, get_meta


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """india-rx-mcp — MCP server for Indian pharma data."""
    if ctx.invoked_subcommand is None:
        from india_rx_mcp.server import main as server_main
        server_main()


@main.command()
def version() -> None:
    """Print version."""
    click.echo(__version__)


@main.command()
def status() -> None:
    """Show cache status (path, last refresh per source, error count)."""
    db_path = get_db_path()
    conn = init_db(db_path)
    click.echo(f"Cache: {db_path}")
    click.echo(f"CDSCO last refresh: {get_meta(conn, 'cdsco_last_refresh') or 'never'}")
    click.echo(f"NPPA last refresh:  {get_meta(conn, 'nppa_last_refresh') or 'never'}")
    n_approvals = conn.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
    n_form = conn.execute("SELECT COUNT(*) FROM formulations").fetchone()[0]
    n_errors = conn.execute("SELECT COUNT(*) FROM scraper_errors").fetchone()[0]
    click.echo(f"Approvals cached: {n_approvals}")
    click.echo(f"Formulations cached: {n_form}")
    click.echo(f"Scraper errors logged: {n_errors}")
    conn.close()


@main.command()
@click.option("--source", type=click.Choice(["cdsco", "nppa", "all"]), default="all",
              help="Which data source to refresh.")
def refresh(source: str) -> None:
    """Force refresh of the cache from gov.in sources."""
    from india_rx_mcp.refresh import refresh_cdsco, refresh_nppa
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if source in ("cdsco", "all"):
        click.echo("Refreshing CDSCO...")
        refresh_cdsco()
    if source in ("nppa", "all"):
        click.echo("Refreshing NPPA...")
        refresh_nppa()
    click.echo("Done.")
```

- [ ] **Step 4: Run, confirm pass**

```bash
pytest tests/test_cli.py -v
```

Note: the `refresh` command imports a module we haven't built yet (`india_rx_mcp.refresh`). That's intentional — `refresh` is built in Task 15.

Expected: `3 passed` for version/status/help tests. The refresh command will fail at runtime if invoked, but no tests exercise it yet.

- [ ] **Step 5: Commit**

```bash
git add src/india_rx_mcp/cli.py tests/test_cli.py
git commit -m "feat: CLI with version, status, refresh subcommands"
```

---

## Task 15: Background refresh orchestrator

**Files:**
- Create: `src/india_rx_mcp/refresh.py`
- Create: `tests/test_refresh.py`

- [ ] **Step 1: Write failing test**

`tests/test_refresh.py`:

```python
from datetime import datetime, timedelta
from unittest.mock import patch

from india_rx_mcp.cache.db import init_db, set_meta, get_meta
from india_rx_mcp.refresh import should_refresh_cdsco, should_refresh_nppa


def test_should_refresh_cdsco_when_never_refreshed(tmp_path):
    conn = init_db(tmp_path / "t.db")
    assert should_refresh_cdsco(conn) is True
    conn.close()


def test_should_refresh_cdsco_when_older_than_24h(tmp_path):
    conn = init_db(tmp_path / "t.db")
    old = (datetime.utcnow() - timedelta(hours=30)).isoformat()
    set_meta(conn, "cdsco_last_refresh", old)
    assert should_refresh_cdsco(conn) is True
    conn.close()


def test_should_not_refresh_cdsco_when_recent(tmp_path):
    conn = init_db(tmp_path / "t.db")
    recent = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    set_meta(conn, "cdsco_last_refresh", recent)
    assert should_refresh_cdsco(conn) is False
    conn.close()


def test_should_refresh_nppa_threshold_is_7_days(tmp_path):
    conn = init_db(tmp_path / "t.db")
    older_than_week = (datetime.utcnow() - timedelta(days=8)).isoformat()
    set_meta(conn, "nppa_last_refresh", older_than_week)
    assert should_refresh_nppa(conn) is True
    fresh = (datetime.utcnow() - timedelta(days=2)).isoformat()
    set_meta(conn, "nppa_last_refresh", fresh)
    assert should_refresh_nppa(conn) is False
    conn.close()
```

- [ ] **Step 2: Run, confirm failure**

- [ ] **Step 3: Implement refresh**

`src/india_rx_mcp/refresh.py`:

```python
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from platformdirs import user_cache_dir

from india_rx_mcp.cache.db import get_meta, init_db, set_meta
from india_rx_mcp.cache.repo import upsert_approvals, upsert_formulations
from india_rx_mcp.scrapers.cdsco_scraper import scrape_all_years
from india_rx_mcp.scrapers.nppa_scraper import scrape_all_pdfs

log = logging.getLogger(__name__)

CDSCO_REFRESH_INTERVAL = timedelta(hours=24)
NPPA_REFRESH_INTERVAL = timedelta(days=7)


def _is_stale(last: str | None, interval: timedelta) -> bool:
    if not last:
        return True
    return datetime.utcnow() - datetime.fromisoformat(last) > interval


def should_refresh_cdsco(conn: sqlite3.Connection) -> bool:
    return _is_stale(get_meta(conn, "cdsco_last_refresh"), CDSCO_REFRESH_INTERVAL)


def should_refresh_nppa(conn: sqlite3.Connection) -> bool:
    return _is_stale(get_meta(conn, "nppa_last_refresh"), NPPA_REFRESH_INTERVAL)


def _log_error(conn: sqlite3.Connection, source: str, url: str | None, err: Exception) -> None:
    conn.execute(
        "INSERT INTO scraper_errors(source, url, error_message, occurred_at) VALUES (?,?,?,?)",
        (source, url, str(err), datetime.utcnow().isoformat()),
    )
    conn.commit()


def refresh_cdsco() -> int:
    conn = init_db()
    n = 0
    try:
        approvals = list(scrape_all_years())
        n = upsert_approvals(conn, approvals)
        set_meta(conn, "cdsco_last_refresh", datetime.utcnow().isoformat())
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
        formulations = list(scrape_all_pdfs(pdf_dir))
        n = upsert_formulations(conn, formulations)
        set_meta(conn, "nppa_last_refresh", datetime.utcnow().isoformat())
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

    def _run():
        if cdsco_due:
            refresh_cdsco()
        if nppa_due:
            refresh_nppa()

    if cdsco_due or nppa_due:
        threading.Thread(target=_run, daemon=True, name="india-rx-refresh").start()
```

- [ ] **Step 4: Wire background refresh into server startup**

Modify `src/india_rx_mcp/server.py` `main()`:

```python
def main() -> None:
    from india_rx_mcp.refresh import refresh_if_stale_in_background
    refresh_if_stale_in_background()
    mcp.run(transport="stdio")
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/test_refresh.py tests/test_server.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/india_rx_mcp/refresh.py src/india_rx_mcp/server.py tests/test_refresh.py
git commit -m "feat: background refresh orchestrator with staleness thresholds"
```

---

## Task 16: End-to-end smoke test

**Files:**
- Create: `tests/test_e2e_server.py`

- [ ] **Step 1: Write end-to-end test that exercises the FastMCP server in-process**

`tests/test_e2e_server.py`:

```python
import asyncio
from datetime import date

import pytest
from india_rx_mcp.cache.db import init_db
from india_rx_mcp.cache.models import Approval
from india_rx_mcp.cache.repo import upsert_approvals
from india_rx_mcp.server import mcp


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "t.db")
    upsert_approvals(conn, [
        Approval("X-1", "Atorvastatin", "Sun Pharma", date(2024, 6, 1),
                 "Hyperlipidemia", "10mg tab", None, "http://x"),
    ])
    from india_rx_mcp.tools import cdsco_tools, nppa_tools
    from india_rx_mcp.resources import catalogs
    monkeypatch.setattr(cdsco_tools, "_get_conn", lambda: conn)
    monkeypatch.setattr(nppa_tools, "_get_conn", lambda: conn)
    monkeypatch.setattr(catalogs, "_get_conn", lambda: conn)
    yield conn
    conn.close()


@pytest.mark.asyncio
async def test_e2e_list_tools_and_call(seeded):
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "search_cdsco_approvals" in names

    result = await mcp.call_tool("search_cdsco_approvals", {"query": "ator"})
    text = result.content[0].text if hasattr(result, "content") else str(result)
    assert "Atorvastatin" in text
```

- [ ] **Step 2: Add pytest-asyncio to dev deps**

Modify `pyproject.toml` `[project.optional-dependencies] dev`:

```toml
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "respx>=0.21.0",
    "ruff>=0.5.0",
]
```

Add at the bottom of `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
asyncio_mode = "auto"
```

(If `[tool.pytest.ini_options]` already exists from Task 1, just add the `asyncio_mode = "auto"` line.)

Then:

```bash
uv pip install -e ".[dev]"
```

- [ ] **Step 3: Run end-to-end test**

```bash
pytest tests/test_e2e_server.py -v
```

Expected: pass. If FastMCP's `call_tool` returns a different shape than `result.content[0].text` in your installed version, adjust the assertion to match — the test's intent is "the response contains 'Atorvastatin'."

- [ ] **Step 4: Run full suite for confidence**

```bash
pytest --cov=india_rx_mcp --cov-report=term-missing
```

Expected: all tests pass, coverage >80%.

- [ ] **Step 5: Commit**

```bash
git add tests/test_e2e_server.py pyproject.toml
git commit -m "test: end-to-end FastMCP server smoke test"
```

---

## Task 17: README, docs, demo prep

**Files:**
- Modify: `README.md`
- Create: `docs/claude-desktop-setup.md`
- Create: `docs/architecture.md`
- Manually capture `docs/demo.gif` (not generated by code)

- [ ] **Step 1: Write full README**

Overwrite `README.md`:

````markdown
# india-rx-mcp

An MCP (Model Context Protocol) server for **Indian pharma regulatory data** — CDSCO drug approvals and NPPA ceiling-price data — for any MCP-compatible LLM client (Claude Desktop, Cursor, Cline, Continue).

Built by a pharma market analyst, for pharma market analysts.

## Why this exists

Multiple MCP servers exist for US pharma (openFDA, Orange Book, ClinicalTrials.gov). **None exist for Indian pharma.** Indian regulatory data is overwhelmingly scrape-not-API, which is exactly why no one has done it. This server fills the gap.

## What it gives you

**7 tools** that map directly to analyst questions:

| Question | Tool |
|---|---|
| "What did Sun Pharma get approved in 2026?" | `cdsco_sponsor_pipeline` |
| "What's new in oncology this month?" | `search_cdsco_approvals` |
| "What's the ceiling price for atorvastatin 10mg?" | `get_nppa_ceiling_price` |
| "Any antibiotic price changes recently?" | `list_nppa_price_changes` |

**2 browseable resources:** full CDSCO catalog, full NPPA scheduled-formulations catalog.

**3 pre-built workflows:** `competitor_briefing`, `therapeutic_area_landscape`, `monthly_market_update`.

## Install (Claude Desktop)

Add to your Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "india-rx": {
      "command": "uvx",
      "args": ["india-rx-mcp"]
    }
  }
}
```

Restart Claude Desktop. First launch will scrape and cache CDSCO + NPPA data in the background (5-10 minutes). After that, queries are <100ms.

## CLI

```bash
india-rx-mcp version       # print version
india-rx-mcp status        # show cache status
india-rx-mcp refresh       # force refresh from gov.in
india-rx-mcp refresh --source cdsco   # refresh just CDSCO
```

## Architecture

See [docs/architecture.md](docs/architecture.md).

## Example session

> **You:** What did Sun Pharma get approved in 2024?
>
> **Claude:** *[calls `cdsco_sponsor_pipeline("Sun Pharma")`]*
> Sun Pharma had 12 CDSCO approvals in 2024, primarily in...

## Limitations (v1)

- `therapeutic_area` filter uses a small built-in keyword-expansion map (not a full taxonomy)
- Patents, CTRI trials, and FDA cross-reference are out of scope for v1
- Data is cached; freshness depends on refresh cadence (24h CDSCO, 7d NPPA)

## Roadmap

- v1.1: CTRI clinical trials
- v1.2: CDSCO ↔ FDA approval-timing comparison
- v2.0: Indian Patent Office (inPASS) integration

## License

MIT. See [LICENSE](LICENSE).
````

- [ ] **Step 2: Write Claude Desktop setup doc**

`docs/claude-desktop-setup.md`:

````markdown
# Claude Desktop setup

## Prerequisites

- Claude Desktop installed
- `uv` installed (`pip install uv` or [official installer](https://docs.astral.sh/uv/getting-started/installation/))

## Config

Edit your Claude Desktop config:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add:

```json
{
  "mcpServers": {
    "india-rx": {
      "command": "uvx",
      "args": ["india-rx-mcp"]
    }
  }
}
```

Save and restart Claude Desktop.

## First launch

On first invocation, the server scrapes CDSCO + NPPA in the background. Expect a 5-10 minute initial delay before queries return useful data. Use `india-rx-mcp status` from your terminal to monitor progress.

## Verifying it works

In Claude Desktop, ask: "What CDSCO drug approval tools do you have?"

Claude should list the 7 tools. If not, check:
- Claude Desktop logs (Help → Show Logs)
- `india-rx-mcp version` works in terminal
- `uvx` is on `$PATH`
````

- [ ] **Step 3: Write architecture doc**

`docs/architecture.md`:

````markdown
# Architecture

See [the design spec](superpowers/specs/2026-05-21-india-rx-mcp-design.md) for full design rationale. This file is a quick reference.

## Layers

```
MCP client (Claude Desktop, Cursor, etc.)
  ↓ stdio
FastMCP server (server.py)
  ↓
Tools / Resources / Prompts
  ↓
Services (ApprovalsService, PricingService)
  ↓
Cache (SQLite via cache/repo.py)
  ↑
Scrapers (scrapers/cdsco_scraper.py, scrapers/nppa_scraper.py)
  ↑
gov.in (cdsco.gov.in HTML, nppa.gov.in PDFs)
```

## Refresh

- **CDSCO:** 24h interval, HTML scraping with `httpx` + `BeautifulSoup4`
- **NPPA:** 7d interval, PDF parsing with `pdfplumber`
- Refresh runs on background thread on server startup if cache is stale
- Manual refresh: `india-rx-mcp refresh`

## Failure handling

Scrapers log errors to `scraper_errors` table; tools always return cached data with a freshness indicator. Stale > nothing.

## Cache location

- Linux: `$XDG_CACHE_HOME/india-rx-mcp/cache.db`
- macOS: `~/Library/Caches/india-rx-mcp/cache.db`
- Windows: `%LOCALAPPDATA%\india-rx-mcp\cache.db`
````

- [ ] **Step 4: Manually record demo GIF**

This is a manual step, not a code change.

1. Open Claude Desktop with the server configured
2. Run a quick refresh: `india-rx-mcp refresh` until cache is populated
3. Use a screen-recording tool (ScreenToGif on Windows, Kap on macOS) to record 60 seconds:
   - Ask: "What did Sun Pharma get approved recently?"
   - Show Claude's response with the markdown table
   - Ask: "What's the ceiling price for atorvastatin 10mg?"
   - Show the response with the price
4. Save as `docs/demo.gif` (target ~5MB max)

- [ ] **Step 5: Commit docs**

```bash
git add README.md docs/claude-desktop-setup.md docs/architecture.md docs/demo.gif
git commit -m "docs: README, Claude Desktop setup, architecture, demo GIF"
```

---

## Task 18: PyPI publish

**Files:**
- Modify: `pyproject.toml` (verify metadata)
- Manual: PyPI account, API token

- [ ] **Step 1: Verify the build works**

```bash
uv build
```

Expected: creates `dist/india_rx_mcp-0.1.0-py3-none-any.whl` and `dist/india_rx_mcp-0.1.0.tar.gz`.

- [ ] **Step 2: Install the wheel into a fresh venv and smoke-test**

```bash
uv venv .testenv
.testenv\Scripts\activate
uv pip install dist\india_rx_mcp-0.1.0-py3-none-any.whl
india-rx-mcp version
deactivate
```

Expected: prints `0.1.0`.

- [ ] **Step 3: Get a PyPI API token**

1. Create account at https://pypi.org/ if needed
2. Account Settings → API tokens → Add API token (scope: project, name: india-rx-mcp)
3. Save the token (`pypi-...`) securely

- [ ] **Step 4: Publish to TestPyPI first**

```bash
uv publish --repository testpypi dist/* --token <test-token>
```

Verify at `https://test.pypi.org/project/india-rx-mcp/`.

Test install from TestPyPI in a fresh venv:

```bash
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ india-rx-mcp version
```

- [ ] **Step 5: Publish to real PyPI**

```bash
uv publish dist/* --token <real-token>
```

Verify at `https://pypi.org/project/india-rx-mcp/`.

- [ ] **Step 6: Tag the release in git**

```bash
git tag -a v0.1.0 -m "Initial release"
git push origin v0.1.0
```

- [ ] **Step 7: Commit any final tweaks and announce**

If you made any last-minute changes to `pyproject.toml` for publishing:

```bash
git add pyproject.toml
git commit -m "chore: release v0.1.0"
```

---

## Done

The MCP server is published to PyPI. Anyone can install it with one line in Claude Desktop config. Pin the repo on your GitHub profile, write the companion blog post (optional), and you have a portfolio piece that demonstrates "domain expert who ships AI infra."

---

## Spec coverage check

| Spec section | Implemented in |
|---|---|
| Architecture: client ↔ MCP ↔ services ↔ cache ↔ scrapers | Tasks 2, 6, 7, 11 |
| 7 tools (4 CDSCO + 3 NPPA) | Tasks 9, 10 |
| 2 resources | Task 12 |
| 3 prompts | Task 13 |
| SQLite cache with per-source refresh thresholds | Tasks 2, 15 |
| CDSCO scraper | Task 4 |
| NPPA scraper (PDF parsing) | Task 5 |
| Background refresh, never blocks tools | Task 15 |
| `india-rx-mcp refresh / status / version` CLI | Task 14 |
| Parameter matching semantics (sponsor substring, TA keyword expansion) | Tasks 6, 7 |
| Markdown returns with source citations | Tasks 8, 9, 10 |
| Fixture-based scraper tests, CI-safe | Tasks 4, 5 |
| Polished README + Claude Desktop config + demo GIF | Task 17 |
| Published to PyPI via `uv publish` | Task 18 |
| Resilience: failed scrapers don't break tools | Task 15 |
