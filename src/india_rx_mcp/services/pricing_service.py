import sqlite3
from datetime import date, timedelta

from india_rx_mcp.cache.models import Formulation, PriceChange
from india_rx_mcp.cache.repo import find_formulations, find_price_changes


class PricingService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_ceiling_price(
        self, drug_name: str, strength: str | None = None, form: str | None = None
    ) -> list[Formulation]:
        return find_formulations(self.conn, drug_name=drug_name, strength=strength, form=form)

    def search_scheduled(
        self, query: str | None = None, therapeutic_area: str | None = None, limit: int = 20
    ) -> list[Formulation]:
        # NPPA formulations don't carry indication; therapeutic_area is best-effort substring on drug name.
        # v1 limitation: documented in README.
        if therapeutic_area:
            return find_formulations(self.conn, drug_name=therapeutic_area, limit=limit)
        return find_formulations(self.conn, drug_name=query, limit=limit)

    def price_changes(self, since_date: date | None = None, limit: int = 50) -> list[PriceChange]:
        if since_date is None:
            since_date = date.today() - timedelta(days=180)
        return find_price_changes(self.conn, from_date=since_date, limit=limit)
