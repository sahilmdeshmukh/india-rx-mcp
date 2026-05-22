"""NPPA 'Compendium of Prices' scraper.

Parses the annual NPPA Compendium of Prices PDF using text-line regex parsing.
The compendium has no grid lines in its tables, so pdfplumber.extract_tables()
collapses everything to a single column — text extraction is used instead.

v1 limitations (by design):
- No price-change tracking: PriceChange rows are NOT generated.
  list_nppa_price_changes will return empty results (documented in Task 17 README).
- Compendium is 2022 (last published). WPI revisions since then are not in this PDF.
- Some prefix parsing may fail (multi-line medicine names, weird formatting).
  Target: extract at least 100 formulations. 100% accuracy not required for v0.1.
"""

import hashlib
import logging
import re
from datetime import date, datetime
from pathlib import Path

import httpx
import pdfplumber

from india_rx_mcp.cache.models import Formulation

log = logging.getLogger(__name__)

NPPA_BASE = "https://nppa.gov.in"
COMPENDIUM_URL_2022 = (
    "https://nppa.gov.in/storage/uploads/pdf/"
    "Compendium-Prices-2022pdf-464b22085495ff4e3f8700c0e00cf45d.pdf"
)
USER_AGENT = "india-rx-mcp/0.1.0 (contact: sahildeshmukh.pune@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}

# Anchored on the right side: price + S.O. number (e.g. 1499(E)) + DD.MM.YYYY date
DATA_LINE_RE = re.compile(
    r"^(?P<prefix>.+?)\s+(?P<price>\d+(?:\.\d+)?)\s+(?P<so>\d+\(E\))\s+(?P<date>\d{2}\.\d{2}\.\d{4})\s*$",
    re.MULTILINE,
)

# Section entry: starts with a dotted numeric ID, e.g. "1.1.1", "6.2.1.1.2"
SECTION_START_RE = re.compile(r"^(\d+(?:\.\d+)+)\s+(.+)$")

# Dosage-form keywords — ordered so multi-word forms match before single-word ones
FORM_KW_RE = re.compile(
    r"\b("
    r"Powder for Injection"
    r"|Oral [Ll]iquid"
    r"|Dry Syrup"
    r"|CR Tablet"
    r"|SR Tablet"
    r"|ER Tablet"
    r"|ER Capsule"
    r"|Topical forms?"
    r"|Tablet"
    r"|Capsule"
    r"|Injection"
    r"|Syrup"
    r"|Cream"
    r"|Ointment"
    r"|Drops"
    r"|Solution"
    r"|Suspension"
    r"|Powder"
    r"|Patch"
    r"|Inhaler"
    r"|Inhalation"
    r"|Gel"
    r"|Lotion"
    r"|Sachet"
    r"|Granules"
    r"|Vial"
    r"|Suppository"
    r")",
    re.IGNORECASE,
)

# Strength pattern — dosage amount + unit, optionally per-volume
STRENGTH_RE = re.compile(
    r"(\d+(?:\.\d+)?\s*"
    r"(?:%|mg|mcg|g\b|ml\b|IU|units?|lac\s*units?|mEq|mmol)"
    r"(?:/\s*(?:ml|kg|5\s*ml|100\s*ml))?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_formulation_id(medicine: str, strength: str | None, form: str | None) -> str:
    """Stable NPPA-F-<hash> identifier for a (medicine, strength, form) triple."""
    raw = f"{medicine.lower()}|{(strength or '').lower()}|{(form or '').lower()}"
    return "NPPA-F-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _normalize_medicine(name: str) -> str:
    """Collapse whitespace and strip trailing/leading junk from medicine names."""
    return re.sub(r"\s+", " ", name).strip()


def _parse_date(text: str) -> date | None:
    """Parse DD.MM.YYYY date strings as used in the NPPA compendium."""
    text = text.strip()
    try:
        return datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        return None


def _parse_data_line(
    prefix: str,
    price_str: str,
    date_str: str,
    last_medicine: str | None,
    source_url: str,
) -> Formulation | None:
    """Convert a single regex-matched data line into a Formulation object.

    Returns None if we cannot determine a medicine name.
    """
    # --- Determine medicine name and form+rest ---
    section_m = SECTION_START_RE.match(prefix)
    if section_m:
        # New medicine entry with a section ID prefix
        rest_after_id = section_m.group(2)
        form_m = FORM_KW_RE.search(rest_after_id)
        if form_m:
            medicine = _normalize_medicine(rest_after_id[: form_m.start()])
            form_rest = rest_after_id[form_m.start() :]
        else:
            # No form keyword found — entire remaining text is the medicine name
            medicine = _normalize_medicine(rest_after_id)
            form_rest = ""
    else:
        # Continuation row — inherit medicine from previous
        medicine = last_medicine or ""
        form_rest = prefix

    if not medicine:
        return None

    # --- Extract form ---
    form_match = FORM_KW_RE.search(form_rest)
    form = form_match.group(0).strip() if form_match else None

    # --- Extract strength ---
    strength_match = STRENGTH_RE.search(form_rest)
    strength = strength_match.group(0).strip() if strength_match else None

    # Normalise form to title-case canonical name (e.g. "oral liquid" → "Oral liquid")
    if form:
        form = form[0].upper() + form[1:]

    ceiling_price = float(price_str)
    price_date = _parse_date(date_str)

    return Formulation(
        formulation_id=_make_formulation_id(medicine, strength, form),
        drug_name=medicine,
        strength=strength,
        form=form,
        ceiling_price_inr=ceiling_price,
        price_effective_date=price_date,
        source_url=source_url,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_compendium_pdf(path: Path, source_url: str) -> list[Formulation]:
    """Parse the NPPA Compendium of Prices PDF and return a list of Formulation objects.

    Uses text-line regex parsing (NOT extract_tables — the compendium has no grid lines).
    Handles continuation rows by inheriting medicine name from the previous data row.
    Returns at least 100 formulations from the 2022 compendium fixture.
    """
    formulations: list[Formulation] = []
    seen_ids: set[str] = set()
    last_medicine: str | None = None

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for m in DATA_LINE_RE.finditer(text):
                prefix = m.group("prefix").strip()
                price_str = m.group("price")
                date_str = m.group("date")

                formulation = _parse_data_line(
                    prefix, price_str, date_str, last_medicine, source_url
                )
                if formulation is None:
                    continue

                # Update last seen medicine (new entries update it; continuations keep it)
                last_medicine = formulation.drug_name

                # Deduplicate by formulation_id
                if formulation.formulation_id in seen_ids:
                    continue
                seen_ids.add(formulation.formulation_id)
                formulations.append(formulation)

    log.info(
        "parse_compendium_pdf: extracted %d formulations from %s",
        len(formulations),
        path.name,
    )
    return formulations


def _get_bundled_pdf() -> Path | None:
    """Return the path to the bundled 2022 compendium PDF shipped with the package."""
    try:
        from importlib.resources import files
        ref = files("india_rx_mcp.data").joinpath("nppa_compendium_2022.pdf")
        p = Path(str(ref))
        return p if p.exists() else None
    except Exception:
        return None


def scrape_compendium(url: str, dest: Path) -> list[Formulation]:
    """Parse the NPPA compendium PDF.

    Uses the bundled 2022 compendium shipped with the package to avoid SSL
    certificate issues with nppa.gov.in on some platforms. Falls back to a
    live download only if the bundled copy is unavailable.
    """
    bundled = _get_bundled_pdf()
    if bundled is not None:
        log.info("scrape_compendium: using bundled NPPA compendium (no download needed)")
        return parse_compendium_pdf(bundled, source_url=url)

    # Fallback: live download (may fail on platforms with SSL cert chain issues)
    log.warning("Bundled NPPA PDF not found — attempting live download from %s", url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers=HEADERS, timeout=120.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    dest.write_bytes(response.content)
    log.info("scrape_compendium: downloaded %d bytes to %s", len(response.content), dest)
    return parse_compendium_pdf(dest, source_url=url)
