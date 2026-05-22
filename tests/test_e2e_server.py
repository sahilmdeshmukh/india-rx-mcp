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
    from india_rx_mcp.resources import catalogs
    from india_rx_mcp.tools import cdsco_tools, nppa_tools
    monkeypatch.setattr(cdsco_tools, "_get_conn", lambda: conn)
    monkeypatch.setattr(nppa_tools, "_get_conn", lambda: conn)
    monkeypatch.setattr(catalogs, "_get_conn", lambda: conn)
    yield conn
    conn.close()


async def test_e2e_list_tools(seeded):
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    expected = {
        "search_cdsco_approvals", "get_cdsco_approval",
        "list_recent_cdsco_approvals", "cdsco_sponsor_pipeline",
        "get_nppa_ceiling_price", "search_nppa_scheduled_formulations",
        "list_nppa_price_changes",
    }
    assert expected <= names


async def test_e2e_call_tool_returns_seeded_data(seeded):
    """Call a real tool via the MCP server and assert the response contains seeded data."""
    result = await mcp.call_tool("search_cdsco_approvals", {"query": "ator"})
    # FastMCP's call_tool returns (content, metadata) — extract text robustly
    if isinstance(result, tuple):
        content = result[0]
    else:
        content = result.content if hasattr(result, "content") else result
    text_parts = []
    for item in content:
        if hasattr(item, "text"):
            text_parts.append(item.text)
        elif isinstance(item, str):
            text_parts.append(item)
    text = " ".join(text_parts)
    assert "Atorvastatin" in text, f"Expected 'Atorvastatin' in response, got: {text[:500]}"


async def test_e2e_list_resources(seeded):
    resources = await mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "cdsco://catalog/approved-drugs" in uris
    assert "nppa://catalog/scheduled-formulations" in uris


async def test_e2e_list_prompts(seeded):
    prompts = await mcp.list_prompts()
    names = {p.name for p in prompts}
    expected = {"competitor_briefing", "therapeutic_area_landscape", "monthly_market_update"}
    assert expected <= names
