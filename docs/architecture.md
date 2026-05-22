# Architecture

For full design rationale, see [the spec](superpowers/specs/2026-05-21-india-rx-mcp-design.md). This is the quick reference.

## Layers

```
MCP client (Claude Desktop, Cursor, etc.)
  ↓ stdio
FastMCP server (server.py)
  ↓
Tools / Resources / Prompts
  ↓
Services (ApprovalsService, PricingService)
  ↓
Cache (SQLite via cache/repo.py)
  ↑
Scrapers (scrapers/cdsco_scraper.py, scrapers/nppa_scraper.py)
  ↑
gov.in (CDSCO yearly PDFs, NPPA compendium PDF)
```

## Data sources

- **CDSCO**: yearly "List of New Drugs approved" PDFs from cdsco.gov.in. Each year's PDF is downloaded via a two-hop URL (JSP wrapper → iframe → actual PDF) and parsed with pdfplumber. The yearly PDF has 4 columns: S.No, Drug Name, Indication, Date.
- **NPPA**: the "Compendium of Prices 2022" PDF from nppa.gov.in. ~31 pages with structured text but no grid lines — parsed via text-line regex with continuation-row merging (rows without a leading section ID inherit the previous medicine name).

## Refresh

- **CDSCO**: 24h interval, fetches index + all year-PDFs.
- **NPPA**: 7d interval, fetches the compendium.
- Refresh runs on a background thread at server startup if cache is stale.
- Manual refresh: `india-rx-mcp refresh`

## Failure handling

Scrapers log errors to a `scraper_errors` table; tools always return cached data with a freshness indicator. Stale > nothing.

## Cache location

- Linux: `$XDG_CACHE_HOME/india-rx-mcp/cache.db`
- macOS: `~/Library/Caches/india-rx-mcp/cache.db`
- Windows: `%LOCALAPPDATA%\india-rx-mcp\cache.db`

## Threading

The MCP server holds one long-lived SQLite connection (`check_same_thread=True` by default). The background refresh worker opens its own connection per refresh call — required because Python's sqlite3 forbids cross-thread connection use.
