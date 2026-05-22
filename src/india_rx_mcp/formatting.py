from datetime import date

from india_rx_mcp.cache.models import Approval, Formulation, PriceChange


def _fmt_date(d: date | None) -> str:
    return d.isoformat() if d else ""


def _fmt_price(p: float | None) -> str:
    return f"₹{p:.2f}" if p is not None else ""


def approvals_table(approvals: list[Approval]) -> str:
    if not approvals:
        return "_No approvals found for the given criteria._"
    lines = [
        "| Drug | Sponsor | Approval Date | Indication |",
        "|---|---|---|---|",
    ]
    for a in approvals:
        lines.append(
            f"| {a.drug_name} | {a.sponsor or ''} | "
            f"{_fmt_date(a.approval_date)} | {a.indication or ''} |"
        )
    lines.append("")
    lines.append(citations_block([a.source_url for a in approvals]))
    return "\n".join(lines)


def approval_detail(a: Approval) -> str:
    return "\n".join([
        f"# {a.drug_name}",
        "",
        f"- **Approval ID:** `{a.approval_id}`",
        f"- **Sponsor:** {a.sponsor or ''}",
        f"- **Approval date:** {_fmt_date(a.approval_date)}",
        f"- **Indication:** {a.indication or ''}",
        f"- **Formulation:** {a.formulation or ''}",
        f"- **Conditions of approval:** {a.conditions or ''}",
        "",
        citations_block([a.source_url]),
    ])


def formulations_table(formulations: list[Formulation]) -> str:
    if not formulations:
        return "_No formulations found for the given criteria._"
    lines = [
        "| Drug | Strength | Form | Ceiling price | Effective |",
        "|---|---|---|---|---|",
    ]
    for f in formulations:
        lines.append(
            f"| {f.drug_name} | {f.strength or ''} | {f.form or ''} | "
            f"{_fmt_price(f.ceiling_price_inr)} | {_fmt_date(f.price_effective_date)} |"
        )
    lines.append("")
    lines.append(citations_block([f.source_url for f in formulations]))
    return "\n".join(lines)


def price_changes_table(changes: list[PriceChange]) -> str:
    if not changes:
        return "_No price changes found for the given criteria._"
    lines = [
        "| Formulation | Old price | New price | Effective | Reason |",
        "|---|---|---|---|---|",
    ]
    for c in changes:
        lines.append(
            f"| `{c.formulation_id}` | {_fmt_price(c.old_price_inr)} | "
            f"{_fmt_price(c.new_price_inr)} | {_fmt_date(c.effective_date)} | "
            f"{c.reason or ''} |"
        )
    lines.append("")
    lines.append(citations_block([c.source_url for c in changes]))
    return "\n".join(lines)


def citations_block(urls: list[str]) -> str:
    seen: set[str] = set()
    unique = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            unique.append(u)
    if not unique:
        return ""
    lines = ["**Sources:**"]
    for u in unique:
        lines.append(f"- {u}")
    return "\n".join(lines)
