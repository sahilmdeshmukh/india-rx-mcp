from pathlib import Path

from india_rx_mcp.scrapers.cdsco_scraper import (
    CdscoYearPdf,
    parse_cdsco_pdf,
    parse_index_html,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cdsco"
INDEX_HTML = (FIXTURES / "approved_new_drugs_index.html").read_text(encoding="utf-8")
PDF_2024 = FIXTURES / "approvals_2024.pdf"


def test_parse_index_html_extracts_yearly_pdf_entries():
    entries = parse_index_html(INDEX_HTML)
    assert len(entries) >= 5
    for e in entries:
        assert isinstance(e, CdscoYearPdf)
        assert e.year >= 2000
        assert e.year <= 2030
        # The JSP URL pattern, before resolution
        assert "download_file_division.jsp" in e.pdf_url or e.pdf_url.endswith(".pdf")


def test_parse_index_html_includes_recent_years():
    entries = parse_index_html(INDEX_HTML)
    years = {e.year for e in entries}
    # Index should cover at least 2020-2024
    assert {2020, 2021, 2022, 2023, 2024} <= years


def test_parse_cdsco_pdf_returns_approvals_with_required_fields():
    approvals = parse_cdsco_pdf(PDF_2024, year=2024, source_url="https://cdsco.gov.in/test.pdf")
    assert len(approvals) >= 5
    a = approvals[0]
    assert a.drug_name  # non-empty
    assert a.sponsor is None  # v1 limitation
    assert a.formulation is None  # v1 limitation
    assert a.source_url == "https://cdsco.gov.in/test.pdf"
    assert a.approval_id.startswith("CDSCO-")


def test_parse_cdsco_pdf_extracts_approval_dates_where_present():
    approvals = parse_cdsco_pdf(PDF_2024, year=2024, source_url="https://cdsco.gov.in/test.pdf")
    dated = [a for a in approvals if a.approval_date is not None]
    # Most rows should have dates; allow some leniency for mis-parses
    assert len(dated) >= max(3, len(approvals) // 2)


def test_parse_cdsco_pdf_indication_does_not_contain_raw_pua_bullet():
    """The PDF has \\uf0b7 (Private Use Area bullet) as a list marker. Should be normalized."""
    approvals = parse_cdsco_pdf(PDF_2024, year=2024, source_url="https://cdsco.gov.in/test.pdf")
    for a in approvals:
        if a.indication:
            assert "" not in a.indication, f"Raw PUA bullet leaked into indication: {a.indication!r}"


def test_parse_cdsco_pdf_approval_ids_are_unique():
    approvals = parse_cdsco_pdf(PDF_2024, year=2024, source_url="https://cdsco.gov.in/test.pdf")
    ids = [a.approval_id for a in approvals]
    assert len(ids) == len(set(ids)), "approval_ids should be unique within a PDF"
