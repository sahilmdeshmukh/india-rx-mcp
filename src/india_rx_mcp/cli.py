import logging

import click

from india_rx_mcp import __version__
from india_rx_mcp.cache.db import get_db_path, get_meta, init_db


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """india-rx-mcp - MCP server for Indian pharma data."""
    if ctx.invoked_subcommand is None:
        from india_rx_mcp.server import main as server_main
        server_main()


@main.command()
def version() -> None:
    """Print version."""
    click.echo(__version__)


@main.command()
def status() -> None:
    """Show cache status (path, last refresh per source, error count)."""
    db_path = get_db_path()
    conn = init_db(db_path)
    click.echo(f"Cache: {db_path}")
    click.echo(f"CDSCO last refresh: {get_meta(conn, 'cdsco_last_refresh') or 'never'}")
    click.echo(f"NPPA last refresh:  {get_meta(conn, 'nppa_last_refresh') or 'never'}")
    n_approvals = conn.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
    n_form = conn.execute("SELECT COUNT(*) FROM formulations").fetchone()[0]
    n_errors = conn.execute("SELECT COUNT(*) FROM scraper_errors").fetchone()[0]
    click.echo(f"Approvals cached: {n_approvals}")
    click.echo(f"Formulations cached: {n_form}")
    click.echo(f"Scraper errors logged: {n_errors}")
    conn.close()


@main.command()
@click.option("--source", type=click.Choice(["cdsco", "nppa", "all"]), default="all",
              help="Which data source to refresh.")
def refresh(source: str) -> None:
    """Force refresh of the cache from gov.in sources."""
    from india_rx_mcp.refresh import refresh_cdsco, refresh_nppa
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if source in ("cdsco", "all"):
        click.echo("Refreshing CDSCO...")
        refresh_cdsco()
    if source in ("nppa", "all"):
        click.echo("Refreshing NPPA...")
        refresh_nppa()
    click.echo("Done.")
