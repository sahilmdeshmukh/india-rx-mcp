# india-rx-mcp

An MCP (Model Context Protocol) server for **Indian pharma regulatory data** — CDSCO drug approvals and NPPA ceiling-price data — for any MCP-compatible LLM client (Claude Desktop, Cursor, Cline, Continue).

Built by a pharma market analyst, for pharma market analysts.

## Why this exists

Multiple MCP servers exist for US pharma (openFDA, Orange Book, ClinicalTrials.gov). **None exist for Indian pharma.** Indian regulatory data is overwhelmingly scrape-not-API, which is exactly why no one has done it. This server fills the gap.

## What it gives you

**7 tools** that map directly to analyst questions:

| Question | Tool |
|---|---|
| "What did Sun Pharma get approved in 2026?" | `cdsco_sponsor_pipeline` * |
| "What's new in oncology this month?" | `search_cdsco_approvals` |
| "What's the ceiling price for atorvastatin 10mg?" | `get_nppa_ceiling_price` |
| "Any recent antibiotic price changes?" | `list_nppa_price_changes` * |
| "Tell me about the latest CDSCO approval for [drug]" | `get_cdsco_approval` |
| "What's new in CDSCO approvals?" | `list_recent_cdsco_approvals` |
| "Which formulations are NPPA-controlled in cardiology?" | `search_nppa_scheduled_formulations` |

`*` denotes a v1 limitation — see [Limitations](#limitations-v1) below.

**2 browseable resources:**
- `cdsco://catalog/approved-drugs` — full CDSCO catalog as one document
- `nppa://catalog/scheduled-formulations` — full NPPA ceiling-price list

**3 pre-built analyst workflow prompts:**
- `competitor_briefing(sponsor)` — written brief on a company's regulatory footprint
- `therapeutic_area_landscape(therapeutic_area, since_months=12)` — landscape view of a TA
- `monthly_market_update()` — digest of recent approvals and price changes

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

See [docs/claude-desktop-setup.md](docs/claude-desktop-setup.md) for the full setup including PAT-style alternatives.

## CLI

```bash
india-rx-mcp version       # print version
india-rx-mcp status        # show cache status (counts + last refresh per source)
india-rx-mcp refresh       # force refresh from gov.in
india-rx-mcp refresh --source cdsco   # refresh just CDSCO
```

## Architecture

See [docs/architecture.md](docs/architecture.md).

## Limitations (v1)

This is v0.1 — first public release. Known gaps you should know about before relying on the data:

1. **CDSCO sponsor data is missing.** CDSCO publishes yearly approval PDFs with `S.No / Drug Name / Indication / Date` only — no sponsor column. So:
   - `cdsco_sponsor_pipeline(...)` returns empty for CDSCO-sourced data
   - `search_cdsco_approvals(sponsor=...)` filter won't match CDSCO data
   - `Approval.sponsor` is `None` for all CDSCO records
   - Planned for v1.1 (likely by parsing detailed approval letters or alternative CDSCO endpoints)
2. **NPPA data is from the 2022 Compendium of Prices** (last published comprehensive compilation). Quarterly WPI revisions since then aren't in v1. Adding WPI-revision notification parsing is planned for v1.2.
3. **`list_nppa_price_changes(...)` returns empty in v1.** The compendium is a snapshot. Price-change tracking requires either comparing successive compendiums or parsing WPI revision notifications — both planned for v1.2.
4. **`therapeutic_area` on NPPA is best-effort substring match on drug name** (NPPA formulations don't carry indication metadata). For richer TA filtering use `search_cdsco_approvals(therapeutic_area=...)`, which has a built-in keyword-expansion map.
5. **Patents, CTRI clinical trials, FDA cross-reference**: out of scope for v1.

## Roadmap

- **v1.1**: CDSCO sponsor data; CTRI clinical trials integration
- **v1.2**: WPI revision parsing for live price changes; CDSCO ↔ FDA approval-timing comparison tool
- **v2.0**: Indian Patent Office (inPASS) integration; optional hosted multi-tenant version

## Contributing

This is a portfolio project but contributions are welcome. Open an issue describing what you want to add before sending a PR.

## License

MIT. See [LICENSE](LICENSE).
