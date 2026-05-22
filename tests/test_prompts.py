from india_rx_mcp.prompts.workflows import (
    competitor_briefing,
    monthly_market_update,
    therapeutic_area_landscape,
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
