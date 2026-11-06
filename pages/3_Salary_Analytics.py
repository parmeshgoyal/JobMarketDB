"""
JobMarketDB — Module 3: Salary Analytics & Outlier Audit (Phase 7 Stage 5)
Page: pages/3_Salary_Analytics.py

A publication-grade executive compensation intelligence dashboard designed in accordance
with the premium Sage & Ivory commercial SaaS visual direction:
- Editorial Hero Header: Category eyebrow, serif title, live dataset scope
- Asymmetric Executive KPI Grid: Primary LinkedIn continuous compensation card + supporting Indeed & outlier cards
- Central Tendency Breakdown: Unadjusted vs Threshold-adjusted (≤ $1M) statistics
- 5 Deep-Dive Distribution Tabs: Histogram, Salary Buckets, Experience Level, Job Title, State Geography
- Dual Analytical Panels: Pay Period Multipliers & Outlier Audit Classification (38 records > $1M)
- Data Provenance Disclosures: Transparent missing salary and outlier treatment policies
"""

import html
import os
import sys
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is available for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService
from utils.ui_components import (
    load_custom_css,
    render_editorial_header,
    render_editorial_stat_card,
    render_editorial_callout,
    render_empty_state,
    render_error_state,
)
from utils.plots import (
    apply_theme,
    create_empty_chart,
    THEME,
)

# -----------------------------------------------------------------------------
# 1. Page Configuration & Editorial CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Salary Analytics — JobMarketDB",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_custom_css()

# -----------------------------------------------------------------------------
# 2. Service Client & Cached Data Loaders
# -----------------------------------------------------------------------------
@st.cache_resource
def get_analytics_service() -> Optional[JobMarketAnalyticsService]:
    """Provides cached database analytics service instance."""
    try:
        if not verify_connection(timeout_ms=3000):
            return None
        db = get_database()
        return JobMarketAnalyticsService(db)
    except Exception:
        return None


@st.cache_data(ttl=300)
def load_salary_overview_cached() -> Optional[Dict[str, Any]]:
    service = get_analytics_service()
    return service.get_salary_overview() if service else None


@st.cache_data(ttl=300)
def load_bucket_distribution_cached() -> Optional[Dict[str, Any]]:
    service = get_analytics_service()
    return service.get_salary_distribution() if service else None


@st.cache_data(ttl=300)
def load_experience_salary_cached() -> Optional[Dict[str, Any]]:
    service = get_analytics_service()
    return service.get_salary_by_experience() if service else None


@st.cache_data(ttl=300)
def load_state_salary_cached(limit: int = 15) -> Optional[Dict[str, Any]]:
    service = get_analytics_service()
    return service.get_salary_by_state(limit=limit) if service else None


@st.cache_data(ttl=300)
def load_title_salary_cached(limit: int = 20) -> Optional[Dict[str, Any]]:
    service = get_analytics_service()
    return service.get_salary_by_title(limit=limit) if service else None


@st.cache_data(ttl=300)
def load_histogram_cached(source: str = "linkedin") -> Optional[Dict[str, Any]]:
    service = get_analytics_service()
    return service.get_salary_histogram(source=source) if service else None


service = get_analytics_service()

# -----------------------------------------------------------------------------
# 3. Editorial Page Header
# -----------------------------------------------------------------------------
render_editorial_header(
    title="Salary Distributions & Outlier Audit",
    subtitle=(
        "Comprehensive compensation analysis across 36,059 LinkedIn continuous records and "
        "5,715 Indeed derived midpoints. Platform-separated methodology with full outlier transparency."
    ),
    eyebrow="COMPENSATION & MACRO INTELLIGENCE",
    badge_text="Module 3",
    status_text="Dual Compensation Taxonomies",
)

if not service:
    render_error_state(
        title="Database Connection Failure",
        message="Unable to connect to local MongoDB at mongodb://localhost:27017/jobmarketdb. Please ensure MongoDB service is active."
    )
    st.stop()


# -----------------------------------------------------------------------------
# 4. Critical Methodology Disclosure (Editorial Callout)
# -----------------------------------------------------------------------------
render_editorial_callout(
    title="Methodology Note: LinkedIn and Indeed Use Incompatible Salary Fields",
    text=(
        "<b>LinkedIn</b> (123,835 postings): <code>salary.normalized_annual</code> represents reported compensation "
        "normalized to annual equivalents (50.1% annualized from HOURLY, MONTHLY, WEEKLY, or BIWEEKLY pay periods). "
        "<b>29.12% of LinkedIn postings (36,059)</b> have a salary annotation. The remaining 70.88% are excluded.<br><br>"
        "<b>Indeed</b> (5,715 postings): <code>salary.normalized_annual</code> is NULL for 100% of Indeed records. "
        "Instead, Indeed provides <code>salary.estimated_midpoint</code> — a DERIVED midpoint from discrete QUERY_BUCKET "
        "salary search bands. This is NOT an observed/stated salary value.<br><br>"
        "<b>These two figures are never combined.</b> Each platform is analysed independently below."
    ),
    callout_type="warning",
    eyebrow="Data Provenance Safeguard",
)

st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 5. Data Loading & Asymmetric Executive KPI Grid
# -----------------------------------------------------------------------------
with st.spinner("Loading authentic compensation data from MongoDB…"):
    try:
        overview = load_salary_overview_cached()
        if not overview:
            render_error_state("Data Retrieval Error", "Unable to load salary overview metrics.")
            st.stop()
        li = overview["linkedin"]
        ind = overview["indeed"]
        outlier_audit = overview["outlier_audit"]
    except Exception as exc:
        render_error_state("Failed to load salary analytics", str(exc))
        st.stop()

# Asymmetric Grid: Primary Large Insight Card (left) + Stacked Supporting Cards (right)
grid_col_left, grid_col_right = st.columns([1.85, 1.15])

with grid_col_left:
    adj_mean_val = li["threshold_adjusted"]["mean"]
    unadj_mean_val = li["unadjusted"]["mean"]
    adj_med_val = li["threshold_adjusted"]["approx_median"]
    adj_count = li["threshold_adjusted"]["count"]
    outlier_count = outlier_audit.get("total_outliers", 38)

    st.markdown(
        f"""
        <div class="jmdb-card" style="padding: 1.5rem; height: 100%;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">
                    PRIMARY BENCHMARK // OBSERVED CONTINUOUS COMPENSATION
                </div>
                <span class="jmdb-badge jmdb-badge-linkedin">LinkedIn (N = 36,059)</span>
            </div>
            <div style="font-size: 0.92rem; color: #4A524D; margin-bottom: 0.25rem;">
                Threshold-Adjusted Mean Annual Salary (≤ $1,000,000)
            </div>
            <div style="font-size: 2.75rem; font-weight: 800; color: #1C1F1D; font-family: 'Newsreader', serif; line-height: 1.1; margin-bottom: 0.65rem;">
                ${adj_mean_val:,.0f} <span style="font-size: 1rem; font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 600; color: #6E856C;">/ year</span>
            </div>
            <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.45; margin-bottom: 1.25rem;">
                Calculated across <b>{adj_count:,}</b> authentic LinkedIn records excluding <b>{outlier_count}</b> extreme 
                outliers (> $1M). The unadjusted mean of <b>${unadj_mean_val:,.0f}</b> is distorted by +${(unadj_mean_val - adj_mean_val):,.0f} (+{((unadj_mean_val - adj_mean_val)/adj_mean_val*100):.1f}%) 
                due to hourly conversion artifacts and entry anomalies.
            </p>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; border-top: 1px solid #E2DDD5; padding-top: 1rem;">
                <div>
                    <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: #737D76;">Approx. Median</div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #2E3A2D; font-family: 'JetBrains Mono', monospace;">${adj_med_val:,.0f}</div>
                    <div style="font-size: 0.74rem; color: #4A524D;">Robust metric</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: #737D76;">Observed Range</div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #2E3A2D; font-family: 'JetBrains Mono', monospace;">${li['unadjusted']['min_val']:,.0f}–$1M+</div>
                    <div style="font-size: 0.74rem; color: #4A524D;">Stated bounds</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: #737D76;">Pay Period Mix</div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #2E3A2D; font-family: 'JetBrains Mono', monospace;">50.1% Annualized</div>
                    <div style="font-size: 0.74rem; color: #4A524D;">Hourly / Monthly</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with grid_col_right:
    im = ind["estimated_midpoint"]
    ind_mean = im.get("mean", 0)
    ind_med = im.get("approx_median", 0)
    ind_count = ind.get("postings_with_estimated_midpoint", 5715)

    render_editorial_stat_card(
        title="Indeed Derived Midpoints",
        value=f"${ind_med:,.0f}" if ind_med else "N/A",
        subtitle=f"Mean: ${ind_mean:,.0f} · N = {ind_count:,} jobs",
        delta="100% Query-Bucket Derived",
        delta_type="positive",
    )

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    render_editorial_stat_card(
        title="Salary Information Coverage",
        value="32.24%",
        subtitle="41,774 / 129,550 total postings with pay data",
        delta="87,776 Unstated Excluded",
        delta_type="positive",
    )

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    render_editorial_stat_card(
        title="Outlier Audit Classification",
        value=f"{outlier_count} Postings > $1M",
        subtitle="19 hourly artifacts · 10 entry errors · 8 unresolved",
        delta="Source Preserved (Read-Only)",
        delta_type="positive",
    )

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 6. Central Tendency Breakdown (Side-by-Side Analytical Panels)
# -----------------------------------------------------------------------------
st.markdown("## 📈 Central Tendency & Empirical Distribution")
st.markdown(
    "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.4rem; margin-bottom: 1.25rem;'>"
    "Contrasting observed continuous compensation (LinkedIn) with search-band derived midpoints (Indeed)."
    "</p>",
    unsafe_allow_html=True,
)

ct_col1, ct_col2 = st.columns(2)

with ct_col1:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; margin-bottom: 0.75rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <h4 style="margin: 0; font-family: 'Newsreader', serif; font-size: 1.18rem; color: #1C1F1D;">
                    LinkedIn Continuous Compensation Metrics
                </h4>
                <span class="jmdb-badge jmdb-badge-linkedin">Observed Base Pay</span>
            </div>
            <p style="font-size: 0.86rem; color: #4A524D; margin-bottom: 0.75rem;">
                Comparison between unadjusted population (including 38 extreme outliers > $1M) and threshold-adjusted metrics (≤ $1M).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uc1, uc2, uc3 = st.columns(3)
    with uc1:
        st.metric("Adjusted Mean (≤ $1M)", f"${li['threshold_adjusted']['mean']:,.0f}", delta=f"-${(unadj_mean_val - adj_mean_val):,.0f} vs unadjusted")
    with uc2:
        st.metric("Approx. Median", f"${li['threshold_adjusted']['approx_median']:,.0f}")
    with uc3:
        st.metric("Valid Postings", f"{li['threshold_adjusted']['count']:,}", delta=f"-{outlier_count} outliers")

    st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)
    st.caption(f"Unadjusted Mean: ${unadj_mean_val:,.0f} | Range: ${li['unadjusted']['min_val']:,.0f} – ${li['unadjusted']['max_val']:,.0f}")

with ct_col2:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; margin-bottom: 0.75rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <h4 style="margin: 0; font-family: 'Newsreader', serif; font-size: 1.18rem; color: #1C1F1D;">
                    Indeed Derived Midpoint Metrics
                </h4>
                <span class="jmdb-badge jmdb-badge-indeed">Query-Bucket Midpoint</span>
            </div>
            <p style="font-size: 0.86rem; color: #4A524D; margin-bottom: 0.75rem;">
                Analytical midpoints derived from pre-filtered search bands ($15k–$30k interval width). 0 observed base salaries.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        st.metric("Derived Midpoint Mean", f"${im['mean']:,.0f}")
    with ic2:
        st.metric("Derived Median", f"${im['approx_median']:,.0f}")
    with ic3:
        st.metric("Midpoint Postings", f"{ind['postings_with_estimated_midpoint']:,}", delta="100% of Indeed")

    st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)
    st.caption(f"Midpoint Search Band Range: ${im['min_val']:,.0f} – ${im['max_val']:,.0f}")

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 7. Deep-Dive Distribution Analytics (5 Spacious Tabs)
# -----------------------------------------------------------------------------
st.markdown("## 🔬 Deep-Dive Distribution Analytics")
st.markdown(
    "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.4rem; margin-bottom: 1.25rem;'>"
    "Multi-dimensional drilldowns examining compensation density, standardized bucket distributions, experience levels, titles, and states."
    "</p>",
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Salary Histogram & Density",
    "🪣 Canonical Salary Buckets",
    "🎓 Compensation by Experience Level",
    "🗂️ Compensation by Job Title",
    "🗺️ Geographic Compensation by State",
])

# ── Tab 1: Histogram ──────────────────────────────────────────────────────────
with tab1:
    st.markdown("### Salary Distribution Histogram & Central Tendency")
    hist_platform = st.radio(
        "Select Sourcing Platform",
        options=["LinkedIn (Observed Continuous Compensation)", "Indeed (Derived Midpoint)"],
        horizontal=True,
        key="hist_platform",
    )
    source_key = "linkedin" if "LinkedIn" in hist_platform else "indeed"

    with st.spinner("Loading distribution values from MongoDB…"):
        try:
            hist_data = load_histogram_cached(source_key)
        except Exception as e:
            render_error_state("Failed to load histogram", str(e))
            hist_data = None

    if hist_data and hist_data.get("values"):
        values = hist_data["values"]
        n = hist_data["count"]
        stats = hist_data["stats"]

        bar_color = THEME["linkedin_blue"] if source_key == "linkedin" else THEME["indeed_blue"]

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=values,
            nbinsx=40,
            name=hist_data["value_label"],
            marker=dict(
                color=bar_color,
                line=dict(color="rgba(46, 58, 45, 0.15)", width=0.5),
            ),
            opacity=0.88,
            hovertemplate="Salary: %{x:$,.0f}<br>Count: %{y:,}<extra></extra>",
        ))

        # Vertical line annotations for mean and median
        if stats["mean"]:
            fig.add_vline(
                x=stats["mean"],
                line_dash="dash",
                line_color=THEME["accent_amber"],
                line_width=2,
                annotation_text=f"Mean: ${stats['mean']:,.0f}",
                annotation_position="top right",
                annotation_font_color=THEME["accent_amber"],
            )
        if stats["approx_median"]:
            fig.add_vline(
                x=stats["approx_median"],
                line_dash="dot",
                line_color=THEME["accent_emerald"],
                line_width=2,
                annotation_text=f"Median: ${stats['approx_median']:,.0f}",
                annotation_position="top left",
                annotation_font_color=THEME["accent_emerald"],
            )

        threshold_label = ""
        if hist_data.get("outlier_threshold") and source_key == "linkedin":
            threshold_label = f" (Threshold-Adjusted ≤ ${hist_data['outlier_threshold']:,.0f})"
        fig = apply_theme(fig, title=f"{hist_data['value_label']}{threshold_label} (n = {n:,})", height=440)
        fig.update_xaxes(title_text="Annual Salary / Derived Midpoint (USD)", tickformat="$,.0f")
        fig.update_yaxes(title_text="Posting Density Count")
        st.plotly_chart(fig, use_container_width=True)

        h_c1, h_c2, h_c3 = st.columns(3)
        with h_c1:
            render_editorial_stat_card("Records Evaluated", f"{n:,}", "Non-null compensation sample", delta_type="neutral")
        with h_c2:
            render_editorial_stat_card("Distribution Mean", f"${stats['mean']:,.0f}" if stats['mean'] else "N/A", "Arithmetic average", delta_type="positive")
        with h_c3:
            render_editorial_stat_card("Distribution Median", f"${stats['approx_median']:,.0f}" if stats['approx_median'] else "N/A", "Approximate midpoint", delta_type="positive")

        st.caption(f"⚠️ {hist_data['currency_note']}")
    else:
        render_empty_state("No Histogram Data Available", "No valid compensation values found for selected platform.")


# ── Tab 2: Salary Buckets ─────────────────────────────────────────────────────
with tab2:
    st.markdown("### Standardized Salary Buckets (6 Canonical Tiers)")
    render_editorial_callout(
        title="Bucket Alignment Disclosure",
        text=(
            "Both LinkedIn and Indeed records map into the same 6 canonical salary tiers (<$80k, $80k–$100k, etc.). "
            "However, LinkedIn tiers are derived from <code>salary.normalized_annual</code> (observed continuous), "
            "whereas Indeed tiers originate from <code>QUERY_BUCKET</code> search queries. "
            "They are shown side-by-side for market orientation, but originate from distinct data collection mechanisms."
        ),
        callout_type="info",
        eyebrow="Taxonomy Alignment Note",
    )

    with st.spinner("Loading bucket statistics…"):
        try:
            buckets_raw = load_bucket_distribution_cached()
            buckets = buckets_raw.get("buckets", []) if buckets_raw else []
        except Exception as e:
            render_error_state("Failed to load bucket data", str(e))
            buckets = []

    if buckets:
        BUCKET_LABELS = {
            "<80000": "< $80k",
            "80000-99999": "$80k–$100k",
            "100000-119999": "$100k–$120k",
            "120000-139999": "$120k–$140k",
            "140000-159999": "$140k–$160k",
            ">160000": "> $160k",
        }
        labels = [BUCKET_LABELS.get(b.get("salary_bucket"), b.get("salary_bucket", "?")) for b in buckets]
        li_counts = [b.get("linkedin_count", 0) or 0 for b in buckets]
        ind_counts = [b.get("indeed_count", 0) or 0 for b in buckets]

        b_col_chart, b_col_table = st.columns([1.1, 0.9])

        with b_col_chart:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="LinkedIn (Observed)",
                x=labels, y=li_counts,
                marker=dict(color=THEME["linkedin_blue"], line=dict(color="rgba(46, 58, 45, 0.15)", width=1)),
                text=[f"{c:,}" for c in li_counts], textposition="auto",
                hovertemplate="<b>%{x}</b><br>LinkedIn: %{y:,}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                name="Indeed (Derived)",
                x=labels, y=ind_counts,
                marker=dict(color=THEME["indeed_blue"], line=dict(color="rgba(46, 58, 45, 0.15)", width=1)),
                text=[f"{c:,}" for c in ind_counts], textposition="auto",
                hovertemplate="<b>%{x}</b><br>Indeed: %{y:,}<extra></extra>",
            ))
            fig.update_layout(barmode="group")
            fig = apply_theme(fig, title="Salary Bucket Posting Counts by Platform", height=420)
            fig.update_xaxes(title_text="Annual Salary Tier (USD)")
            fig.update_yaxes(title_text="Total Postings")
            st.plotly_chart(fig, use_container_width=True)

        with b_col_table:
            st.markdown("#### Standardized Bucket Breakdown Table")
            bucket_df = pd.DataFrame([
                {
                    "Salary Tier": BUCKET_LABELS.get(b.get("salary_bucket"), b.get("salary_bucket", "?")),
                    "Total Postings": f"{b.get('total_count', 0):,}",
                    "LinkedIn Count": f"{b.get('linkedin_count', 0):,}",
                    "Indeed Count": f"{b.get('indeed_count', 0):,}",
                    "LinkedIn Avg ($)": f"${b['linkedin_avg_normalized_annual']:,.0f}" if b.get("linkedin_avg_normalized_annual") else "N/A",
                    "Indeed Midpoint ($)": f"${b['indeed_avg_estimated_midpoint']:,.0f}" if b.get("indeed_avg_estimated_midpoint") else "N/A",
                    "Outliers > $1M": b.get("outlier_count_gt_1m", 0),
                }
                for b in buckets
            ])
            st.dataframe(bucket_df, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No Bucket Data Available", "Unable to retrieve bucket distribution statistics.")


# ── Tab 3: Experience Level ──────────────────────────────────────────────────
with tab3:
    st.markdown("### LinkedIn Compensation by Experience Level")
    render_editorial_callout(
        title="Experience Level Annotation Scope",
        text=(
            "Indeed records contain no experience level annotations (100% NOT_AVAILABLE). "
            "This section utilizes <code>salary.normalized_annual</code> from LinkedIn exclusively. "
            "Both unadjusted means and threshold-adjusted means (≤ $1M) are displayed across all 6 experience tiers "
            "as well as the Unclassified cohort (29,396 postings lacking experience classification)."
        ),
        callout_type="info",
        eyebrow="Platform Scope Restriction",
    )

    with st.spinner("Loading experience-level compensation data…"):
        try:
            exp_data = load_experience_salary_cached()
            exp_rows = exp_data.get("experience_levels", []) if exp_data else []
        except Exception as e:
            render_error_state("Failed to load experience compensation", str(e))
            exp_rows = []

    if exp_rows:
        labels = [r["experience_level"] for r in exp_rows]
        adj_means = [r["adjusted_mean"] or 0 for r in exp_rows]
        unadj_means = [r["unadjusted_mean"] or 0 for r in exp_rows]

        labels_rev = list(reversed(labels))
        adj_rev = list(reversed(adj_means))
        unadj_rev = list(reversed(unadj_means))

        exp_col_chart, exp_col_table = st.columns([1.1, 0.9])

        with exp_col_chart:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Adjusted Mean (≤ $1M)",
                y=labels_rev, x=adj_rev, orientation="h",
                marker=dict(color=THEME["accent_emerald"], line=dict(color="rgba(46, 58, 45, 0.15)", width=1)),
                text=[f"${v:,.0f}" for v in adj_rev], textposition="auto",
                hovertemplate="<b>%{y}</b><br>Adj. Mean: %{x:$,.0f}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                name="Unadjusted Mean (All Records)",
                y=labels_rev, x=unadj_rev, orientation="h",
                marker=dict(color=THEME["accent_amber"], opacity=0.55, line=dict(color="rgba(46, 58, 45, 0.15)", width=1)),
                text=[f"${v:,.0f}" for v in unadj_rev], textposition="auto",
                hovertemplate="<b>%{y}</b><br>Unadj. Mean: %{x:$,.0f}<extra></extra>",
            ))
            fig.update_layout(barmode="group")
            fig = apply_theme(fig, title="Mean Annual Salary by Experience Level (LinkedIn Only)", height=450)
            fig.update_xaxes(title_text="Mean Annual Salary (USD)", tickformat="$,.0f")
            st.plotly_chart(fig, use_container_width=True)

        with exp_col_table:
            st.markdown("#### Experience Level Summary Table")
            exp_df = pd.DataFrame([
                {
                    "Experience Tier": r["experience_level"],
                    "Total Jobs": f"{r.get('total_postings', 0):,}",
                    "Salary Postings": f"{r['unadjusted_count']:,}",
                    "Adjusted Mean ($)": f"${r['adjusted_mean']:,.0f}" if r['adjusted_mean'] else "N/A",
                    "Unadjusted Mean ($)": f"${r['unadjusted_mean']:,.0f}" if r['unadjusted_mean'] else "N/A",
                    "Outliers > $1M": f"{r['outlier_count']:,}",
                }
                for r in exp_rows
            ])
            st.dataframe(exp_df, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No Experience Level Data", "Unable to retrieve experience level salary statistics.")


# ── Tab 4: Job Title ──────────────────────────────────────────────────────────
with tab4:
    st.markdown("### LinkedIn Compensation by Job Title")
    render_editorial_callout(
        title="Title Inclusion Threshold",
        text=(
            "Only job titles with <b>≥ 20 LinkedIn salary-annotated postings</b> are included to preserve statistical validity. "
            "Means are threshold-adjusted (≤ $1M) to eliminate distortion from extreme outliers. "
            "Note that titles common in contract staffing (e.g., hourly travel nursing) reflect lower annualized equivalents."
        ),
        callout_type="info",
        eyebrow="Sample Size Filter (≥ 20 Postings)",
    )

    title_ctrl1, title_ctrl2 = st.columns([1, 2])
    with title_ctrl1:
        top_n_titles = st.slider("Number of Top Titles", 10, 30, 15, key="title_slider")

    with st.spinner("Loading title compensation data…"):
        try:
            title_data = load_title_salary_cached(limit=top_n_titles)
            title_rows = title_data.get("titles", []) if title_data else []
        except Exception as e:
            render_error_state("Failed to load title compensation", str(e))
            title_rows = []

    if title_rows:
        sorted_by_salary = sorted(title_rows, key=lambda x: x["adj_mean"], reverse=True)
        labels_t = [r["title"] for r in sorted_by_salary]
        means_t = [r["adj_mean"] for r in sorted_by_salary]
        labels_t_rev = list(reversed(labels_t))
        means_t_rev = list(reversed(means_t))

        t_col_chart, t_col_table = st.columns([1.1, 0.9])

        with t_col_chart:
            fig = go.Figure(go.Bar(
                y=labels_t_rev, x=means_t_rev, orientation="h",
                marker=dict(color=THEME["accent_purple"], line=dict(color="rgba(46, 58, 45, 0.15)", width=1)),
                text=[f"${v:,.0f}" for v in means_t_rev], textposition="auto",
                hovertemplate="<b>%{y}</b><br>Adj. Mean: %{x:$,.0f}<extra></extra>",
            ))
            fig = apply_theme(fig, title=f"Top {len(title_rows)} Job Titles by Adjusted Mean Salary (LinkedIn ≤ $1M)", height=max(420, len(title_rows) * 26 + 80))
            fig.update_xaxes(title_text="Adjusted Mean Annual Salary (USD)", tickformat="$,.0f")
            st.plotly_chart(fig, use_container_width=True)

        with t_col_table:
            st.markdown("#### Ranked Titles Table")
            title_df = pd.DataFrame([
                {
                    "Job Title": r["title"],
                    "Records (≤ $1M)": r["count"],
                    "Adjusted Mean ($)": f"${r['adj_mean']:,.0f}",
                    "Min Observed ($)": f"${r['min_val']:,.0f}",
                    "Max Observed ($)": f"${r['max_val']:,.0f}",
                }
                for r in sorted_by_salary
            ])
            st.dataframe(title_df, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No Title Compensation Data", "No titles met the ≥ 20 salary postings threshold.")


# ── Tab 5: State Geography ────────────────────────────────────────────────────
with tab5:
    st.markdown("### LinkedIn Compensation by US State")
    render_editorial_callout(
        title="State Geography Statistical Threshold",
        text=(
            "Only US jurisdictions with <b>≥ 50 LinkedIn salary-annotated postings</b> are evaluated to ensure representativeness. "
            "Both unadjusted and threshold-adjusted (≤ $1M) means are presented. "
            "State figures reflect regional industry concentrations (e.g., tech headquarters vs healthcare/staffing hubs)."
        ),
        callout_type="info",
        eyebrow="Sample Size Filter (≥ 50 Postings)",
    )

    state_ctrl1, state_ctrl2 = st.columns([1, 2])
    with state_ctrl1:
        top_n_states = st.slider("Number of States", 10, 25, 15, key="state_slider")

    with st.spinner("Loading state compensation data…"):
        try:
            state_data = load_state_salary_cached(limit=top_n_states)
            state_rows = state_data.get("states", []) if state_data else []
        except Exception as e:
            render_error_state("Failed to load state compensation", str(e))
            state_rows = []

    if state_rows:
        sorted_states = sorted(state_rows, key=lambda x: (x["adjusted_mean"] or 0), reverse=True)
        labels_s = [r["state"] for r in sorted_states]
        adj_s = [r["adjusted_mean"] or 0 for r in sorted_states]
        unadj_s = [r["unadjusted_mean"] or 0 for r in sorted_states]
        labels_s_rev = list(reversed(labels_s))
        adj_s_rev = list(reversed(adj_s))
        unadj_s_rev = list(reversed(unadj_s))

        s_col_chart, s_col_table = st.columns([1.1, 0.9])

        with s_col_chart:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Adjusted Mean (≤ $1M)",
                y=labels_s_rev, x=adj_s_rev, orientation="h",
                marker=dict(color=THEME["accent_blue"], line=dict(color="rgba(46, 58, 45, 0.15)", width=1)),
                text=[f"${v:,.0f}" for v in adj_s_rev], textposition="auto",
                hovertemplate="<b>State: %{y}</b><br>Adj. Mean: %{x:$,.0f}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                name="Unadjusted Mean (All)",
                y=labels_s_rev, x=unadj_s_rev, orientation="h",
                marker=dict(color=THEME["accent_amber"], opacity=0.55, line=dict(color="rgba(46, 58, 45, 0.15)", width=1)),
                text=[f"${v:,.0f}" for v in unadj_s_rev], textposition="auto",
                hovertemplate="<b>State: %{y}</b><br>Unadj. Mean: %{x:$,.0f}<extra></extra>",
            ))
            fig.update_layout(barmode="group")
            fig = apply_theme(fig, title=f"LinkedIn Mean Annual Salary by State (Top {len(state_rows)})", height=max(420, len(state_rows) * 26 + 80))
            fig.update_xaxes(title_text="Mean Annual Salary (USD, LinkedIn Only)", tickformat="$,.0f")
            st.plotly_chart(fig, use_container_width=True)

        with s_col_table:
            st.markdown("#### Ranked State Compensation Table")
            state_df = pd.DataFrame([
                {
                    "State": r["state"],
                    "Records (≤ $1M)": r["adjusted_count"],
                    "Adjusted Mean ($)": f"${r['adjusted_mean']:,.0f}" if r['adjusted_mean'] else "N/A",
                    "Unadjusted Mean ($)": f"${r['unadjusted_mean']:,.0f}" if r['unadjusted_mean'] else "N/A",
                    "Min ($)": f"${r['min_observed']:,.0f}" if r['min_observed'] else "N/A",
                    "Max ($)": f"${r['max_observed']:,.0f}" if r['max_observed'] else "N/A",
                }
                for r in sorted_states
            ])
            st.dataframe(state_df, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No State Data Available", "No states met the ≥ 50 salary postings threshold.")

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 8. Dual Analytical Panels: Pay Periods & Outlier Audit
# -----------------------------------------------------------------------------
st.markdown("## 🔍 Provenance & Outlier Audit Analysis")
st.markdown(
    "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.4rem; margin-bottom: 1.25rem;'>"
    "Detailed inspection of ingestion annualization multipliers and empirical audit classifications for 38 records exceeding $1M."
    "</p>",
    unsafe_allow_html=True,
)

panel_col1, panel_col2 = st.columns(2)

with panel_col1:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; height: 100%;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C; margin-bottom: 0.35rem;">
                ETL INGESTION ANNUALISATION MULTIPLIERS
            </div>
            <h4 style="margin: 0 0 0.5rem 0; font-family: 'Newsreader', serif; font-size: 1.15rem; color: #1C1F1D;">
                LinkedIn Pay Period Breakdown
            </h4>
            <p style="font-size: 0.86rem; color: #4A524D; line-height: 1.45; margin-bottom: 0.75rem;">
                Raw postings report compensation in diverse intervals. Multipliers below were applied at ingest time. 
                HOURLY roles (14,741 records) represent the majority of lower annualized wages.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pp_data = li.get("pay_period_breakdown", [])
    if pp_data:
        MULTIPLIERS = {"YEARLY": "×1 (Direct Annual)", "HOURLY": "×2,080 (40h/wk × 52wk)", "MONTHLY": "×12 (Calendar Months)", "WEEKLY": "×52 (Weeks)", "BIWEEKLY": "×26 (Bi-Weekly)"}
        pp_df = pd.DataFrame([
            {
                "Pay Interval": r["pay_period"],
                "Posting Count": f"{r['count']:,}",
                "ETL Formula": MULTIPLIERS.get(r["pay_period"], "?"),
                "% of Salary Postings": f"{r['count'] / li['postings_with_normalized_annual'] * 100:.1f}%",
            }
            for r in pp_data
        ])
        st.dataframe(pp_df, use_container_width=True, hide_index=True)

with panel_col2:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; height: 100%;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C; margin-bottom: 0.35rem;">
                READ-ONLY INTEGRITY // SOURCE PRESERVED
            </div>
            <h4 style="margin: 0 0 0.5rem 0; font-family: 'Newsreader', serif; font-size: 1.15rem; color: #1C1F1D;">
                Outlier Audit Classification (38 Records > $1,000,000)
            </h4>
            <p style="font-size: 0.86rem; color: #4A524D; line-height: 1.45; margin-bottom: 0.75rem;">
                All 38 records exceeding $1M originate from LinkedIn. Canonical records are strictly retained in MongoDB. 
                Prior audit classified 30 records into error categories; 8 remain unresolved intern stipend candidates.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    classification = outlier_audit.get("classification", {})
    audit_df = pd.DataFrame([
        {"Audit Category": "Hourly-conversion artifacts", "Records": classification.get("hourly_conversion_artifacts", 0), "Description": "HOURLY pay_period × 2,080 produced implausibly high annualized values"},
        {"Audit Category": "Recruiter/source entry errors", "Records": classification.get("recruiter_entry_errors", 0), "Description": "Salary values appear to be data-entry or source pipeline errors"},
        {"Audit Category": "Task fee / non-standard compensation", "Records": classification.get("task_fee_or_other", 0), "Description": "Value does not represent regular annual salary (e.g. one-time fee)"},
        {"Audit Category": "Unresolved (intern stipend candidates)", "Records": classification.get("unresolved_internship_stipends", 0), "Description": "Possible summer intern stipend totals; classification pending review"},
        {"Audit Category": "TOTAL EXTREME OUTLIERS", "Records": outlier_audit.get("total_outliers", 0), "Description": "All normalized_annual > $1,000,000 retained in source database"},
    ])
    st.dataframe(audit_df, use_container_width=True, hide_index=True)

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 9. Technical Provenance & Field Reference Expander
# -----------------------------------------------------------------------------
with st.expander("🔬 Full Salary Methodology & BSON Field Reference", expanded=False):
    st.markdown("""
### LinkedIn Salary Schema Specifications
| Field | Population Coverage | Ingestion & Analytical Semantics |
| :--- | :--- | :--- |
| `salary.normalized_annual` | 36,059 / 123,835 (29.12%) | Observed continuous salary, annualized from raw `pay_period` at ETL time |
| `salary.salary_bucket` | 36,059 / 123,835 (29.12%) | 6-tier categorical bin derived from `normalized_annual` |
| `salary.pay_period` | 36,059 / 123,835 (29.12%) | Raw pay interval: YEARLY, HOURLY, MONTHLY, WEEKLY, BIWEEKLY |
| `salary.min_salary` | 29,793 (24.06%) | Raw lower bound of pay range |
| `salary.max_salary` | 29,793 (24.06%) | Raw upper bound of pay range |
| `salary.currency` | 123,835 (100%) | Always USD in this dataset |
| `salary.estimated_midpoint` | 0 (0%) | Not populated for LinkedIn records |

### Indeed Salary Schema Specifications
| Field | Population Coverage | Ingestion & Analytical Semantics |
| :--- | :--- | :--- |
| `salary.normalized_annual` | 0 / 5,715 (0%) | Always null — Indeed does not provide continuous salary |
| `salary.estimated_midpoint` | 5,715 / 5,715 (100%) | DERIVED analytical midpoint from QUERY_BUCKET discrete search bands |
| `salary.salary_bucket` | 5,715 / 5,715 (100%) | 6-tier categorical bin derived from the QUERY_BUCKET band |
| `salary.compensation_type` | 5,715 (100%) | Always `QUERY_BUCKET` for Indeed records |

### Missing Salary & Outlier Policies
- **Missing Salary Policy:** Postings without salary annotations are **never treated as zero-pay**. They are excluded from all count denominators, means, medians, and distributions. 87,776 LinkedIn postings (70.88%) have no observable salary annotation.
- **Outlier Treatment Policy:** 38 LinkedIn records with `normalized_annual > $1,000,000` are **retained in source data unchanged**. A threshold-adjusted statistic (≤ $1,000,000) is computed separately and displayed alongside the unadjusted figure with the threshold explicitly labelled. No implicit removal or synthetic imputation occurs.
    """)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
st.markdown("---")
st.caption(
    "JobMarketDB · Advanced Database Management Systems Project · "
    "Module 3: Salary Analytics & Outlier Audit · Local MongoDB Community Server @ localhost:27017"
)
