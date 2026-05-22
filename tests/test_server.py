import asyncio

from india_rx_mcp.server import mcp


def test_mcp_server_has_name():
    assert mcp.name == "india-rx-mcp"


def test_mcp_server_registers_all_7_tools():
    # FastMCP's tool listing is async (list_tools is a coroutine).
    # The internal _tool_manager.list_tools() is sync but private.
    # Try the async public API first, fall back to internal if needed.
    try:
        tools = asyncio.run(mcp.list_tools())
        tool_names = {t.name for t in tools}
    except (AttributeError, TypeError):
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
    assert expected <= tool_names, f"Missing tools: {expected - tool_names}"
