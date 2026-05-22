import sqlite3
from datetime import date, timedelta

from india_rx_mcp.cache.models import Approval
from india_rx_mcp.cache.repo import find_approvals, row_to_approval

THERAPEUTIC_AREA_KEYWORDS: dict[str, list[str]] = {
    "oncology": ["cancer", "tumor", "tumour", "carcinoma", "oncology", "leukemia",
                 "lymphoma", "melanoma", "sarcoma"],
    "cardiology": ["cardiac", "cardiovascular", "hypertension", "hyperlipidemia",
                   "angina", "heart", "myocardial"],
    "diabetes": ["diabetes", "diabetic", "glycemic", "insulin"],
    "respiratory": ["asthma", "copd", "bronchitis", "pulmonary", "respiratory"],
    "neurology": ["alzheimer", "parkinson", "epilepsy", "migraine", "neurologic",
                  "multiple sclerosis"],
    "infectious": ["bacterial", "viral", "fungal", "antibiotic", "antiviral",
                   "infection", "hiv", "hepatitis", "tuberculosis", "covid"],
    "psychiatry": ["depression", "anxiety", "schizophrenia", "bipolar", "psychiatric"],
    "dermatology": ["psoriasis", "eczema", "dermatitis", "acne"],
}


class ApprovalsService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def search(
        self,
        query: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        therapeutic_area: str | None = None,
        sponsor: str | None = None,
        limit: int = 20,
    ) -> list[Approval]:
        if therapeutic_area:
            keywords = THERAPEUTIC_AREA_KEYWORDS.get(therapeutic_area.lower(), [therapeutic_area])
            matches: list[Approval] = []
            seen: set[str] = set()
            for kw in keywords:
                for a in find_approvals(
                    self.conn, drug_query=query, sponsor=sponsor,
                    from_date=from_date, to_date=to_date,
                    indication_query=kw, limit=limit,
                ):
                    if a.approval_id not in seen:
                        seen.add(a.approval_id)
                        matches.append(a)
                        if len(matches) >= limit:
                            return matches
            return matches
        return find_approvals(
            self.conn, drug_query=query, sponsor=sponsor,
            from_date=from_date, to_date=to_date, limit=limit,
        )

    def get(self, approval_id: str | None = None, drug_name: str | None = None) -> Approval | None:
        if approval_id:
            row = self.conn.execute(
                "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
            return row_to_approval(row) if row else None
        if drug_name:
            results = find_approvals(self.conn, drug_query=drug_name, limit=1)
            return results[0] if results else None
        return None

    def recent(self, since_date: date | None = None, limit: int = 20) -> list[Approval]:
        if since_date is None:
            since_date = date.today() - timedelta(days=30)
        return find_approvals(self.conn, from_date=since_date, limit=limit)

    def sponsor_pipeline(self, sponsor_name: str) -> list[Approval]:
        return find_approvals(self.conn, sponsor=sponsor_name, limit=1000)
