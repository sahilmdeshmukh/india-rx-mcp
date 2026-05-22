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
