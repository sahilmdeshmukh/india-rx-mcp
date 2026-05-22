import sqlite3
from collections.abc import Iterable
from datetime import date, datetime

from india_rx_mcp.cache.models import Approval, Formulation, PriceChange


def _date_str(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    return date.fromisoformat(s)


def upsert_approvals(conn: sqlite3.Connection, approvals: Iterable[Approval]) -> int:
    n = 0
    for a in approvals:
        conn.execute(
            """INSERT INTO approvals(
                approval_id, drug_name, sponsor, approval_date, indication,
                formulation, conditions, source_url, scraped_at
            ) VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(approval_id) DO UPDATE SET
                drug_name=excluded.drug_name,
                sponsor=excluded.sponsor,
                approval_date=excluded.approval_date,
                indication=excluded.indication,
                formulation=excluded.formulation,
                conditions=excluded.conditions,
                source_url=excluded.source_url,
                scraped_at=excluded.scraped_at""",
            (a.approval_id, a.drug_name, a.sponsor, _date_str(a.approval_date),
             a.indication, a.formulation, a.conditions, a.source_url,
             a.scraped_at.isoformat()),
        )
        n += 1
    conn.commit()
    return n


def upsert_formulations(conn: sqlite3.Connection, formulations: Iterable[Formulation]) -> int:
    n = 0
    for f in formulations:
        conn.execute(
            """INSERT INTO formulations(
                formulation_id, drug_name, strength, form, ceiling_price_inr,
                price_effective_date, source_url, scraped_at
            ) VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(formulation_id) DO UPDATE SET
                drug_name=excluded.drug_name,
                strength=excluded.strength,
                form=excluded.form,
                ceiling_price_inr=excluded.ceiling_price_inr,
                price_effective_date=excluded.price_effective_date,
                source_url=excluded.source_url,
                scraped_at=excluded.scraped_at""",
            (f.formulation_id, f.drug_name, f.strength, f.form,
             f.ceiling_price_inr, _date_str(f.price_effective_date),
             f.source_url, f.scraped_at.isoformat()),
        )
        n += 1
    conn.commit()
    return n


def upsert_price_changes(conn: sqlite3.Connection, changes: Iterable[PriceChange]) -> int:
    n = 0
    for c in changes:
        conn.execute(
            """INSERT INTO price_changes(
                formulation_id, old_price_inr, new_price_inr,
                effective_date, reason, source_url, scraped_at
            ) VALUES (?,?,?,?,?,?,?)""",
            (c.formulation_id, c.old_price_inr, c.new_price_inr,
             _date_str(c.effective_date), c.reason, c.source_url,
             c.scraped_at.isoformat()),
        )
        n += 1
    conn.commit()
    return n


def _row_to_approval(row: sqlite3.Row) -> Approval:
    return Approval(
        approval_id=row["approval_id"],
        drug_name=row["drug_name"],
        sponsor=row["sponsor"],
        approval_date=_parse_date(row["approval_date"]),
        indication=row["indication"],
        formulation=row["formulation"],
        conditions=row["conditions"],
        source_url=row["source_url"],
        scraped_at=datetime.fromisoformat(row["scraped_at"]),
    )


def _row_to_formulation(row: sqlite3.Row) -> Formulation:
    return Formulation(
        formulation_id=row["formulation_id"],
        drug_name=row["drug_name"],
        strength=row["strength"],
        form=row["form"],
        ceiling_price_inr=row["ceiling_price_inr"],
        price_effective_date=_parse_date(row["price_effective_date"]),
        source_url=row["source_url"],
        scraped_at=datetime.fromisoformat(row["scraped_at"]),
    )


def _row_to_price_change(row: sqlite3.Row) -> PriceChange:
    return PriceChange(
        change_id=row["change_id"],
        formulation_id=row["formulation_id"],
        old_price_inr=row["old_price_inr"],
        new_price_inr=row["new_price_inr"],
        effective_date=_parse_date(row["effective_date"]),
        reason=row["reason"],
        source_url=row["source_url"],
        scraped_at=datetime.fromisoformat(row["scraped_at"]),
    )


def find_approvals(
    conn: sqlite3.Connection,
    drug_query: str | None = None,
    sponsor: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    indication_query: str | None = None,
    limit: int = 100,
) -> list[Approval]:
    clauses: list[str] = []
    params: list = []
    if drug_query:
        clauses.append("LOWER(drug_name) LIKE ?")
        params.append(f"%{drug_query.lower()}%")
    if sponsor:
        clauses.append("LOWER(sponsor) LIKE ?")
        params.append(f"%{sponsor.lower()}%")
    if from_date:
        clauses.append("approval_date >= ?")
        params.append(from_date.isoformat())
    if to_date:
        clauses.append("approval_date <= ?")
        params.append(to_date.isoformat())
    if indication_query:
        clauses.append("LOWER(indication) LIKE ?")
        params.append(f"%{indication_query.lower()}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    # SQLite 3.30+ supports NULLS LAST; Python 3.14 ships 3.45+, so safe.
    sql = f"SELECT * FROM approvals {where} ORDER BY approval_date DESC NULLS LAST LIMIT ?"
    params.append(limit)
    return [_row_to_approval(r) for r in conn.execute(sql, params)]


def find_formulations(
    conn: sqlite3.Connection,
    drug_name: str | None = None,
    strength: str | None = None,
    form: str | None = None,
    limit: int = 100,
) -> list[Formulation]:
    clauses: list[str] = []
    params: list = []
    if drug_name:
        clauses.append("LOWER(drug_name) LIKE ?")
        params.append(f"%{drug_name.lower()}%")
    if strength:
        clauses.append("LOWER(strength) LIKE ?")
        params.append(f"%{strength.lower()}%")
    if form:
        clauses.append("LOWER(form) LIKE ?")
        params.append(f"%{form.lower()}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM formulations {where} ORDER BY drug_name LIMIT ?"
    params.append(limit)
    return [_row_to_formulation(r) for r in conn.execute(sql, params)]


def find_price_changes(
    conn: sqlite3.Connection,
    from_date: date | None = None,
    to_date: date | None = None,
    formulation_id: str | None = None,
    limit: int = 100,
) -> list[PriceChange]:
    clauses: list[str] = []
    params: list = []
    if from_date:
        clauses.append("effective_date >= ?")
        params.append(from_date.isoformat())
    if to_date:
        clauses.append("effective_date <= ?")
        params.append(to_date.isoformat())
    if formulation_id:
        clauses.append("formulation_id = ?")
        params.append(formulation_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM price_changes {where} ORDER BY effective_date DESC LIMIT ?"
    params.append(limit)
    return [_row_to_price_change(r) for r in conn.execute(sql, params)]
