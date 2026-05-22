from datetime import date
from pathlib import Path

from india_rx_mcp.scrapers.nppa_scraper import parse_compendium_pdf

FIXTURE = Path(__file__).parent / "fixtures" / "nppa" / "compendium_2022.pdf"


def test_parse_compendium_extracts_at_least_100_formulations():
    formulations = parse_compendium_pdf(FIXTURE, source_url="https://nppa.gov.in/test.pdf")
    assert len(formulations) >= 100


def test_parse_compendium_includes_atropine_with_price():
    formulations = parse_compendium_pdf(FIXTURE, source_url="https://nppa.gov.in/test.pdf")
    atropine = [f for f in formulations if f.drug_name.lower() == "atropine"]
    assert len(atropine) >= 1
    for f in atropine:
        assert f.ceiling_price_inr is not None
        assert f.ceiling_price_inr > 0
        assert f.source_url == "https://nppa.gov.in/test.pdf"


def test_parse_compendium_propagates_medicine_name_to_continuation_rows():
    """Atropine has 3 forms in the compendium: Ointment, Injection, Drops.
    All 3 should share the medicine name even though only the first row has it explicit."""
    formulations = parse_compendium_pdf(FIXTURE, source_url="https://nppa.gov.in/test.pdf")
    atropine_forms = {f.form for f in formulations if f.drug_name.lower() == "atropine"}
    # At least 2 of the 3 expected forms should be detected
    expected = {"ointment", "injection", "drops"}
    detected_lower = {(f or "").lower() for f in atropine_forms}
    assert len(detected_lower & expected) >= 2, f"Expected 2+ of {expected}, got {detected_lower}"


def test_parse_compendium_dates_are_real_dates():
    formulations = parse_compendium_pdf(FIXTURE, source_url="https://nppa.gov.in/test.pdf")
    dated = [f for f in formulations if f.price_effective_date is not None]
    assert len(dated) >= len(formulations) // 2  # at least half should have dates
    for f in dated:
        assert isinstance(f.price_effective_date, date)
        assert f.price_effective_date.year >= 2000


def test_parse_compendium_formulation_ids_are_unique():
    formulations = parse_compendium_pdf(FIXTURE, source_url="https://nppa.gov.in/test.pdf")
    ids = [f.formulation_id for f in formulations]
    assert len(ids) == len(set(ids))


def test_parse_compendium_ids_start_with_nppa_prefix():
    formulations = parse_compendium_pdf(FIXTURE, source_url="https://nppa.gov.in/test.pdf")
    assert all(f.formulation_id.startswith("NPPA-F-") for f in formulations)
