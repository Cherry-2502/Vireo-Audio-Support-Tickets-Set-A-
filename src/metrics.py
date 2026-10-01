from bisect import bisect_right, insort

import pandas as pd
import numpy as np

ISSUE_CATEGORY_ALIASES = {
    "account & login": "account/login",
    "connectivity (bluetooth/app)": "connectivity",
    "charging & battery": "charging/battery",
    "delivery & shipping": "delivery",
    "returns & refunds": "returns/refunds",
    "billing & payments": "billing/payments",
    "hardware defect/damage": "hardware defect",
    "warranty & repair": "hardware defect",
    "app & firmware": "app/firmware",
}


def _canonical_issue_category(value):
    if pd.isna(value):
        return None
    category = " ".join(str(value).casefold().split())
    if category in {"", "other", "unknown"}:
        return None
    return ISSUE_CATEGORY_ALIASES.get(category, category)


def detect_repeat_contacts(tickets_df):
    """Flag same-customer, same-category/SKU returns within 30 days of resolution.

    Category plus SKU is an issue proxy because the export has no issue identifier.
    Only valid, resolved prior tickets can start a repeat window.
    """
    df = tickets_df.copy().reset_index(drop=True)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["resolved_at"] = pd.to_datetime(df["resolved_at"], errors="coerce")
    df["_row_order"] = np.arange(len(df))
    df["_issue_category"] = df["category"].map(_canonical_issue_category)
    df["_issue_product"] = df["product_sku"].astype("string").str.strip().str.upper()
    previous_resolution_values = [pd.NaT] * len(df)
    elapsed_day_values = np.full(len(df), np.nan)
    repeat_values = np.zeros(len(df), dtype=bool)

    valid_issue = (
        df["customer_id"].notna()
        & df["_issue_category"].notna()
        & df["_issue_product"].notna()
        & df["_issue_product"].ne("")
        & df["created_at"].notna()
    )
    issue_columns = ["customer_id", "_issue_category", "_issue_product"]

    ordered = df.loc[valid_issue].sort_values(
        issue_columns + ["created_at", "_row_order"], kind="stable"
    )
    row_orders = ordered["_row_order"].to_numpy(dtype=int)
    created_values = ordered["created_at"].to_numpy()
    resolved_values = ordered["resolved_at"].to_numpy()
    status_values = ordered["status"].to_numpy()
    group_positions = ordered.groupby(issue_columns, sort=False, dropna=False).indices.values()

    for positions in group_positions:
        prior_resolutions = []
        for position in positions:
            row_index = row_orders[position]
            created_at = pd.Timestamp(created_values[position])
            eligible_index = bisect_right(prior_resolutions, created_at) - 1
            if eligible_index >= 0:
                previous_resolution = prior_resolutions[eligible_index]
                elapsed_days = (created_at - previous_resolution).total_seconds() / 86400
                previous_resolution_values[row_index] = previous_resolution
                elapsed_day_values[row_index] = elapsed_days
                repeat_values[row_index] = elapsed_days <= 30

            resolved_at = pd.Timestamp(resolved_values[position]) if pd.notna(resolved_values[position]) else pd.NaT
            if (
                str(status_values[position]).casefold() == "resolved"
                and pd.notna(resolved_at)
                and resolved_at >= created_at
            ):
                insort(prior_resolutions, resolved_at)

    df["prev_resolved_at"] = pd.to_datetime(previous_resolution_values)
    df["days_since_prev_resolution"] = elapsed_day_values
    df["is_repeat"] = repeat_values
    channel_costs = {"chat": 210, "email": 260, "voice": 520, "social": 240}
    channels = df["channel"].astype("string").str.strip().str.casefold()
    df["contact_cost"] = channels.map(channel_costs).fillna(290)
    df["repeat_cost"] = np.where(df["is_repeat"], df["contact_cost"], 0)
    return df.sort_values("_row_order").drop(
        columns=["_row_order", "_issue_category", "_issue_product"]
    ).reset_index(drop=True)

def get_repeat_metrics(df):
    """Aggregate repeat-contact costs; quarterly waste is annualized over the span."""
    total_tickets = len(df)
    repeat_tickets = int(df["is_repeat"].fillna(False).sum()) if total_tickets else 0
    repeat_pct = repeat_tickets / total_tickets * 100 if total_tickets else 0.0
    total_waste = float(df["repeat_cost"].fillna(0).sum()) if total_tickets else 0.0

    dates = pd.to_datetime(df["created_at"], errors="coerce").dropna()
    if dates.empty:
        quarter_span_days = 0
    else:
        quarter_span_days = (dates.max().normalize() - dates.min().normalize()).days + 1
    quarterly_waste = (
        total_waste * 365.25 / (quarter_span_days * 4) if quarter_span_days else 0.0
    )

    repeat_df = df.loc[df["is_repeat"].fillna(False).astype(bool)]
    top_products = repeat_df["product_sku"].value_counts().head(3)
    top_categories = repeat_df["category"].value_counts().head(3)
    return {
        "total_tickets": total_tickets,
        "repeat_tickets": repeat_tickets,
        "repeat_pct": round(repeat_pct, 2),
        "repeat_rate_pct": round(repeat_pct, 2),
        "total_waste": round(total_waste, 2),
        "quarterly_waste": round(quarterly_waste, 2),
        "target_savings_per_quarter": round(quarterly_waste * 0.30, 2),
        "top_products": top_products.to_dict(),
        "top_categories": top_categories.to_dict(),
    }


def build_weekly_metrics(tickets_df):
    """Return Monday-start weekly volume, repeat rate, and repeat-contact cost."""
    columns = ["week_start", "total_tickets", "repeat_tickets", "repeat_pct", "repeat_cost"]
    dated = tickets_df.dropna(subset=["created_at"]).copy()
    if dated.empty:
        return pd.DataFrame(columns=columns)
    dated["week_start"] = pd.to_datetime(dated["created_at"]).dt.to_period("W-SUN").dt.start_time
    weekly = dated.groupby("week_start").agg(
        total_tickets=("ticket_id", "count"),
        repeat_tickets=("is_repeat", "sum"),
        repeat_cost=("repeat_cost", "sum"),
    ).reset_index()
    weekly["repeat_pct"] = np.where(
        weekly["total_tickets"].gt(0),
        weekly["repeat_tickets"] / weekly["total_tickets"] * 100,
        0.0,
    )
    return weekly[columns]


def _attach_ticket_date_assignments(resolved, agents_df):
    roster = agents_df[["agent_id", "name", "team", "tier", "from_date", "to_date"]].copy()
    roster["from_date"] = pd.to_datetime(roster["from_date"], errors="coerce")
    roster["to_date"] = pd.to_datetime(roster["to_date"], errors="coerce")
    resolved = resolved.copy().reset_index(drop=True)
    resolved["_ticket_row"] = np.arange(len(resolved))
    candidates = resolved[["_ticket_row", "agent_id", "created_at"]].merge(
        roster, on="agent_id", how="left"
    )
    matches = candidates[
        candidates["from_date"].notna()
        & candidates["from_date"].le(candidates["created_at"])
        & (candidates["to_date"].isna() | candidates["to_date"].ge(candidates["created_at"]))
    ].sort_values(["_ticket_row", "from_date"])
    matches = matches.drop_duplicates("_ticket_row", keep="last")
    assignment_columns = ["_ticket_row", "name", "team", "tier"]
    result = resolved.merge(matches[assignment_columns], on="_ticket_row", how="left")
    result["team"] = result["team"].fillna("Unknown")
    result["name"] = result["name"].fillna(result["agent_id"])
    return result.drop(columns="_ticket_row")

# 2. Main Logic: Build Leaderboards
def build_leaderboards(tickets_df, agents_df):
    """Build Tier 1 volume rankings and separate Tier 2 duration summaries."""
    resolved = tickets_df[tickets_df["status"].eq("resolved")].copy()
    resolved["created_at"] = pd.to_datetime(resolved["created_at"], errors="coerce")
    resolved["resolved_at"] = pd.to_datetime(resolved["resolved_at"], errors="coerce")
    resolved = _attach_ticket_date_assignments(resolved, agents_df)
    resolved["transfers"] = pd.to_numeric(resolved["transfers"], errors="coerce").fillna(0)
    resolved["resolution_days"] = (
        resolved["resolved_at"] - resolved["created_at"]
    ).dt.total_seconds() / 86400
    resolved.loc[resolved["resolution_days"] < 0, "resolution_days"] = np.nan

    ranked = resolved[resolved["tier"].eq(1)].copy()
    raw_volume = ranked.groupby(["agent_id", "name", "team"], dropna=False).agg(
        total_resolved=("ticket_id", "count"),
        avg_transfers=("transfers", "mean"),
    ).reset_index().sort_values("total_resolved", ascending=False).head(10)

    ranked["complexity_score"] = (
        1.0
        + ranked["priority"].eq("High").astype(int) * 0.5
        + ranked["transfers"] * 0.3
    )
    weighted_score = ranked.groupby(["agent_id", "name", "team"], dropna=False).agg(
        total_weighted_score=("complexity_score", "sum"),
        total_resolved=("ticket_id", "count"),
    ).reset_index().sort_values("total_weighted_score", ascending=False).head(10)

    team_summary = resolved.groupby(["team", "tier"], dropna=False).agg(
        agent_count=("agent_id", "nunique"),
        total_tickets=("ticket_id", "count"),
        avg_transfers=("transfers", "mean"),
        avg_resolution_days=("resolution_days", "mean"),
    ).reset_index()
    team_summary["avg_tickets_per_agent"] = np.where(
        team_summary["agent_count"].gt(0),
        team_summary["total_tickets"] / team_summary["agent_count"],
        0.0,
    )
    team_summary["volume_metric_applicable"] = team_summary["tier"].eq(1)
    return {
        "raw_volume": raw_volume,
        "weighted_score": weighted_score,
        "team_summary": team_summary,
    }
