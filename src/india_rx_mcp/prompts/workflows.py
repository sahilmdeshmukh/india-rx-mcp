def competitor_briefing(sponsor: str) -> str:
    """Build a written brief on an Indian pharma company's regulatory footprint.

    Note: CDSCO sponsor data is a v1 limitation — sponsor matching is best-effort
    against whatever sponsor strings are available in the cache.
    """
    return (
        f"You are a pharma market analyst. Build a brief on **{sponsor}**'s "
        f"Indian regulatory footprint.\n\n"
        f"Steps:\n"
        f"1. Call `cdsco_sponsor_pipeline(sponsor_name='{sponsor}')` to get all approvals "
        f"for this sponsor.\n"
        f"2. For each approval's drug, call `get_nppa_ceiling_price(drug_name=<drug>)` "
        f"to find NPPA-controlled pricing if any.\n"
        f"3. Summarize: number of approvals by year, top therapeutic areas, "
        f"price-controlled vs free-pricing drugs.\n"
        f"4. End with a 2-sentence strategic takeaway.\n"
        f"5. Cite all source URLs from the tool outputs."
    )


def therapeutic_area_landscape(therapeutic_area: str, since_months: int = 12) -> str:
    """Build a landscape view of a therapeutic area in Indian pharma."""
    return (
        f"You are a pharma market analyst. Build a landscape view of **{therapeutic_area}** "
        f"in India for the last {since_months} months.\n\n"
        f"Steps:\n"
        f"1. Call `search_cdsco_approvals(therapeutic_area='{therapeutic_area}', "
        f"from_date=<{since_months} months ago>)` to find recent approvals.\n"
        f"2. Call `search_nppa_scheduled_formulations(therapeutic_area='{therapeutic_area}')` "
        f"to find price-controlled drugs in this TA.\n"
        f"3. List: top sponsors active in the TA, recent approvals, price-controlled drugs.\n"
        f"4. End with a 2-sentence assessment of competitive intensity.\n"
        f"5. Cite all source URLs."
    )


def monthly_market_update() -> str:
    """Build a monthly digest of CDSCO approvals and NPPA price changes."""
    return (
        "You are a pharma market analyst. Build a monthly digest of Indian pharma "
        "regulatory action.\n\n"
        "Steps:\n"
        "1. Call `list_recent_cdsco_approvals()` to get the last 30 days of approvals.\n"
        "2. Call `list_nppa_price_changes()` to get recent price revisions.\n"
        "3. Group approvals by therapeutic area; flag any first-in-class or notable approvals.\n"
        "4. For price changes, highlight any unusually large revisions.\n"
        "5. End with a 'what to watch' section.\n"
        "6. Cite all source URLs."
    )
