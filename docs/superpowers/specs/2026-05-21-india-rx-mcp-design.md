# india-rx-mcp — Design

**Status:** Design approved, ready for implementation planning
**Date:** 2026-05-21
**Owner:** Sahil Deshmukh (sahildeshmukh.pune@gmail.com)

## What this is

An MCP (Model Context Protocol) server that exposes Indian pharma regulatory data — CDSCO drug approvals and NPPA ceiling prices — to any MCP-compatible LLM client (Claude Desktop, Cursor, Cline, Continue, etc.).

The server is published to PyPI. Users install it with one line in their Claude Desktop config and immediately get analyst-grade tools, browsable catalogs, and pre-built workflows for Indian pharma intelligence.

## Why this project
- The space is **genuinely underserved**. A search of PyPI, GitHub, Glama, Smithery, and Lobehub in May 2026 turned up no MCP server combining CDSCO + NPPA data. Multiple openFDA / Orange Book MCP servers exist for US pharma, none for Indian pharma.
- Public Indian pharma data is overwhelmingly **scrape-not-API**, which is exactly why no one has done it. That barrier is the defensibility.

## Goals & non-goals

### Goals (v1)
- Wrap CDSCO approved-drugs data and NPPA ceiling-price data into a polished MCP server
- Ship 7 tools, 2 resources, 3 prompts
- Cache-backed: tool responses <100ms, no live gov.in dependency per query
- One-line install via `uvx india-rx-mcp`
- Polished README + 60-second demo GIF.

### Non-goals (v1)
- CTRI (clinical trials) — separate domain, lower analyst value
- Indian Patent Office (inPASS) — scraping is its own rabbit hole
- FDA cross-reference — scope creep
- Real-time scraping per query — cache-only by design
- Web UI / hosted service — CLI MCP server only
- Multi-user, auth, rate limiting beyond polite scraping

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Claude Desktop / Cursor / any MCP client           │
└───────────────────┬─────────────────────────────────┘
                    │ stdio (MCP protocol)
┌───────────────────▼─────────────────────────────────┐
│  india-rx-mcp server                                 │
│  ┌─────────────────────────────────────────────┐    │
│  │ MCP primitives: Tools / Resources / Prompts │    │
│  └──────────────────┬──────────────────────────┘    │
│  ┌──────────────────▼──────────────────────────┐    │
│  │ Service layer                                │    │
│  │  • ApprovalsService (CDSCO)                  │    │
│  │  • PricingService (NPPA)                     │    │
│  └──────────────────┬──────────────────────────┘    │
│  ┌──────────────────▼──────────────────────────┐    │
│  │ Data layer                                   │    │
│  │  • SQLite cache (scheduled refresh)          │    │
│  │  • Scrapers (httpx + BS4 + pdfplumber)       │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
            │
            │ scheduled refresh (daily/weekly)
            ▼
   ┌─────────────────────┐    ┌──────────────────┐
   │ cdsco.gov.in (HTML) │    │ nppa.gov.in (PDF)│
   └─────────────────────┘    └──────────────────┘
```

### Key architectural decisions

1. **SQLite-backed cache.** Tool responses read from local SQLite, not live gov.in. This gives <100ms responses, offline usability, and resilience when gov.in is down. Trade-off: data can be stale up to one refresh cycle.

2. **Scrapers isolated in `scrapers/` module.** When CDSCO's or NPPA's pages change, only one file needs to change. Tools never touch HTML or PDF parsing.

3. **Service layer between MCP and scrapers.** Tools call services; services query cache. If a real API ever ships (CDSCO's DDRS is in RFP as of 2026), only the scraper changes — tools and services stay stable.

4. **Background refresh.** Refresh runs out-of-band. Tools never block on a scraper. A manual `india-rx-mcp refresh` CLI exists for force-refresh.

5. **Python.** Choice driven by scraping + PDF parsing ecosystem (BeautifulSoup, pdfplumber, playwright). The MCP Python SDK is mature. PyPI fits the audience.

## MCP primitives — full surface

### Tools (7)

#### CDSCO tools

```
search_cdsco_approvals(
    query: str | None = None,
    from_date: str | None = None,        # ISO 8601
    to_date: str | None = None,
    therapeutic_area: str | None = None,
    sponsor: str | None = None,
    limit: int = 20,
) -> str  # markdown table + source citations
```
Returns approvals matching filters.

```
get_cdsco_approval(
    approval_id: str | None = None,
    drug_name: str | None = None,
) -> str
```
Returns full record for one approval: formulation, indication, conditions of approval, sponsor, references. Exactly one of `approval_id` or `drug_name` required.

```
list_recent_cdsco_approvals(
    since_date: str | None = None,       # default: 30 days ago
    limit: int = 20,
) -> str
```
Convenience for "what's new lately."

```
cdsco_sponsor_pipeline(sponsor_name: str) -> str
```
All approvals for one sponsor, grouped by year and therapeutic area.

#### NPPA tools

```
get_nppa_ceiling_price(
    drug_name: str,
    strength: str | None = None,         # e.g. "10mg"
    form: str | None = None,             # e.g. "tablet", "injection"
) -> str
```
Returns ceiling price record: price per unit, effective date, formulation details.

```
search_nppa_scheduled_formulations(
    query: str | None = None,
    therapeutic_area: str | None = None,
    limit: int = 20,
) -> str
```
Lists NPPA-controlled formulations matching criteria.

```
list_nppa_price_changes(
    since_date: str | None = None,       # default: 180 days ago
    limit: int = 50,
) -> str
```
Recent price revisions: formulation, old price, new price, effective date, reason (WPI adjustment / specific order).

### Resources (2)

```
cdsco://catalog/approved-drugs
  → full list of CDSCO-approved drugs, browseable as one resource

nppa://catalog/scheduled-formulations
  → current NPPA ceiling-price list as one document
```

Both refresh on the same cron as the underlying scrapers.

### Prompts (3)

```
competitor_briefing(sponsor: str)
  → orchestrates cdsco_sponsor_pipeline + NPPA prices for their drugs
  → output: written brief on a company's Indian pharma footprint

therapeutic_area_landscape(therapeutic_area: str, since_months: int = 12)
  → orchestrates search_cdsco_approvals + search_nppa_scheduled_formulations
  → output: who got approved, what's price-controlled, who the players are

monthly_market_update()
  → orchestrates list_recent_cdsco_approvals + list_nppa_price_changes
  → output: "what mattered this month in Indian pharma" digest
```

### Tool return format

All tools return **structured markdown**: tables and key/value blocks, with source URLs cited at the bottom of each result. The citation lets the analyst click through to the original gov.in page for verification.

### Parameter matching semantics

- **`sponsor` / `sponsor_name`**: case-insensitive substring match against the sponsor field. Handles common variants (e.g., `"sun pharma"` matches `"Sun Pharmaceutical Industries Ltd."`).
- **`therapeutic_area`**: CDSCO does not categorize approvals by therapeutic area natively. v1 implementation uses substring match against the indication text (e.g., `therapeutic_area="oncology"` matches indications containing "cancer", "tumor", "oncology", etc., via a small keyword-expansion map). This is a known approximation and is documented in the README as a v1 limitation.
- **`drug_name`**: case-insensitive match on canonical drug name OR brand name; partial matches return ranked results.
- **`from_date` / `to_date`**: ISO 8601 (`YYYY-MM-DD`). Inclusive bounds.

## Data sources

### CDSCO (drug approvals)
- Primary: `https://cdsco.gov.in/opencms/opencms/en/Approval_new/Approved-New-Drugs/` (year-wise HTML lists)
- Secondary: `https://cdscoonline.gov.in/CDSCO/Drugs` (search interface)
- Data Bank: `https://cdsco.gov.in/opencms/opencms/en/Data-Bank/` (downloadable Excel/PDF)
- **No public API.** A "Digital Drugs Regulatory System" (DDRS) is in RFP as of 2026 — not operational.

### NPPA (drug pricing)
- Primary: `https://nppa.gov.in/` (ceiling price PDFs and revision orders)
- Secondary: `https://nppaipdms.gov.in/` (Integrated Pharmaceutical Database Management System)
- Most data is PDF tables; some HTML lists.
- **No public API.**

## Scraping strategy

### CDSCO scraper (`src/india_rx_mcp/scrapers/cdsco_scraper.py`)
- Stack: `httpx` + `BeautifulSoup4`
- Rate limit: 1 request/second
- User-Agent: `india-rx-mcp/0.1.0 (contact: sahildeshmukh.pune@gmail.com)`
- First-run backfill: scrape historical years (~2017–present), one-time, expected duration 5-10 min, with progress in logs
- Incremental: scrape current year's updates daily

### NPPA scraper (`src/india_rx_mcp/scrapers/nppa_scraper.py`)
- Stack: `httpx` + `pdfplumber`
- Strategy: poll for new PDFs weekly. Parse tables from each PDF, normalize to formulations + price-changes rows
- WPI annual revision (typically April) and ad-hoc revision orders both supported

### Resilience
If a scraper breaks (HTML changes, PDF format changes, gov.in outage):
- Tools still return cached data
- Each tool response includes `last_refreshed: <date>` so the analyst knows freshness
- Failure is logged to a `scraper_errors` table; visible via `india-rx-mcp status` CLI command
- Stale data > no data

## Cache

- **SQLite** at platform-appropriate cache dir:
  - Linux: `$XDG_CACHE_HOME/india-rx-mcp/cache.db`
  - macOS: `~/Library/Caches/india-rx-mcp/cache.db`
  - Windows: `%LOCALAPPDATA%\india-rx-mcp\cache.db`
- Tables:
  - `approvals` (CDSCO approval records)
  - `formulations` (NPPA scheduled formulations with current ceiling price)
  - `price_changes` (NPPA price revision history)
  - `meta` (per-source last_refresh timestamp, last_error)
  - `scraper_errors` (log of failed scrape attempts for diagnostics)
- Refresh policy:
  - CDSCO: refresh if `meta.cdsco_last_refresh` older than 24h
  - NPPA: refresh if `meta.nppa_last_refresh` older than 7 days
  - Refresh runs in background thread on server start, never blocks tool responses

## Project structure

```
india-rx-mcp/
├── pyproject.toml
├── README.md
├── LICENSE                            # MIT
├── docs/
│   ├── claude-desktop-setup.md
│   ├── architecture.md
│   └── demo.gif
├── src/india_rx_mcp/
│   ├── __init__.py
│   ├── server.py                      # MCP server entry point
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── cdsco_tools.py             # 4 CDSCO tools
│   │   └── nppa_tools.py              # 3 NPPA tools
│   ├── resources/
│   │   ├── __init__.py
│   │   └── catalogs.py                # 2 catalog resources
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── workflows.py               # 3 prompt templates
│   ├── services/
│   │   ├── __init__.py
│   │   ├── approvals_service.py
│   │   └── pricing_service.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── cdsco_scraper.py
│   │   └── nppa_scraper.py
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── db.py                      # SQLite connection + schema migrations
│   │   └── models.py                  # dataclasses for rows
│   ├── formatting.py                  # markdown rendering helpers
│   └── cli.py                         # `india-rx-mcp refresh|status|version`
└── tests/
    ├── fixtures/                      # recorded HTML/PDF samples
    ├── test_scrapers/
    ├── test_services/
    ├── test_tools/
    └── test_e2e/                      # MCP server end-to-end smoke tests
```

## Testing strategy

- **Scrapers** tested against recorded fixtures in `tests/fixtures/` (saved HTML pages, sample PDFs). CI never hits gov.in.
- **Services** tested against an in-memory SQLite seeded with known rows.
- **Tools** tested end-to-end with a seeded SQLite cache, asserting on returned markdown structure and citation correctness.
- **MCP server smoke tests** launch the server, send a `list_tools` / `call_tool` request, assert the response shape conforms to MCP spec.
- Target: >80% line coverage, all critical paths covered.

## Packaging & distribution

- Published to PyPI as `india-rx-mcp`
- Versioning: SemVer, starting at `0.1.0`
- Installation in Claude Desktop:

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

  `uvx` handles install + execution. No prior `pip install` needed.

## Portfolio assets shipped alongside v1

- **README** with: Why / What / Install / Examples / Architecture / Roadmap
- **60-second demo GIF** showing Claude Desktop asking three real analyst questions and getting structured answers with citations
- **Companion blog post** (optional but recommended): "Building the MCP server for Indian pharma data nobody else wanted to scrape"
- **Repo pinned** on the author's GitHub profile

## Effort estimate

| Phase | Days |
|---|---|
| Scrapers + cache schema | 3 |
| Services + tools | 1.5 |
| Resources + prompts | 0.5 |
| Tests + fixtures | 1 |
| README + demo + PyPI publish | 1 |
| **Total** | **~7 days of focused work** |

Highest-risk item: NPPA PDF parsing variance. Add buffer there if needed.

## Open questions / decisions deferred to implementation

- Exact CDSCO year-page URL pattern (verify during scraper development; structure may differ for older years)
- NPPA PDF format consistency across years (may need format-version detection)
- Whether to expose individual approval letters as additional MCP resources in v1.1
- Whether to add CTRI trials in v2

## Future roadmap (post-v1)

- **v1.1:** CTRI clinical trials integration
- **v1.2:** Cross-reference tool comparing CDSCO vs FDA approval timing
- **v2.0:** Indian Patent Office (inPASS) integration
- **v2.1:** Optional hosted version with shared cache, multi-tenant

## References

- [Model Context Protocol specification](https://github.com/modelcontextprotocol/modelcontextprotocol)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [CDSCO Approved New Drugs](https://cdsco.gov.in/opencms/opencms/en/Approval_new/Approved-New-Drugs/)
- [CDSCO Online Portal](https://cdscoonline.gov.in/CDSCO/Drugs)
- [NPPA Official Site](https://nppa.gov.in/)
- [NPPA IPDMS Portal](https://nppaipdms.gov.in/)
- Existing pharma MCP servers (for differentiation reference):
  - [drug-pipeline-mcp](https://glama.ai/mcp/servers/DasClown/drug-pipeline-mcp)
  - [openpharma-org/fda-mcp](https://glama.ai/mcp/servers/@openpharma-org/fda-mcp)
  - [Augmented-Nature/OpenFDA-MCP-Server](https://github.com/Augmented-Nature/OpenFDA-MCP-Server)
