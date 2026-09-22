import streamlit as st
import pandas as pd
import plotly.express as px
import pandasai as pai
from pandasai_litellm.litellm import LiteLLM
import io
import time


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="E-Commerce Sales Analytics",
    page_icon="🛒",
    layout="wide"
)

# =========================================================
# THEME
# =========================================================
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

theme = st.sidebar.selectbox(
    "🎨 Dashboard Theme",
    ["Dark", "Light"],
    index=0 if st.session_state.theme == "Dark" else 1,
    key="theme_selector",
)
st.session_state.theme = theme
PLOTLY_TEMPLATE = "plotly_dark" if theme == "Dark" else "plotly_white"

st.markdown("""
<style>
[data-testid="stMetric"] { padding: 12px; border-radius: 10px; }
[data-testid="stSidebar"] { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# FILE PATH
# =========================================================

FILE_PATH = r"D:\E-Commerce Sales Analytics.csv"


# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data
def load_data():
    data = pd.read_csv(FILE_PATH)

    data["order_date"] = pd.to_datetime(
        data["order_date"],
        errors="coerce"
    )

    return data


df = load_data()


# =========================================================
# PANDASAI + LOCAL OLLAMA CONFIGURATION
# =========================================================
# @st.cache_resource ensures this only runs ONCE per server session
# instead of re-creating the LLM client + re-running pai.config.set()
# on every widget interaction (every filter change was doing this before).

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "ollama/llama3.2"


@st.cache_resource(show_spinner=False)
def get_llm_configured():
    llm = LiteLLM(
        model=OLLAMA_MODEL,
        api_base=OLLAMA_URL,
        # keep_alive keeps the model resident in Ollama's memory between
        # requests. Without this, Ollama can unload llama3.2 after each
        # call and pay a multi-second reload cost on the next question.
        keep_alive="30m",
        # NOTE: PandasAI's generated response includes a full code block
        # (imports, function def, execution, result assignment). A low
        # max_tokens cap truncates that code before the required
        # `result = {"type": ..., "value": ...}` line is emitted, which
        # is what causes the "Result must be in the format of dictionary"
        # error. Give it enough headroom instead of capping tightly.
        max_tokens=2048,
        temperature=0,
    )

    pai.config.set({
        "llm": llm,
        # Let PandasAI cache identical query+dataframe executions itself
        # (skips re-running generated code for repeated questions).
        "enable_cache": True,
    })

    return llm


# LLM is initialized lazily only when an AI question needs it.


# =========================================================
# TITLE
# =========================================================

st.title("🛒 E-Commerce Sales Analytics")

st.markdown(
    "### Interactive Sales Dashboard + 🤖 Local PandasAI"
)

st.caption(
    "Powered by Streamlit + PandasAI + LiteLLM + Ollama llama3.2"
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("🔎 Dashboard Filters")

category_options = sorted(df["product_category"].dropna().unique().tolist())

selected_categories = st.sidebar.multiselect(
    "Product Category",
    options=category_options,
    default=category_options,
)


region_options = sorted(df["region"].dropna().unique().tolist())

selected_regions = st.sidebar.multiselect(
    "Region",
    options=region_options,
    default=region_options,
)

# Cache keys need to be hashable/order-independent — a plain list would
# bust the cache on every rerun even when the same items are selected in
# a different order, so normalize to a sorted tuple.
category_key = tuple(sorted(selected_categories))
region_key = tuple(sorted(selected_regions))

# Human-readable labels for headers/captions/reports.
category_label = (
    "All" if set(selected_categories) == set(category_options)
    else ", ".join(selected_categories) if selected_categories
    else "None selected"
)
region_label = (
    "All" if set(selected_regions) == set(region_options)
    else ", ".join(selected_regions) if selected_regions
    else "None selected"
)


# ---------------------------------------------------------
# DATE RANGE
# ---------------------------------------------------------

data_min_date = df["order_date"].min()
data_max_date = df["order_date"].max()

start_date = None
end_date = None

if pd.notna(data_min_date) and pd.notna(data_max_date):
    min_date = data_min_date.date()
    max_date = data_max_date.date()

    date_col1, date_col2 = st.sidebar.columns(2)

    with date_col1:
        start_date = st.date_input(
            "📅 Start Date",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
            key="start_date_picker",
        )

    with date_col2:
        end_date = st.date_input(
            "📅 End Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            key="end_date_picker",
        )

    if start_date > end_date:
        st.sidebar.error("⚠️ Start Date cannot be after End Date.")
        start_date, end_date = end_date, start_date

    if st.sidebar.button("↺ Reset dates", use_container_width=True):
        st.session_state.start_date_picker = min_date
        st.session_state.end_date_picker = max_date
        st.rerun()


# =========================================================
# FILTER DATA
# =========================================================
# Cached on the filter selections. Streamlit reruns the whole script on
# every interaction (including every chat message), so without this the
# filter + all downstream groupbys were being recomputed even when the
# user was just asking the AI a question, not touching a filter.

@st.cache_data(show_spinner=False)
def get_filtered_data(categories, regions, start, end):
    result = df

    if categories:
        result = result[result["product_category"].isin(categories)]
    else:
        result = result.iloc[0:0]

    if regions:
        result = result[result["region"].isin(regions)]
    else:
        result = result.iloc[0:0]

    if start is not None and end is not None:
        result = result[
            (result["order_date"] >= pd.Timestamp(start))
            & (result["order_date"] <= pd.Timestamp(end))
        ]

    return result


filtered_df = get_filtered_data(category_key, region_key, start_date, end_date)

if filtered_df.empty:
    st.warning(
        "No data matches the current filters. Select at least one "
        "category and region, and check the date range."
    )
    st.stop()


# =========================================================
# KPI SECTION
# =========================================================

total_revenue = filtered_df["revenue"].sum()
total_orders = len(filtered_df)
avg_rating = filtered_df["customer_rating"].mean()
avg_delivery = filtered_df["delivery_days"].mean()


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "💰 Total Revenue",
        f"${total_revenue:,.2f}"
    )

with col2:
    st.metric(
        "📦 Total Orders",
        f"{total_orders:,}"
    )

with col3:
    st.metric(
        "⭐ Avg Rating",
        f"{avg_rating:.2f}"
    )

with col4:
    st.metric(
        "🚚 Avg Delivery Days",
        f"{avg_delivery:.2f}"
    )


st.divider()


# =========================================================
# FILTERED RESULTS
# =========================================================

st.subheader("📊 Filtered Results")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Filtered Revenue",
        f"${filtered_df['revenue'].sum():,.2f}"
    )

with col2:
    st.metric(
        "Filtered Orders",
        f"{len(filtered_df):,}"
    )

with col3:
    st.metric(
        "Filtered Quantity",
        f"{filtered_df['quantity'].sum():,.0f}"
    )


st.divider()


# =========================================================
# REVENUE BY PRODUCT CATEGORY
# =========================================================

st.subheader("💰 Revenue by Product Category")


@st.cache_data(show_spinner=False)
def get_category_revenue(categories, regions, start, end):
    data = get_filtered_data(categories, regions, start, end)
    return (
        data
        .groupby("product_category", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
    )


category_revenue = get_category_revenue(category_key, region_key, start_date, end_date)

fig_category = px.bar(
    category_revenue,
    x="product_category",
    y="revenue",
    text_auto=".2s",
    title="Revenue by Product Category",
    template=PLOTLY_TEMPLATE
)

fig_category.update_layout(
    xaxis_title="Product Category",
    yaxis_title="Revenue"
)

st.plotly_chart(
    fig_category,
    use_container_width=True
)


# =========================================================
# TWO COLUMN CHARTS
# =========================================================

col1, col2 = st.columns(2)


# ---------------------------------------------------------
# REGION
# ---------------------------------------------------------

with col1:

    st.subheader("🌍 Revenue by Region")

    @st.cache_data(show_spinner=False)
    def get_region_revenue(categories, regions, start, end):
        data = get_filtered_data(categories, regions, start, end)
        return (
            data
            .groupby("region", as_index=False)["revenue"]
            .sum()
            .sort_values("revenue", ascending=False)
        )

    region_revenue = get_region_revenue(category_key, region_key, start_date, end_date)

    fig_region = px.bar(
        region_revenue,
        x="region",
        y="revenue",
        text_auto=".2s",
        title="Revenue by Region",
        template=PLOTLY_TEMPLATE
    )

    st.plotly_chart(
        fig_region,
        use_container_width=True
    )


# ---------------------------------------------------------
# PAYMENT METHOD
# ---------------------------------------------------------

with col2:

    st.subheader("💳 Revenue by Payment Method")

    @st.cache_data(show_spinner=False)
    def get_payment_revenue(categories, regions, start, end):
        data = get_filtered_data(categories, regions, start, end)
        return (
            data
            .groupby("payment_method", as_index=False)["revenue"]
            .sum()
            .sort_values("revenue", ascending=False)
        )

    payment_revenue = get_payment_revenue(category_key, region_key, start_date, end_date)

    fig_payment = px.pie(
        payment_revenue,
        names="payment_method",
        values="revenue",
        title="Revenue by Payment Method",
        template=PLOTLY_TEMPLATE
    )

    st.plotly_chart(
        fig_payment,
        use_container_width=True
    )


# =========================================================
# MONTHLY REVENUE
# =========================================================

st.subheader("📈 Monthly Revenue Trend")


@st.cache_data(show_spinner=False)
def get_monthly_revenue(categories, regions, start, end):
    data = get_filtered_data(categories, regions, start, end)
    return (
        data
        .dropna(subset=["order_date"])
        .set_index("order_date")
        .resample("ME")["revenue"]
        .sum()
        .reset_index()
    )


monthly_revenue = get_monthly_revenue(category_key, region_key, start_date, end_date)

fig_monthly = px.line(
    monthly_revenue,
    x="order_date",
    y="revenue",
    markers=True,
    title="Monthly Revenue",
    template=PLOTLY_TEMPLATE
)

fig_monthly.update_layout(
    xaxis_title="Month",
    yaxis_title="Revenue"
)

st.plotly_chart(
    fig_monthly,
    use_container_width=True
)


st.divider()


# =========================================================
# TOP-N LEADERBOARD
# =========================================================

st.subheader("🏆 Top-N Leaderboard")

top_n = st.slider("Number of top entries (N)", min_value=3, max_value=25, value=10)

leader_col1, leader_col2 = st.columns(2)


@st.cache_data(show_spinner=False)
def get_customer_leaderboard(categories, regions, start, end):
    data = get_filtered_data(categories, regions, start, end)
    return (
        data
        .groupby("customer_id", as_index=False)
        .agg(
            total_revenue=("revenue", "sum"),
            orders=("order_id", "count"),
            avg_rating=("customer_rating", "mean"),
        )
        .sort_values("total_revenue", ascending=False)
    )


@st.cache_data(show_spinner=False)
def get_category_leaderboard(categories, regions, start, end):
    data = get_filtered_data(categories, regions, start, end)
    return (
        data
        .groupby("product_category", as_index=False)
        .agg(
            total_revenue=("revenue", "sum"),
            units_sold=("quantity", "sum"),
            orders=("order_id", "count"),
            avg_rating=("customer_rating", "mean"),
        )
        .sort_values("total_revenue", ascending=False)
    )


customer_leaderboard = get_customer_leaderboard(
    category_key, region_key, start_date, end_date
)
category_leaderboard = get_category_leaderboard(
    category_key, region_key, start_date, end_date
)

with leader_col1:
    st.markdown("**👤 Top Customers by Revenue**")
    st.dataframe(
        customer_leaderboard.head(top_n).style.format({
            "total_revenue": "${:,.2f}",
            "avg_rating": "{:.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

with leader_col2:
    st.markdown("**📦 Top Categories by Revenue**")
    st.dataframe(
        category_leaderboard.head(top_n).style.format({
            "total_revenue": "${:,.2f}",
            "avg_rating": "{:.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )


st.divider()


# =========================================================
# YEAR-OVER-YEAR COMPARISON
# =========================================================

st.subheader("📆 Year-over-Year Comparison")

st.caption(
    "Uses the category/region filters but ignores the date range picker, "
    "so full years can be compared."
)


@st.cache_data(show_spinner=False)
def get_yearly_summary(categories, regions):
    data = get_filtered_data(categories, regions, None, None)
    data = data.dropna(subset=["order_date"]).copy()
    data["year"] = data["order_date"].dt.year

    yearly = (
        data
        .groupby("year", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "count"),
            avg_rating=("customer_rating", "mean"),
        )
        .sort_values("year")
    )

    yearly["yoy_growth_pct"] = yearly["revenue"].pct_change() * 100

    return yearly


yearly_summary = get_yearly_summary(category_key, region_key)

yoy_col1, yoy_col2 = st.columns([2, 1])

with yoy_col1:
    fig_yoy = px.bar(
        yearly_summary,
        x="year",
        y="revenue",
        text_auto=".2s",
        title="Revenue by Year",
        template=PLOTLY_TEMPLATE,
    )
    fig_yoy.update_layout(xaxis_title="Year", yaxis_title="Revenue")
    fig_yoy.update_xaxes(type="category")
    st.plotly_chart(fig_yoy, use_container_width=True)

with yoy_col2:
    st.markdown("**YoY Growth**")
    st.dataframe(
        yearly_summary[["year", "revenue", "yoy_growth_pct"]].style.format({
            "revenue": "${:,.0f}",
            "yoy_growth_pct": "{:+.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )


st.divider()


# =========================================================
# DELIVERY PERFORMANCE
# =========================================================

st.subheader("🚚 Delivery Performance")

late_threshold = st.slider(
    "Late delivery threshold (days)",
    min_value=int(filtered_df["delivery_days"].min()),
    max_value=int(filtered_df["delivery_days"].max()),
    value=min(7, int(filtered_df["delivery_days"].max())),
)

delivery_df = filtered_df.copy()
delivery_df["is_late"] = delivery_df["delivery_days"] > late_threshold

overall_late_rate = delivery_df["is_late"].mean() * 100

late_by_region = (
    delivery_df
    .groupby("region", as_index=False)["is_late"]
    .mean()
)
late_by_region["is_late"] = late_by_region["is_late"] * 100
late_by_region = late_by_region.rename(columns={"is_late": "late_rate_pct"})
late_by_region = late_by_region.sort_values("late_rate_pct", ascending=False)

delivery_col1, delivery_col2 = st.columns([1, 2])

with delivery_col1:
    st.metric("⏱️ Avg Delivery Days", f"{filtered_df['delivery_days'].mean():.2f}")
    st.metric(
        f"🐢 Orders Later Than {late_threshold}d",
        f"{overall_late_rate:.1f}%",
    )

with delivery_col2:
    fig_late = px.bar(
        late_by_region,
        x="region",
        y="late_rate_pct",
        text_auto=".1f",
        title=f"Late Delivery Rate by Region (> {late_threshold} days)",
        template=PLOTLY_TEMPLATE,
    )
    fig_late.update_layout(xaxis_title="Region", yaxis_title="Late Rate (%)")
    st.plotly_chart(fig_late, use_container_width=True)


st.divider()


# =========================================================
# DISCOUNT IMPACT ANALYSIS
# =========================================================

st.subheader("🏷️ Discount Impact Analysis")

st.caption(
    "No cost/margin data exists in this dataset, so this shows discount's "
    "effect on realized revenue and rating rather than true profit margin."
)

discount_df = filtered_df.copy()
discount_df["discount_bucket"] = pd.cut(
    discount_df["discount"],
    bins=[-0.001, 0.10, 0.20, 0.30, 1.0],
    labels=["0-10%", "10-20%", "20-30%", "30%+"],
)
discount_df["gross_revenue"] = discount_df["quantity"] * discount_df["unit_price"]
discount_df["discount_amount"] = discount_df["gross_revenue"] - discount_df["revenue"]

discount_summary = (
    discount_df
    .groupby("discount_bucket", as_index=False, observed=True)
    .agg(
        orders=("order_id", "count"),
        avg_order_revenue=("revenue", "mean"),
        total_discount_given=("discount_amount", "sum"),
        avg_rating=("customer_rating", "mean"),
    )
)

discount_col1, discount_col2 = st.columns(2)

with discount_col1:
    fig_discount_rev = px.bar(
        discount_summary,
        x="discount_bucket",
        y="avg_order_revenue",
        text_auto=".2s",
        title="Avg Order Revenue by Discount Tier",
        template=PLOTLY_TEMPLATE,
    )
    fig_discount_rev.update_layout(
        xaxis_title="Discount Tier", yaxis_title="Avg Revenue / Order"
    )
    st.plotly_chart(fig_discount_rev, use_container_width=True)

with discount_col2:
    fig_discount_rating = px.bar(
        discount_summary,
        x="discount_bucket",
        y="avg_rating",
        text_auto=".2f",
        title="Avg Customer Rating by Discount Tier",
        template=PLOTLY_TEMPLATE,
    )
    fig_discount_rating.update_layout(
        xaxis_title="Discount Tier", yaxis_title="Avg Rating"
    )
    st.plotly_chart(fig_discount_rating, use_container_width=True)

st.dataframe(
    discount_summary.style.format({
        "avg_order_revenue": "${:,.2f}",
        "total_discount_given": "${:,.2f}",
        "avg_rating": "{:.2f}",
    }),
    use_container_width=True,
    hide_index=True,
)


st.divider()


# =========================================================
# PERIOD-OVER-PERIOD COMPARISON (tied to the date range picker)
# =========================================================
# The Year-over-Year section above intentionally ignores the date filter
# so full calendar years stay comparable. This does the opposite: it
# compares your EXACT selected start/end window against the immediately
# preceding window of the same length, so picking a custom date range
# actually changes the insights below.

@st.cache_data(show_spinner=False)
def get_period_comparison(categories, regions, start, end):
    if start is None or end is None:
        return None

    period_days = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
    prior_end = pd.Timestamp(start) - pd.Timedelta(days=1)
    prior_start = prior_end - pd.Timedelta(days=period_days - 1)

    data_start = df["order_date"].min()

    if pd.isna(data_start) or prior_end < data_start:
        # Not enough history before the selected window to compare.
        return None

    prior_start = max(prior_start, data_start)

    current = get_filtered_data(categories, regions, start, end)
    prior = get_filtered_data(
        categories, regions, prior_start.date(), prior_end.date()
    )

    return {
        "current_revenue": current["revenue"].sum(),
        "current_orders": len(current),
        "current_rating": current["customer_rating"].mean() if len(current) else float("nan"),
        "prior_revenue": prior["revenue"].sum(),
        "prior_orders": len(prior),
        "prior_rating": prior["customer_rating"].mean() if len(prior) else float("nan"),
        "prior_start": prior_start.date(),
        "prior_end": prior_end.date(),
        "period_days": period_days,
    }


period_comparison = get_period_comparison(
    category_key, region_key, start_date, end_date
)


# =========================================================
# INSIGHTS, ALERTS & GROWTH FOCUS
# =========================================================
# Rule-based, computed from the real aggregations above for the CURRENT
# filters — not generic boilerplate text. Thresholds are relative to the
# data itself (gaps vs the leader, deviations from the overall average)
# rather than hardcoded absolute numbers, so this stays meaningful as
# filters/date range change.

def generate_business_insights(
    category_revenue, region_revenue, payment_revenue,
    late_by_region, discount_summary, yearly_summary,
    filtered_df, late_threshold, period_comparison,
    start_date, end_date,
):
    alerts = []      # (level, message) — level is "🔴" or "🟡"
    insights = []     # plain observations
    focus_areas = []  # actionable growth suggestions

    # --- Period-over-period revenue (respects the exact date range picked) ---
    if period_comparison is not None and period_comparison["prior_revenue"] > 0:
        cur_rev = period_comparison["current_revenue"]
        prior_rev = period_comparison["prior_revenue"]
        growth = (cur_rev - prior_rev) / prior_rev * 100

        period_label = f"{start_date} → {end_date}"
        prior_label = (
            f"{period_comparison['prior_start']} → "
            f"{period_comparison['prior_end']}"
        )

        if growth < -3:
            alerts.append((
                "🔴",
                f"Revenue for your selected period ({period_label}) is down "
                f"{abs(growth):.1f}% vs the prior equivalent period "
                f"({prior_label}): ${prior_rev:,.0f} → ${cur_rev:,.0f}."
            ))
        elif growth > 5:
            insights.append(
                f"Revenue for your selected period is up {growth:.1f}% vs "
                f"the prior equivalent period (${prior_rev:,.0f} → "
                f"${cur_rev:,.0f})."
            )
        else:
            insights.append(
                f"Revenue for your selected period is roughly flat vs the "
                f"prior equivalent period ({growth:+.1f}%)."
            )

        rating_diff = period_comparison["current_rating"] - period_comparison["prior_rating"]
        if pd.notna(rating_diff) and rating_diff < -0.2:
            alerts.append((
                "🟡",
                f"Average rating dropped {abs(rating_diff):.2f} points vs "
                f"the prior equivalent period "
                f"({period_comparison['prior_rating']:.2f} → "
                f"{period_comparison['current_rating']:.2f})."
            ))
    elif period_comparison is None and start_date is not None:
        insights.append(
            "Not enough order history before your selected start date to "
            "compute a period-over-period comparison — try a later start "
            "date or a shorter window."
        )

    # --- Revenue trend (guard against a partial/in-progress final year) ---
    if not yearly_summary.empty and len(yearly_summary) >= 2:
        median_orders = yearly_summary["orders"].median()
        complete_years = yearly_summary[yearly_summary["orders"] >= median_orders * 0.9]

        if len(complete_years) >= 2:
            latest = complete_years.iloc[-1]
            growth = latest["yoy_growth_pct"]

            if pd.notna(growth):
                if growth < -3:
                    alerts.append((
                        "🔴",
                        f"(Full-history) Revenue fell {abs(growth):.1f}% in "
                        f"{int(latest['year'])} vs the prior calendar year."
                    ))
                elif growth > 5:
                    insights.append(
                        f"(Full-history) Revenue grew {growth:.1f}% in "
                        f"{int(latest['year'])} — the strongest calendar-year "
                        f"gain on record."
                    )
                else:
                    insights.append(
                        f"(Full-history) Revenue was roughly flat in "
                        f"{int(latest['year'])} ({growth:+.1f}% YoY)."
                    )

        if len(yearly_summary) > len(complete_years):
            partial = yearly_summary.iloc[-1]
            insights.append(
                f"{int(partial['year'])} has only {int(partial['orders'])} orders "
                f"so far and looks like a partial year — exclude it from YoY "
                f"conclusions until it's complete."
            )

    # --- Category concentration ---
    if len(category_revenue) > 1:
        top_cat = category_revenue.iloc[0]
        bottom_cat = category_revenue.iloc[-1]
        gap_pct = (1 - bottom_cat["revenue"] / top_cat["revenue"]) * 100

        insights.append(
            f"**{top_cat['product_category']}** leads revenue at "
            f"${top_cat['revenue']:,.0f}."
        )

        if gap_pct > 30:
            focus_areas.append(
                f"**{bottom_cat['product_category']}** brings in {gap_pct:.0f}% "
                f"less revenue than the leading category "
                f"(**{top_cat['product_category']}**) — worth investigating "
                f"pricing, assortment, or promotion for this category."
            )

    # --- Region imbalance ---
    if len(region_revenue) > 1:
        top_region = region_revenue.iloc[0]
        bottom_region = region_revenue.iloc[-1]
        gap_pct = (1 - bottom_region["revenue"] / top_region["revenue"]) * 100

        if gap_pct > 25:
            focus_areas.append(
                f"**{bottom_region['region']}** trails **{top_region['region']}** "
                f"by {gap_pct:.0f}% in revenue — a candidate for expanded "
                f"marketing spend or regional promotions if demand exists."
            )

    # --- Delivery / logistics risk ---
    if not late_by_region.empty:
        worst = late_by_region.iloc[0]  # already sorted descending

        if worst["late_rate_pct"] > 40:
            alerts.append((
                "🔴",
                f"{worst['region']} has a {worst['late_rate_pct']:.0f}% "
                f"late-delivery rate (over {late_threshold} days) — "
                f"logistics risk worth prioritizing."
            ))
        elif worst["late_rate_pct"] > 30:
            alerts.append((
                "🟡",
                f"{worst['region']}'s late-delivery rate is elevated at "
                f"{worst['late_rate_pct']:.0f}%."
            ))

    # --- Payment channel concentration ---
    if not payment_revenue.empty:
        total_rev = payment_revenue["revenue"].sum()
        top_payment = payment_revenue.iloc[0]
        share = top_payment["revenue"] / total_rev * 100 if total_rev else 0

        if share > 40:
            insights.append(
                f"**{top_payment['payment_method']}** drives {share:.0f}% of "
                f"revenue — the dominant payment channel. Consider incentives "
                f"on other methods to reduce dependency risk."
            )

    # --- Discount effectiveness ---
    if len(discount_summary) > 1:
        lowest_disc = discount_summary.iloc[0]
        highest_disc = discount_summary.iloc[-1]
        rating_diff = highest_disc["avg_rating"] - lowest_disc["avg_rating"]

        if abs(rating_diff) < 0.15:
            focus_areas.append(
                f"Deep discounting isn't measurably improving satisfaction "
                f"(avg rating {highest_disc['avg_rating']:.2f} at the highest "
                f"discount tier vs {lowest_disc['avg_rating']:.2f} at the "
                f"lowest) while avg order revenue drops to "
                f"${highest_disc['avg_order_revenue']:,.0f} from "
                f"${lowest_disc['avg_order_revenue']:,.0f} — consider "
                f"tightening the deepest discount tier."
            )

    # --- Overall satisfaction watch ---
    if not filtered_df.empty:
        avg_rating_overall = filtered_df["customer_rating"].mean()

        if avg_rating_overall < 3.5:
            alerts.append((
                "🟡",
                f"Overall average customer rating is {avg_rating_overall:.2f}/5 "
                f"— below a healthy 3.5+ benchmark."
            ))

    return alerts, insights, focus_areas


st.header("📌 Business Insights & Alerts")

st.caption(
    f"Period comparison uses your selected range ({start_date} → {end_date}) "
    f"vs the equivalent prior period. Items marked '(Full-history)' use "
    f"complete calendar years regardless of the date picker."
)

alerts, biz_insights, focus_areas = generate_business_insights(
    category_revenue, region_revenue, payment_revenue,
    late_by_region, discount_summary, yearly_summary,
    filtered_df, late_threshold, period_comparison,
    start_date, end_date,
)

if alerts:
    for level, msg in alerts:
        if level == "🔴":
            st.error(msg)
        else:
            st.warning(msg)
else:
    st.success("No alerts triggered for the current filters — metrics look healthy.")

if biz_insights:
    with st.expander("💡 Key Insights", expanded=True):
        for msg in biz_insights:
            st.markdown(f"- {msg}")

if focus_areas:
    with st.expander("🎯 Growth Focus Areas", expanded=True):
        for msg in focus_areas:
            st.markdown(f"- {msg}")
else:
    st.caption("No specific growth-focus flags for the current filters.")


st.divider()

with st.expander("📋 View Sales Data"):

    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=400
    )



# =========================================================
# FUTURE REVENUE PREDICTION + AREAS TO FOCUS
# =========================================================

st.divider()
st.header("🔮 Future Revenue Prediction")

st.caption(
    "Forecasts monthly revenue from the historical data using a trend + "
    "calendar-month regression model. Predictions are estimates, not guarantees."
)

forecast_months = st.slider(
    "Forecast horizon (months)",
    min_value=3,
    max_value=12,
    value=6,
    step=1,
)

@st.cache_data(show_spinner=False)
def make_revenue_forecast(categories, regions, start, end, horizon):
    data = get_filtered_data(categories, regions, None, None).copy()
    data = data.dropna(subset=["order_date", "revenue"])

    if data.empty:
        return pd.DataFrame(), pd.DataFrame(), "No historical data available."

    monthly = (
        data.set_index("order_date")
        .resample("ME")["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"order_date": "month"})
    )

    # A forecast needs enough monthly observations to learn a trend.
    if len(monthly) < 6:
        return (
            monthly.assign(type="Actual"),
            pd.DataFrame(),
            "At least 6 months of historical data are recommended for forecasting."
        )

    monthly["month_num"] = range(len(monthly))
    monthly["calendar_month"] = monthly["month"].dt.month

    # Trend + month-of-year seasonality using one-hot encoding.
    month_dummies = pd.get_dummies(
        monthly["calendar_month"],
        prefix="m",
        dtype=float
    )

    X = pd.concat(
        [monthly[["month_num"]].astype(float), month_dummies],
        axis=1
    )
    y = monthly["revenue"].astype(float)

    # Use sklearn if available; otherwise fall back to a trend-only model.
    try:
        from sklearn.linear_model import LinearRegression

        model = LinearRegression()
        model.fit(X, y)

        future_dates = pd.date_range(
            monthly["month"].max() + pd.offsets.MonthEnd(1),
            periods=horizon,
            freq="ME"
        )

        future = pd.DataFrame({"month": future_dates})
        future["month_num"] = range(len(monthly), len(monthly) + horizon)
        future["calendar_month"] = future["month"].dt.month

        future_dummies = pd.get_dummies(
            future["calendar_month"],
            prefix="m",
            dtype=float
        )

        future_X = pd.concat(
            [future[["month_num"]].astype(float), future_dummies],
            axis=1
        )

        # Make training and future columns identical.
        future_X = future_X.reindex(columns=X.columns, fill_value=0)

        predictions = model.predict(future_X)
        predictions = pd.Series(predictions).clip(lower=0)

        forecast = future[["month"]].copy()
        forecast["predicted_revenue"] = predictions.values

        actual = monthly[["month", "revenue"]].copy()
        actual["type"] = "Actual"

        forecast_plot = forecast.rename(
            columns={"predicted_revenue": "revenue"}
        )
        forecast_plot["type"] = "Predicted"

        return actual, forecast_plot, None

    except Exception:
        # Dependency-safe fallback: linear trend only.
        import numpy as np

        slope, intercept = np.polyfit(
            monthly["month_num"],
            y,
            1
        )

        future_dates = pd.date_range(
            monthly["month"].max() + pd.offsets.MonthEnd(1),
            periods=horizon,
            freq="ME"
        )

        future_num = np.arange(
            len(monthly),
            len(monthly) + horizon
        )

        predictions = np.maximum(
            0,
            slope * future_num + intercept
        )

        actual = monthly[["month", "revenue"]].copy()
        actual["type"] = "Actual"

        forecast = pd.DataFrame({
            "month": future_dates,
            "revenue": predictions,
            "type": "Predicted"
        })

        return actual, forecast, None


actual_forecast, future_forecast, forecast_error = make_revenue_forecast(
    category_key,
    region_key,
    start_date,
    end_date,
    forecast_months,
)

if forecast_error:
    st.warning(f"⚠️ {forecast_error}")
else:
    forecast_col1, forecast_col2, forecast_col3 = st.columns(3)

    last_actual = actual_forecast["revenue"].iloc[-1]
    first_prediction = future_forecast["revenue"].iloc[0]
    total_predicted = future_forecast["revenue"].sum()

    expected_change = (
        (first_prediction - last_actual) / last_actual * 100
        if last_actual != 0 else 0
    )

    with forecast_col1:
        st.metric(
            "Last Actual Monthly Revenue",
            f"${last_actual:,.0f}"
        )

    with forecast_col2:
        st.metric(
            "Next Month Predicted Revenue",
            f"${first_prediction:,.0f}",
            f"{expected_change:+.1f}%"
        )

    with forecast_col3:
        st.metric(
            f"Next {forecast_months} Months Forecast",
            f"${total_predicted:,.0f}"
        )

    forecast_chart_df = pd.concat(
        [
            actual_forecast.assign(revenue_type="Actual"),
            future_forecast.assign(revenue_type="Predicted"),
        ],
        ignore_index=True,
    )

    fig_forecast = px.line(
        forecast_chart_df,
        x="month",
        y="revenue",
        color="revenue_type",
        markers=True,
        title="Actual vs Predicted Monthly Revenue",
        template=PLOTLY_TEMPLATE,
    )

    fig_forecast.update_layout(
        xaxis_title="Month",
        yaxis_title="Revenue",
        legend_title="Series",
    )

    st.plotly_chart(
        fig_forecast,
        use_container_width=True
    )

    st.subheader("📋 Future Revenue Forecast")

    forecast_table = future_forecast[
        ["month", "revenue"]
    ].copy()

    forecast_table["month"] = forecast_table["month"].dt.strftime("%b %Y")
    forecast_table = forecast_table.rename(
        columns={
            "month": "Month",
            "revenue": "Predicted Revenue",
        }
    )

    st.dataframe(
        forecast_table.style.format({
            "Predicted Revenue": "${:,.2f}"
        }),
        use_container_width=True,
        hide_index=True,
    )

    if expected_change > 5:
        st.success(
            f"📈 **Positive outlook:** the next month's predicted revenue is "
            f"{expected_change:.1f}% above the latest actual month."
        )
    elif expected_change < -5:
        st.error(
            f"📉 **Risk signal:** the next month's predicted revenue is "
            f"{abs(expected_change):.1f}% below the latest actual month."
        )
    else:
        st.info(
            f"➡️ **Stable outlook:** the next month's predicted revenue is "
            f"{expected_change:+.1f}% versus the latest actual month."
        )


# =========================================================
# DATA-DRIVEN AREAS TO FOCUS
# =========================================================

st.subheader("🎯 Areas to Focus")

st.caption(
    "These recommendations are calculated from the current filtered data. "
    "They are business signals, not guarantees."
)

focus_messages = []

# 1. Category opportunity
if len(category_revenue) >= 2:
    top_category = category_revenue.iloc[0]
    weak_category = category_revenue.iloc[-1]

    category_gap = (
        (top_category["revenue"] - weak_category["revenue"])
        / top_category["revenue"] * 100
        if top_category["revenue"] else 0
    )

    if category_gap > 30:
        focus_messages.append(
            (
                "🔴",
                "Product Category",
                f"{weak_category['product_category']} is {category_gap:.0f}% "
                f"below the leading category "
                f"({top_category['product_category']}). Review assortment, "
                f"pricing and promotion before increasing investment."
            )
        )
    else:
        focus_messages.append(
            (
                "🟢",
                "Product Category",
                f"{top_category['product_category']} is the current revenue "
                f"leader. Protect its stock availability and consider "
                f"cross-selling with weaker categories."
            )
        )

# 2. Regional opportunity
if len(region_revenue) >= 2:
    top_region = region_revenue.iloc[0]
    weak_region = region_revenue.iloc[-1]

    region_gap = (
        (top_region["revenue"] - weak_region["revenue"])
        / top_region["revenue"] * 100
        if top_region["revenue"] else 0
    )

    if region_gap > 25:
        focus_messages.append(
            (
                "🟡",
                "Region",
                f"{weak_region['region']} trails {top_region['region']} "
                f"by {region_gap:.0f}% in revenue. Test targeted regional "
                f"offers and marketing before scaling spend."
            )
        )

# 3. Delivery risk
if not late_by_region.empty:
    worst_delivery = late_by_region.iloc[0]

    if worst_delivery["late_rate_pct"] > 30:
        focus_messages.append(
            (
                "🔴",
                "Delivery",
                f"{worst_delivery['region']} has a "
                f"{worst_delivery['late_rate_pct']:.1f}% late-delivery rate "
                f"using the current {late_threshold}-day threshold. "
                f"Prioritize logistics and fulfillment improvement."
            )
        )
    else:
        focus_messages.append(
            (
                "🟢",
                "Delivery",
                f"The highest regional late-delivery rate is "
                f"{worst_delivery['late_rate_pct']:.1f}%, so delivery does "
                f"not currently appear to be the highest-priority risk."
            )
        )

# 4. Discount strategy
if len(discount_summary) >= 2:
    lowest_discount = discount_summary.iloc[0]
    highest_discount = discount_summary.iloc[-1]

    revenue_change = (
        (
            highest_discount["avg_order_revenue"]
            - lowest_discount["avg_order_revenue"]
        )
        / lowest_discount["avg_order_revenue"] * 100
        if lowest_discount["avg_order_revenue"] else 0
    )

    rating_change = (
        highest_discount["avg_rating"]
        - lowest_discount["avg_rating"]
    )

    if revenue_change < -10 and abs(rating_change) < 0.20:
        focus_messages.append(
            (
                "🟡",
                "Discount Strategy",
                f"The highest discount tier has {abs(revenue_change):.1f}% "
                f"lower average order revenue while customer rating changes "
                f"by only {rating_change:+.2f}. Consider reducing deep discounts."
            )
        )

# 5. Revenue forecast
if not forecast_error and not future_forecast.empty:
    forecast_last = future_forecast["revenue"].iloc[-1]
    forecast_first = future_forecast["revenue"].iloc[0]

    forecast_change = (
        (forecast_last - forecast_first)
        / forecast_first * 100
        if forecast_first != 0 else 0
    )

    if forecast_change > 5:
        focus_messages.append(
            (
                "🟢",
                "Future Growth",
                f"The model estimates approximately {forecast_change:.1f}% "
                f"growth from the first to the last forecast month. "
                f"Prepare inventory and marketing capacity for potential demand."
            )
        )
    elif forecast_change < -5:
        focus_messages.append(
            (
                "🔴",
                "Future Risk",
                f"The model estimates approximately {abs(forecast_change):.1f}% "
                f"decline from the first to the last forecast month. "
                f"Review weak categories, regions and pricing before increasing spend."
            )
        )
    else:
        focus_messages.append(
            (
                "🟡",
                "Future Trend",
                "The forecast is relatively stable. Focus on improving "
                "conversion, delivery and average order value rather than "
                "assuming strong organic growth."
            )
        )

if focus_messages:
    for level, title, message in focus_messages:
        if level == "🔴":
            st.error(f"**{title}:** {message}")
        elif level == "🟡":
            st.warning(f"**{title}:** {message}")
        else:
            st.success(f"**{title}:** {message}")
else:
    st.info("No focus areas were triggered for the current filters.")



# =========================================================
# DOWNLOAD FILTERED DATA
# =========================================================

st.subheader("⬇️ Export")

export_col1, export_col2, export_col3 = st.columns(3)

with export_col1:

    csv_data = filtered_df.to_csv(index=False)

    st.download_button(
        label="⬇️ CSV",
        data=csv_data,
        file_name="filtered_sales_data.csv",
        mime="text/csv",
        use_container_width=True,
    )

with export_col2:

    try:
        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Filtered Data")

        st.download_button(
            label="⬇️ Excel",
            data=excel_buffer.getvalue(),
            file_name="filtered_sales_data.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
            use_container_width=True,
        )
    except ImportError:
        st.caption("Run `pip install openpyxl` to enable Excel export.")

with export_col3:

    summary_report = f"""E-COMMERCE SALES ANALYTICS — SUMMARY REPORT
Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

FILTERS
  Category   : {category_label}
  Region     : {region_label}
  Date range : {start_date} to {end_date}

KEY METRICS
  Total Revenue        : ${total_revenue:,.2f}
  Total Orders         : {total_orders:,}
  Average Rating       : {avg_rating:.2f}
  Average Delivery Days: {avg_delivery:.2f}

TOP PERFORMERS
  Top Category       : {category_revenue.iloc[0]['product_category']} \
(${category_revenue.iloc[0]['revenue']:,.2f})
  Top Region         : {region_revenue.iloc[0]['region']} \
(${region_revenue.iloc[0]['revenue']:,.2f})
  Top Payment Method : {payment_revenue.iloc[0]['payment_method']} \
(${payment_revenue.iloc[0]['revenue']:,.2f})
"""

    st.download_button(
        label="⬇️ Summary (.txt)",
        data=summary_report,
        file_name="sales_summary_report.txt",
        mime="text/plain",
        use_container_width=True,
    )


st.divider()


# =========================================================
# PANDASAI AI ANALYST
# =========================================================

chat_header_col1, chat_header_col2 = st.columns([5, 1])

with chat_header_col1:
    st.header("🤖 Ask Your Data")

with chat_header_col2:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.qa_cache = {}
        st.rerun()

st.markdown(
    "Ask questions about your **E-Commerce Sales Analytics** data, "
    "or tap a quick question below."
)

quick_questions = [
    "Total revenue by product category?",
    "Highest revenue category?",
    "Revenue by region?",
    "Average customer rating?",
    "Top payment method by revenue?",
    "Show monthly revenue",
]

quick_cols = st.columns(3)

for idx, q in enumerate(quick_questions):
    with quick_cols[idx % 3]:
        if st.button(q, key=f"quick_q_{idx}", use_container_width=True):
            st.session_state.pending_question = q


# =========================================================
# FAST PATH: ANSWER COMMON QUESTIONS WITHOUT THE LLM
# =========================================================
# The example questions above are simple lookups against aggregations we
# already computed for the charts. Routing them through a local 3B model
# on CPU is slow (minutes) and occasionally non-compliant with PandasAI's
# required output format. Answer them directly and instantly here, and
# only fall back to PandasAI/Ollama for questions that don't match.

def try_fast_path(question):
    q = question.strip().lower()

    if "category" in q and "revenue" in q:
        if "highest" in q or "most" in q or "top" in q:
            top = category_revenue.iloc[0]
            return (
                f"**{top['product_category']}** has the highest revenue "
                f"at **${top['revenue']:,.2f}**."
            )
        return {"type": "dataframe", "value": category_revenue}

    if "region" in q and "revenue" in q:
        return {"type": "dataframe", "value": region_revenue}

    if "payment" in q and "revenue" in q:
        if "most" in q or "highest" in q or "top" in q:
            top = payment_revenue.iloc[0]
            return (
                f"**{top['payment_method']}** generates the most revenue "
                f"at **${top['revenue']:,.2f}**."
            )
        return {"type": "dataframe", "value": payment_revenue}

    if "rating" in q and ("average" in q or "avg" in q):
        return f"The average customer rating is **{avg_rating:.2f}** / 5."

    if "monthly" in q and "revenue" in q:
        return {"type": "dataframe", "value": monthly_revenue}

    return None


# =========================================================
# CREATE PANDASAI DATAFRAME
# =========================================================

@st.cache_resource
def create_pandasai_dataframe():

    pandasai_df = pai.DataFrame(df)

    return pandasai_df


# PandasAI dataframe is created only when a question needs the LLM.


# =========================================================
# CHAT HISTORY
# =========================================================

if "messages" not in st.session_state:

    st.session_state.messages = []

if "qa_cache" not in st.session_state:

    # Manual cache of question -> answer for this session. PandasAI's own
    # enable_cache handles its generated-code cache, but this catches the
    # exact-repeat case instantly without even calling into pandasai.
    st.session_state.qa_cache = {}


# =========================================================
# DISPLAY PREVIOUS CHAT
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        content = message["content"]

        if isinstance(content, dict):

            if content.get("type") == "dataframe":

                st.dataframe(
                    content["value"],
                    use_container_width=True
                )

            else:

                st.write(content)

        else:

            st.write(content)

        if message.get("meta"):
            st.caption(message["meta"])


# =========================================================
# CHAT INPUT
# =========================================================

user_question = st.chat_input(
    "Ask a question about your sales data..."
)

if st.session_state.get("pending_question"):
    user_question = st.session_state.pending_question
    st.session_state.pending_question = None


# =========================================================
# PANDASAI CHAT
# =========================================================

if user_question:

    # Show user message

    st.session_state.messages.append({
        "role": "user",
        "content": user_question
    })

    with st.chat_message("user"):
        st.write(user_question)


    # AI response

    with st.chat_message("assistant"):

        with st.spinner(
            "🤖 Ollama llama3.2 is analyzing your data..."
        ):

            try:

                start_time = time.time()
                cache_key = user_question.strip().lower()
                fast_result = try_fast_path(user_question)

                if fast_result is not None:
                    result = fast_result
                    answer_source = "⚡ instant lookup"

                elif cache_key in st.session_state.qa_cache:
                    result = st.session_state.qa_cache[cache_key]
                    answer_source = "⚡ cached answer"

                else:
                    llm = get_llm_configured()
                    pandasai_df = create_pandasai_dataframe()

                    # Local small models occasionally drop the required
                    # `result = {...}` line on the first try. One retry
                    # is cheap relative to how often it recovers.
                    last_error = None
                    result = None

                    for attempt in range(2):
                        try:
                            result = pandasai_df.chat(user_question)
                            break
                        except Exception as chat_err:
                            last_error = chat_err

                    if result is None:
                        raise last_error

                    st.session_state.qa_cache[cache_key] = result
                    answer_source = "🤖 Ollama llama3.2"

                elapsed = time.time() - start_time

                # -------------------------------------------------
                # PandasAI dataframe result
                # -------------------------------------------------

                if isinstance(result, dict):

                    if result.get("type") == "dataframe":

                        result_df = result.get("value")

                        st.dataframe(
                            result_df,
                            use_container_width=True
                        )

                    elif result.get("type") == "plot":

                        st.write(result)

                    else:

                        st.write(result)


                # -------------------------------------------------
                # PandasAI normal result
                # -------------------------------------------------

                else:

                    st.write(result)


                # Save response

                st.caption(f"{answer_source} · {elapsed:.2f}s")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result,
                    "meta": f"{answer_source} · {elapsed:.2f}s",
                })


            except Exception as e:

                error_message = f"""
❌ PandasAI/Ollama error:

{e}

Please make sure Ollama is running and that
`llama3.2` is installed.
"""

                st.error(error_message)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🟢 Local AI | Ollama llama3.2 | PandasAI | No OpenAI API required"
)