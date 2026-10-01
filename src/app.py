import os
import streamlit as st
import pandas as pd
import plotly.express as px
from src.classify import BATCH_SIZE, classify_batch
from src.metrics import (
    build_leaderboards,
    build_weekly_metrics,
    detect_repeat_contacts,
    get_repeat_metrics,
)

from src.clean import clean_data

st.set_page_config(
    page_title="Vireo Audio — CX Intelligence Hub",
    page_icon="🎧",
    layout="wide"
)

# Custom Styling for polished look
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 16px;
        border-radius: 8px;
        border-left: 5px solid #1E88E5;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎧 Vireo Audio — CX Operations & Intelligence Hub")
st.caption("Internal CX Decision Support Tool | Prepared for Priya Raman (Head of CX) & Arjun Mehta (Finance)")

# --- DATA LOADING ---
@st.cache_data
def load_app_data():
    data = clean_data()
    tickets = detect_repeat_contacts(data["tickets"])
    return tickets, data["agents"]

tickets_all, agents = load_app_data()

if tickets_all.empty:
    st.error("No ticket records were found. Check the CSV files in src/data/.")
    st.stop()

with st.sidebar:
    st.header("Controls & Scope")
    min_date = tickets_all["created_at"].min().date()
    max_date = tickets_all["created_at"].max().date()
    date_range = st.date_input(
        "Ticket date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    selected_channels = st.multiselect(
        "Channels",
        options=sorted(tickets_all["channel"].dropna().unique().tolist()),
        default=sorted(tickets_all["channel"].dropna().unique().tolist()),
    )
    st.markdown("---")
    st.caption("Repeat window: 30 days after valid resolution. Contact costs use policy channel rates.")

if isinstance(date_range, tuple):
    start_date, end_date = date_range if len(date_range) == 2 else (date_range[0], date_range[0])
else:
    start_date = end_date = date_range
mask = (
    tickets_all["created_at"].dt.date.between(start_date, end_date)
    & tickets_all["channel"].isin(selected_channels)
)
tickets = tickets_all.loc[mask].copy()
repeat_metrics = get_repeat_metrics(tickets)
weekly_metrics = build_weekly_metrics(tickets)

if weekly_metrics.empty:
    selected_week = None
    week_tickets = tickets.iloc[0:0].copy()
    selected_week_metrics = {"total_tickets": 0, "repeat_tickets": 0, "repeat_pct": 0.0}
    st.info("No tickets match the selected date and channel filters.")
else:
    selected_week = st.selectbox(
        "Reporting week (Monday to Sunday)",
        options=weekly_metrics["week_start"].tolist(),
        format_func=lambda week: f"{week:%d %b %Y} - {(week + pd.Timedelta(days=6)):%d %b %Y}",
    )
    selected_week_metrics = weekly_metrics.loc[
        weekly_metrics["week_start"].eq(selected_week)
    ].iloc[0]
    week_starts = tickets["created_at"].dt.to_period("W-SUN").dt.start_time
    week_tickets = tickets.loc[week_starts.eq(selected_week)].copy()

if "ai_classifications" not in st.session_state:
    st.session_state["ai_classifications"] = {}

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs([
    "📊 Tab 1: Weekly Complaint Digest",
    "🏆 Tab 2: Agent Leaderboards",
    "🔍 Tab 3: Repeat Contact Deep Dive"
])

# ==========================================
# TAB 1: WEEKLY COMPLAINT DIGEST
# ==========================================
with tab1:
    st.subheader("Weekly Customer Complaint Intelligence")
    if selected_week is not None:
        st.caption("AI classification is opt-in and runs only for the selected week, in batches of 25.")
        if st.button(f"Classify {len(week_tickets):,} tickets in this week with Gemini", disabled=week_tickets.empty):
            if not os.environ.get("GEMINI_API_KEY"):
                st.error("Set GEMINI_API_KEY in the environment before requesting classification.")
            else:
                updated = {}
                try:
                    with st.spinner("Classifying selected-week tickets..."):
                        for start in range(0, len(week_tickets), BATCH_SIZE):
                            batch = week_tickets.iloc[start:start + BATCH_SIZE]
                            results = classify_batch(batch.to_dict("records"))
                            updated.update({item["ticket_id"]: item for item in results})
                    st.session_state["ai_classifications"].update(updated)
                    st.success(f"Classified {len(updated):,} tickets across {(len(week_tickets) + BATCH_SIZE - 1) // BATCH_SIZE} API calls.")
                except Exception as error:
                    st.error(f"Classification stopped: {error}")

        classifications = st.session_state["ai_classifications"]
        week_categories = week_tickets["category"].copy()
        for row_index, ticket_id in week_tickets["ticket_id"].items():
            if str(ticket_id) in classifications:
                week_categories.at[row_index] = classifications[str(ticket_id)]["category"]
        classified_count = sum(str(ticket_id) in classifications for ticket_id in week_tickets["ticket_id"])
        st.caption(f"AI-labeled tickets: {classified_count:,} / {len(week_tickets):,}. Remaining categories use intake tags.")

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Tickets this week", f"{int(selected_week_metrics['total_tickets']):,}")
        kpi2.metric("Policy repeat rate", f"{selected_week_metrics['repeat_pct']:.1f}%")
        kpi3.metric("Repeat-contact cost", f"₹{selected_week_metrics['repeat_cost']:,.0f}")
        kpi4.metric("Filtered-period 30% target", f"₹{repeat_metrics['target_savings_per_quarter']:,.0f}/quarter")

        if not week_tickets.empty:
            col_left, col_right = st.columns([3, 2])
            with col_left:
                st.markdown("#### Complaint categories this week")
                category_frame = week_categories.value_counts().rename_axis("Category").reset_index(name="Tickets")
                fig_category = px.bar(
                    category_frame, x="Tickets", y="Category", orientation="h",
                    color="Tickets", color_continuous_scale="Blues", text="Tickets",
                )
                fig_category.update_layout(yaxis=dict(autorange="reversed"), height=380)
                st.plotly_chart(fig_category, width="stretch")
            with col_right:
                st.markdown("#### Channel mix")
                fig_channel = px.pie(
                    week_tickets, names="channel", hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig_channel.update_layout(height=380)
                st.plotly_chart(fig_channel, width="stretch")

            st.markdown("#### High-priority customer examples")
            high_priority = week_tickets[week_tickets["priority"].eq("High")].head(4)
            for row_index, (_, row) in enumerate(high_priority.iterrows()):
                with st.container():
                    st.markdown(
                        f"**{row['ticket_id']} · {row['category']} · {row['channel']}**  \n"
                        f"{str(row['customer_message'])[:220]}"
                    )
                    if row_index < len(high_priority) - 1:
                        st.divider()
    else:
        st.info("Choose a date range and channel with tickets to view a weekly digest.")

# ==========================================
# TAB 2: AGENT LEADERBOARDS
# ==========================================
with tab2:
    st.subheader("Support Agent Performance & Fair Evaluation")
    st.info("Tier 2 is excluded from both volume rankings. Policy §6 evaluates Tier 2 work by resolution duration.")
    weekly_leaderboards = build_leaderboards(week_tickets, agents)
    view_type = st.radio(
        "Leaderboard view",
        ["Tier 1 volume", "Tier 1 complexity score", "Team and Tier 2 duration"],
        horizontal=True,
    )
    if view_type == "Tier 1 volume":
        st.markdown("##### Tier 1 resolved tickets for the selected week")
        st.dataframe(
            weekly_leaderboards["raw_volume"].rename(columns={
                "name": "Agent Name", "team": "Team", "total_resolved": "Resolved Tickets",
                "avg_transfers": "Avg Transfer Hops",
            }),
            width="stretch",
        )
    elif view_type == "Tier 1 complexity score":
        st.markdown("##### Experimental Tier 1 complexity score for the selected week")
        st.caption("Heuristic: 1 + 0.5 for High priority + 0.3 per transfer. Not calibrated against handle-time data.")
        st.dataframe(
            weekly_leaderboards["weighted_score"].rename(columns={
                "name": "Agent Name", "team": "Team", "total_weighted_score": "Complexity Score",
                "total_resolved": "Resolved Tickets",
            }),
            width="stretch",
        )
    else:
        st.markdown("##### Team totals and Tier 2 resolution duration for the selected week")
        team_display = weekly_leaderboards["team_summary"].copy()
        team_display["volume_metric_applicable"] = team_display["volume_metric_applicable"].map(
            {True: "Yes (Tier 1)", False: "No (not Tier 1)"}
        )
        st.dataframe(
            team_display.rename(columns={
                "team": "Team", "tier": "Tier", "agent_count": "Agents",
                "total_tickets": "Resolved Tickets", "avg_tickets_per_agent": "Tickets / Agent",
                "avg_resolution_days": "Avg Resolution Days",
                "volume_metric_applicable": "May rank by volume?",
            }),
            width="stretch",
        )

# ==========================================
# TAB 3: REPEAT CONTACT DEEP DIVE
# ==========================================
with tab3:
    st.subheader("Repeat Contacts and Estimated Business Impact")
    st.caption("Repeat definition: same customer, canonical category and SKU, returning within 30 days after a valid resolution. Category + SKU is a proxy; the export has no issue ID.")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Weekly repeat rate")
        if not weekly_metrics.empty:
            fig_trend = px.line(
                weekly_metrics, x="week_start", y="repeat_pct", markers=True,
                labels={"week_start": "Week beginning", "repeat_pct": "Repeat rate (%)"},
            )
            fig_trend.update_layout(height=350)
            st.plotly_chart(fig_trend, width="stretch")
        else:
            st.caption("No weekly data for these filters.")
    with col_b:
        st.markdown("#### Products with most repeats in the filtered period")
        repeated_products = tickets.loc[tickets["is_repeat"], "product_sku"].value_counts().head(5)
        if not repeated_products.empty:
            products_frame = repeated_products.rename_axis("Product SKU").reset_index(name="Repeat Tickets")
            fig_products = px.bar(
                products_frame, x="Product SKU", y="Repeat Tickets", color="Repeat Tickets",
                color_continuous_scale="Reds", text="Repeat Tickets",
            )
            fig_products.update_layout(height=350)
            st.plotly_chart(fig_products, width="stretch")
        else:
            st.caption("No repeat contacts in this filtered period.")

    st.markdown("---")
    st.markdown("### Filtered-period cost estimate")
    st.caption("Quarterly figures are annualized from the selected date span; 30% deflection is a scenario, not a measured outcome.")
    calc_col1, calc_col2 = st.columns(2)
    with calc_col1:
        blended_cost = repeat_metrics["repeat_tickets"] * 290
        st.metric("Tickets in filtered period", f"{repeat_metrics['total_tickets']:,}")
        st.metric("Policy-defined repeats", f"{repeat_metrics['repeat_tickets']:,} ({repeat_metrics['repeat_pct']:.1f}%)")
        st.metric("Channel-costed repeat contacts", f"₹{repeat_metrics['total_waste']:,.0f}")
        st.caption(f"At the policy blended rate of ₹290/contact: ₹{blended_cost:,.0f} for this period.")
    with calc_col2:
        st.metric("Annualized repeat cost / quarter", f"₹{repeat_metrics['quarterly_waste']:,.0f}")
        st.metric("30% reduction scenario / quarter", f"₹{repeat_metrics['target_savings_per_quarter']:,.0f}")
        st.caption("Savings require a measured intervention. Gemini classification runs only when requested; account quotas and charges depend on Google AI billing settings.")