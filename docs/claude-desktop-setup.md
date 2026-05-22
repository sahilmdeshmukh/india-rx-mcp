# Claude Desktop setup

## Prerequisites

- Claude Desktop installed
- `uv` installed (`pip install uv` or [official installer](https://docs.astral.sh/uv/getting-started/installation/))

## Config

Edit your Claude Desktop config:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add:

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

Save and restart Claude Desktop.

## First launch

On first invocation, the server scrapes CDSCO + NPPA in the background. Expect a 5-10 minute initial delay before queries return useful data. Use `india-rx-mcp status` from your terminal to monitor progress.

## Verifying it works

In Claude Desktop, ask: "What CDSCO drug approval tools do you have?"

Claude should list 7 tools (4 CDSCO, 3 NPPA). If not, check:
- Claude Desktop logs (Help → Show Logs)
- `india-rx-mcp version` works in terminal
- `uvx` is on `$PATH`

## Troubleshooting

If queries return empty results:
1. Run `india-rx-mcp status` — verify approvals and formulations are cached.
2. If counts are zero, run `india-rx-mcp refresh` and watch the output.
3. If refresh fails, check `scraper_errors` count in `india-rx-mcp status`.

If a CDSCO sponsor query returns nothing: that's expected in v1. CDSCO publishes drug approvals without sponsor metadata in the yearly PDFs. See the [README's Limitations section](../README.md#limitations-v1).
