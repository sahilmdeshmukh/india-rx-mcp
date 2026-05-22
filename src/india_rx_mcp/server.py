from mcp.server.fastmcp import FastMCP

from india_rx_mcp.resources import catalogs
from india_rx_mcp.tools import cdsco_tools, nppa_tools

mcp = FastMCP("india-rx-mcp")

# CDSCO tools
mcp.tool()(cdsco_tools.search_cdsco_approvals)
mcp.tool()(cdsco_tools.get_cdsco_approval)
mcp.tool()(cdsco_tools.list_recent_cdsco_approvals)
mcp.tool()(cdsco_tools.cdsco_sponsor_pipeline)

# NPPA tools
mcp.tool()(nppa_tools.get_nppa_ceiling_price)
mcp.tool()(nppa_tools.search_nppa_scheduled_formulations)
mcp.tool()(nppa_tools.list_nppa_price_changes)

# Resources
mcp.resource("cdsco://catalog/approved-drugs")(catalogs.approved_drugs_catalog)
mcp.resource("nppa://catalog/scheduled-formulations")(catalogs.scheduled_formulations_catalog)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
