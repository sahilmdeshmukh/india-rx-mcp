"""CDSCO 'Approved New Drugs' scraper.

The CDSCO index page lists yearly PDFs. Each PDF has a 4-column table:
  S.No | Name of drug | Indication | Date of issue

Known v1 limitations (by design):
- Approval.sponsor is always None  — not in the yearly PDFs
- Approval.formulation is always None — embedded in drug_name, not extracted
- Approval.conditions is always None — not in the yearly PDFs
"""

import hashlib
import logging
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from india_rx_mcp.cache.models import Approval

log = logging.getLogger(__name__)

BASE = "https://cdsco.gov.in"
APPROVED_INDEX = f"{BASE}/opencms/opencms/en/Approval_new/Approved-New-Drugs/"
USER_AGENT = "india-rx-mcp/0.1.0 (contact: sahildeshmukh.pune@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}
RATE_LIMIT_SECONDS = 1.0

# Unicode Private Use Area bullet that PDF renders as a list marker (U+F0B7)
PUA_BULLET = ""

_YEAR_RE = re.compile(r"\b(20\d{2})\b")

# Date formats to try in order
_DATE_FMTS = [
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d %b %Y",
    "%d %B %Y",
]


@dataclass
class CdscoYearPdf:
    year: int
    title: str
    release_date: str  # raw text like "2024-Dec-27"
    pdf_url: str  # absolute URL (JSP or direct PDF)


def _client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=60.0, follow_redirects=True)


def parse_index_html(html: str, base_url: str = BASE) -> list[CdscoYearPdf]:
    """Parse the CDSCO 'Approved New Drugs' index page.

    Returns one CdscoYearPdf per yearly PDF link found in the table.
    The pdf_url is the raw href from the page (JSP URL, not yet resolved).
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[CdscoYearPdf] = []

    table = soup.find("table", id="example") or soup.find("table")
    if not table:
        return out

    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        # Expect at least 4 columns; actual fixture has 5 (S.no, Title, Release Date, Download, Size)
        if len(tds) < 4:
            continue

        title = tds[1].get_text(" ", strip=True)
        release_date = tds[2].get_text(" ", strip=True)

        # The download link is in column 3 (0-indexed)
        link = tds[3].find("a")
        if not link or not link.get("href"):
            continue

        href = link["href"]
        if href.startswith("/"):
            href = base_url + href

        m = _YEAR_RE.search(title)
        if not m:
            continue
        year = int(m.group(1))

        out.append(CdscoYearPdf(year=year, title=title, release_date=release_date, pdf_url=href))

    return out


def resolve_pdf_url(jsp_url: str) -> str:
    """Resolve a CDSCO JSP download URL to the actual PDF URL.

    The JSP endpoint returns a tiny HTML page containing an iframe whose src
    attribute is the real PDF path.  One HTTP hop.
    """
    with _client() as c:
        r = c.get(jsp_url)
        r.raise_for_status()

    m = re.search(r"src=['\"]([^'\"]+\.pdf)['\"]", r.text, re.IGNORECASE)
    if not m:
        # Some endpoints might already redirect to the PDF directly
        return jsp_url

    src = m.group(1)
    if src.startswith("/"):
        return BASE + src
    return src


def _make_approval_id(drug_name: str, approval_date: date | None, year: int) -> str:
    raw = f"{drug_name}|{approval_date.isoformat() if approval_date else ''}|{year}"
    return "CDSCO-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _parse_date(text: str) -> date | None:
    """Try to parse a date string in the many formats CDSCO uses.

    Examples seen in the wild:
      "19-01 2024"  →  normalised to "19-01-2024"
      "02-02-2024"
      "21-03-2024"
      "31.05.2024"
      "08-05-2024"
    """
    if not text:
        return None
    text = text.strip()

    # Normalise "19-01 2024" (space instead of dash before year)
    text = re.sub(r"(\d{2}-\d{2})\s+(\d{4})", r"\1-\2", text)

    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_text(s: str | None) -> str | None:
    """Clean extracted PDF cell text.

    - Replace PUA bullet (U+F0B7) with "- "
    - Collapse whitespace (including newlines) to single spaces
    - Strip leading/trailing whitespace
    """
    if not s:
        return None
    # Replace the PUA bullet character with a plain dash bullet
    s = s.replace(PUA_BULLET, "- ")
    # Collapse all whitespace runs (newlines, tabs, multiple spaces) to a single space
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def _is_continuation_row(row: list) -> bool:
    """Return True if this row is a cross-page continuation of the previous approval.

    Continuation rows have None (or empty) in the S.No column (index 0) and the
    Date column (index 3), but may have text in the Indication column (index 2).
    """
    sno = (row[0] or "").strip()
    date_cell = (row[3] or "").strip() if len(row) > 3 else ""
    return not sno and not date_cell


def parse_cdsco_pdf(path: Path, year: int, source_url: str) -> list[Approval]:
    """Open a yearly CDSCO PDF and extract Approval records from its tables.

    Handles:
    - Header row on page 1; continuation pages with no header
    - Cross-page row continuation (indication text split across pages)
    - PUA bullet normalisation
    - Mixed date formats
    """
    approvals: list[Approval] = []
    seen_ids: set[str] = set()

    # Buffer for the last incomplete approval (cross-page continuation)
    pending: dict | None = None

    def _flush_pending() -> None:
        """Finalise and append the pending approval if one exists."""
        if pending is None:
            return
        drug = pending["drug"]
        approval_date = pending["approval_date"]
        indication = pending["indication"]

        aid = _make_approval_id(drug, approval_date, year)
        if aid not in seen_ids:
            seen_ids.add(aid)
            approvals.append(
                Approval(
                    approval_id=aid,
                    drug_name=drug,
                    sponsor=None,
                    approval_date=approval_date,
                    indication=indication,
                    formulation=None,
                    conditions=None,
                    source_url=source_url,
                )
            )

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table:
                    continue

                # Determine if the first row is a header
                first_row = table[0]
                first_row_text = " ".join((c or "").lower() for c in first_row)
                has_header = "drug" in first_row_text or "name" in first_row_text or "s.no" in first_row_text

                data_rows = table[1:] if has_header else table

                for row in data_rows:
                    if not row or len(row) < 4:
                        continue

                    if _is_continuation_row(row):
                        # Append the extra indication text to the pending approval
                        extra_indication = _normalize_text(row[2] or "")
                        if pending is not None and extra_indication:
                            existing = pending["indication"] or ""
                            pending["indication"] = (existing + " " + extra_indication).strip()
                        # Skip flushing — more rows may follow for same entry
                        continue

                    # This is a new drug row — flush any pending entry first
                    _flush_pending()
                    pending = None

                    drug_raw = row[1] or ""
                    indication_raw = row[2] or ""
                    date_raw = (row[3] or "").strip()

                    drug = _normalize_text(drug_raw)
                    if not drug:
                        continue

                    indication = _normalize_text(indication_raw)
                    approval_date = _parse_date(date_raw)

                    pending = {
                        "drug": drug,
                        "indication": indication,
                        "approval_date": approval_date,
                    }

        # Flush the last pending entry after all pages
        _flush_pending()

    return approvals


# ---------------------------------------------------------------------------
# Live-fetch helpers (require network; not used in unit tests)
# ---------------------------------------------------------------------------


def list_year_pdfs() -> list[CdscoYearPdf]:
    """Fetch the CDSCO index page and return unresolved yearly PDF entries."""
    with _client() as c:
        r = c.get(APPROVED_INDEX)
        r.raise_for_status()
    time.sleep(RATE_LIMIT_SECONDS)
    return parse_index_html(r.text)


def scrape_year(entry: CdscoYearPdf, dest_dir: Path) -> list[Approval]:
    """Download a single year's PDF and extract Approval records."""
    pdf_url = entry.pdf_url
    if "download_file_division.jsp" in pdf_url:
        pdf_url = resolve_pdf_url(pdf_url)
        time.sleep(RATE_LIMIT_SECONDS)

    dest = dest_dir / f"cdsco_{entry.year}.pdf"
    with _client() as c:
        r = c.get(pdf_url)
        r.raise_for_status()
    dest.write_bytes(r.content)
    time.sleep(RATE_LIMIT_SECONDS)
    return parse_cdsco_pdf(dest, year=entry.year, source_url=pdf_url)


def scrape_all_years(cache_dir: Path) -> Iterator[Approval]:
    """Scrape all years from the CDSCO index, caching PDFs locally."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for entry in list_year_pdfs():
        try:
            yield from scrape_year(entry, cache_dir)
        except Exception:
            log.exception("Failed to scrape year %d", entry.year)
