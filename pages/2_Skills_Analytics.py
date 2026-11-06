"""
JobMarketDB — Module 2: Skills Intelligence & Taxonomy Separation (Phase 7 Stage 4)
Page: pages/2_Skills_Analytics.py

A publication-grade skills intelligence dashboard providing empirical demand analytics
while strictly enforcing Priority 2 taxonomy isolation boundaries:
- Indeed: 464 granular technical tools, libraries, and languages (N = 5,715)
- LinkedIn: 35 broad functional domains and business disciplines (N = 123,835)
- Distinct posting count semantics with MongoDB $setUnion deduplication
- Explicit market share percentages with platform-specific denominators
- Interactive top-N sliders, role category filters, and searchable rankings tables
- Methodological disclosure detailing why the two source taxonomies must never be merged
"""

import html
import os
import sys
from typing import Any, Dict, List, Optional
import pandas as pd
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
    create_skills_demand_chart,
    create_empty_chart,
)

# -----------------------------------------------------------------------------
# 1. Page Configuration & Editorial CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Skills Intelligence — JobMarketDB",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_custom_css()

# -----------------------------------------------------------------------------
# 2. Service Client & Cached Data Helpers
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


@st.cache_data(ttl=600)
def load_top_skills_cached(
    source: str,
    limit: int,
    role_category: Optional[str] = None,
) -> Dict[str, Any]:
    """Caches top skills aggregation results for fast responsive UI interaction."""
    service = get_analytics_service()
    if not service:
        return {"skills": [], "total_postings_evaluated": 0}
    return service.get_top_skills(limit=limit, source=source, role_category=role_category)


@st.cache_data(ttl=600)
def load_platform_overview_cached() -> Optional[Dict[str, Any]]:
    """Caches platform overview skill metadata."""
    service = get_analytics_service()
    if not service:
        return None
    try:
        return service.get_skills_by_platform(limit=1)
    except Exception:
        return None


service = get_analytics_service()

# -----------------------------------------------------------------------------
# 3. Editorial Page Header
# -----------------------------------------------------------------------------
render_editorial_header(
    title="Skills in Demand",
    subtitle=(
        "Platform-separated skill intelligence honoring data provenance boundaries "
        "across LinkedIn functional domains and Indeed technical tools."
    ),
    eyebrow="SKILLS INTELLIGENCE",
    badge_text="Module 2",
    status_text="Strict Taxonomy Isolation",
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
    title="Methodology Note: LinkedIn and Indeed Use Different Skill Classifications",
    text=(
        "<b>LinkedIn</b> utilizes <b>35 broad functional domains</b> (e.g., Information Technology, "
        "Sales, Management, Engineering) sourced from the canonical <code>job_skills</code> industry mapping.<br>"
        "<b>Indeed</b> captures <b>464 granular technical tools and languages</b> (e.g., Python, "
        "SQL, Machine Learning, R, Hadoop, Spark, AWS) extracted from job description tokens.<br>"
        "Because these two taxonomies occupy fundamentally disparate levels of abstraction, <b>they cannot and must "
        "not be combined into a single shared ranking</b>. A merged ranking would introduce severe false equivalence "
        "and allow LinkedIn's 95.6% volume share to completely obscure granular technical tool demand. "
        "All metrics below are strictly segmented by platform with explicit denominators."
    ),
    callout_type="warning",
    eyebrow="Taxonomy Separation Safeguard",
)

st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 5. High-Level Taxonomy KPI Cards (Editorial Stat Cards)
# -----------------------------------------------------------------------------
overview_data = load_platform_overview_cached()

if overview_data and "linkedin" in overview_data and "indeed" in overview_data:
    li_meta = overview_data["linkedin"]
    ind_meta = overview_data["indeed"]

    li_skills = li_meta.get("skills", [])
    ind_skills = ind_meta.get("skills", [])

    li_top_skill = li_skills[0].get("skill", "N/A") if li_skills else "N/A"
    li_top_count = li_skills[0].get("count", 0) if li_skills else 0
    li_top_pct = li_skills[0].get("percentage_of_postings", 0.0) if li_skills else 0.0

    ind_top_skill = ind_skills[0].get("skill", "N/A") if ind_skills else "N/A"
    ind_top_count = ind_skills[0].get("count", 0) if ind_skills else 0
    ind_top_pct = ind_skills[0].get("percentage_of_postings", 0.0) if ind_skills else 0.0

    total_li_postings = li_meta.get("total_postings", 0)
    total_ind_postings = ind_meta.get("total_postings", 0)
else:
    total_li_postings = 123835
    total_ind_postings = 5715
    li_top_skill = "N/A"
    li_top_count = 0
    li_top_pct = 0.0
    ind_top_skill = "N/A"
    ind_top_count = 0
    ind_top_pct = 0.0

kpi_cols = st.columns(4)

with kpi_cols[0]:
    render_editorial_stat_card(
        title="Indeed Skill Taxonomy",
        value="464 Technical Tools",
        subtitle=f"Granular tool tokens · N = {total_ind_postings:,}",
        delta="8.13 tools/posting avg",
        delta_type="positive",
    )

with kpi_cols[1]:
    render_editorial_stat_card(
        title="Top Indeed Tool",
        value=ind_top_skill,
        subtitle=f"{ind_top_count:,} postings on Indeed",
        delta=f"{ind_top_pct:.1f}% of Indeed",
        delta_type="positive",
    )

with kpi_cols[2]:
    render_editorial_stat_card(
        title="LinkedIn Skill Taxonomy",
        value="35 Functional Domains",
        subtitle=f"Organizational codes · N = {total_li_postings:,}",
        delta="1.69 domains/posting avg",
        delta_type="positive",
    )

with kpi_cols[3]:
    render_editorial_stat_card(
        title="Top LinkedIn Domain",
        value=li_top_skill,
        subtitle=f"{li_top_count:,} postings on LinkedIn",
        delta=f"{li_top_pct:.1f}% of LinkedIn",
        delta_type="positive",
    )

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 6. Interactive Platform Tabs
# -----------------------------------------------------------------------------
tab_indeed, tab_linkedin, tab_contrast = st.tabs([
    "🛠️ Indeed Technical Tools (464 Granular Tools)",
    "🏢 LinkedIn Functional Domains (35 Broad Disciplines)",
    "⚖️ Taxonomy Contrast & Deduplication Methodology",
])

# Available Role Categories for filtering
ROLE_CATEGORIES = [
    "All Categories",
    "Data Analyst",
    "Data Engineer",
    "Data Scientist",
    "Healthcare",
    "Machine Learning Engineer",
    "Management",
    "Other",
    "Sales",
    "Software Engineer",
]


# =============================================================================
# TAB 1: INDEED TECHNICAL TOOLS
# =============================================================================
with tab_indeed:
    st.markdown("### Indeed Technical Tools & Libraries")
    st.markdown(
        "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.4rem; margin-bottom: 1.25rem;'>"
        "Analysis of <b>464 granular technical tools, programming languages, and frameworks</b> "
        "extracted from Indeed postings. Market share is calculated against total Indeed postings in scope."
        "</p>",
        unsafe_allow_html=True,
    )

    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 2])
    with ctrl_col1:
        ind_limit = st.slider(
            "Top N Tools to Display",
            min_value=5,
            max_value=30,
            value=15,
            step=5,
            key="ind_limit_slider",
        )
    with ctrl_col2:
        ind_category = st.selectbox(
            "Filter by Role Category (Optional)",
            options=ROLE_CATEGORIES,
            index=0,
            key="ind_role_filter",
        )
    with ctrl_col3:
        ind_search_filter = st.text_input(
            "Filter Table by Tool Name",
            value="",
            placeholder="e.g. Python, SQL, Spark...",
            key="ind_search_box",
        )

    ind_cat_param = None if ind_category == "All Categories" else ind_category

    with st.spinner("Calculating Indeed skill demand via MongoDB aggregation..."):
        try:
            ind_data = load_top_skills_cached(
                source="indeed",
                limit=ind_limit,
                role_category=ind_cat_param,
            )
            ind_skills_list = ind_data.get("skills", [])
            ind_postings_evaluated = ind_data.get("total_postings_evaluated", 0)
        except Exception as exc:
            render_error_state("Failed to retrieve Indeed skills", str(exc))
            ind_skills_list = []
            ind_postings_evaluated = 0

    if ind_postings_evaluated == 0 or not ind_skills_list:
        render_empty_state(
            title="No Skills Found for Selection",
            message=f"No Indeed job postings matched role category '{ind_category}'.",
        )
    else:
        st.markdown(
            f"""
            <div style="font-size: 0.88rem; color: #4A524D; font-family: 'Plus Jakarta Sans', sans-serif; margin-bottom: 0.75rem;">
                Evaluated <span style="font-weight: 700; color: #1C1F1D;">{ind_postings_evaluated:,}</span> Indeed postings. 
                Denominator for share calculation: <span style="font-weight: 700; color: #2E3A2D;">{ind_postings_evaluated:,}</span>.
            </div>
            """,
            unsafe_allow_html=True,
        )

        chart_col, table_col = st.columns([7, 5])

        with chart_col:
            ind_fig = create_skills_demand_chart(
                skills_data=ind_skills_list,
                title=f"Top {len(ind_skills_list)} Technical Tools on Indeed ({ind_category})",
                platform="indeed",
                max_skills=ind_limit,
                height=480,
            )
            st.plotly_chart(ind_fig, use_container_width=True)

        with table_col:
            st.markdown(f"#### Ranked Tools Table ({len(ind_skills_list)} items)")

            table_rows = []
            for rank, item in enumerate(ind_skills_list, start=1):
                name = item.get("skill", "Unknown")
                count = item.get("count", 0)
                pct = item.get("percentage_of_postings", 0.0)
                table_rows.append({
                    "Rank": rank,
                    "Tool / Skill": name,
                    "Postings": count,
                    "Indeed Share": f"{pct:.2f}%",
                })

            df_ind = pd.DataFrame(table_rows)

            if ind_search_filter.strip():
                query = ind_search_filter.strip().lower()
                df_ind = df_ind[df_ind["Tool / Skill"].str.lower().str.contains(query)]

            if df_ind.empty:
                st.info(f"No tools match filter '{ind_search_filter}'.")
            else:
                st.dataframe(
                    df_ind,
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                )

        # Editorial Insights Card
        st.markdown(
            """
            <div class="jmdb-card" style="margin-top: 1.25rem; padding: 1.25rem;">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C; margin-bottom: 0.35rem;">
                    ANALYTICAL SYNTHESIS // INDEED TECHNICAL LANDSCAPE
                </div>
                <h4 style="margin: 0 0 0.5rem 0; font-family: 'Newsreader', serif; font-size: 1.15rem; color: #1C1F1D;">
                    Key Empirical Tool Patterns
                </h4>
                <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.5; margin: 0 0 0.5rem 0;">
                    • <b>Python (58.18%) and SQL (54.31%)</b> dominate Indeed tech postings, appearing in over half of all job descriptions.<br>
                    • <b>Big Data & Distributed Computing</b> tools (Hadoop at 30.0%, Spark at 26.8%, Hive at 16.9%) reflect intense demand for scalable data infrastructure.<br>
                    • <b>Postings list an average of 8.13 tools</b> per posting, demonstrating heavy reliance on multi-tool software stacks rather than single-skill profiles.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =============================================================================
# TAB 2: LINKEDIN FUNCTIONAL DOMAINS
# =============================================================================
with tab_linkedin:
    st.markdown("### LinkedIn Broad Functional Disciplines")
    st.markdown(
        "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.4rem; margin-bottom: 1.25rem;'>"
        "Analysis of <b>35 broad functional skill domains and business disciplines</b> "
        "derived from LinkedIn's standardized taxonomy. Market share is calculated against total LinkedIn postings in scope."
        "</p>",
        unsafe_allow_html=True,
    )

    li_ctrl1, li_ctrl2, li_ctrl3 = st.columns([2, 2, 2])
    with li_ctrl1:
        li_limit = st.slider(
            "Top N Domains to Display",
            min_value=5,
            max_value=35,
            value=15,
            step=5,
            key="li_limit_slider",
        )
    with li_ctrl2:
        li_category = st.selectbox(
            "Filter by Role Category (Optional)",
            options=ROLE_CATEGORIES,
            index=0,
            key="li_role_filter",
        )
    with li_ctrl3:
        li_search_filter = st.text_input(
            "Filter Table by Domain Name",
            value="",
            placeholder="e.g. Information Technology, Sales...",
            key="li_search_box",
        )

    li_cat_param = None if li_category == "All Categories" else li_category

    with st.spinner("Calculating LinkedIn domain demand via MongoDB aggregation..."):
        try:
            li_data = load_top_skills_cached(
                source="linkedin",
                limit=li_limit,
                role_category=li_cat_param,
            )
            li_skills_list = li_data.get("skills", [])
            li_postings_evaluated = li_data.get("total_postings_evaluated", 0)
        except Exception as exc:
            render_error_state("Failed to retrieve LinkedIn skills", str(exc))
            li_skills_list = []
            li_postings_evaluated = 0

    if li_postings_evaluated == 0 or not li_skills_list:
        render_empty_state(
            title="No Domains Found for Selection",
            message=f"No LinkedIn job postings matched role category '{li_category}'.",
        )
    else:
        st.markdown(
            f"""
            <div style="font-size: 0.88rem; color: #4A524D; font-family: 'Plus Jakarta Sans', sans-serif; margin-bottom: 0.75rem;">
                Evaluated <span style="font-weight: 700; color: #1C1F1D;">{li_postings_evaluated:,}</span> LinkedIn postings. 
                Denominator for share calculation: <span style="font-weight: 700; color: #2E3A2D;">{li_postings_evaluated:,}</span>.
            </div>
            """,
            unsafe_allow_html=True,
        )

        li_chart_col, li_table_col = st.columns([7, 5])

        with li_chart_col:
            li_fig = create_skills_demand_chart(
                skills_data=li_skills_list,
                title=f"Top {len(li_skills_list)} Functional Domains on LinkedIn ({li_category})",
                platform="linkedin",
                max_skills=li_limit,
                height=480,
            )
            st.plotly_chart(li_fig, use_container_width=True)

        with li_table_col:
            st.markdown(f"#### Ranked Domains Table ({len(li_skills_list)} items)")

            li_table_rows = []
            for rank, item in enumerate(li_skills_list, start=1):
                name = item.get("skill", "Unknown")
                count = item.get("count", 0)
                pct = item.get("percentage_of_postings", 0.0)
                li_table_rows.append({
                    "Rank": rank,
                    "Functional Domain": name,
                    "Postings": count,
                    "LinkedIn Share": f"{pct:.2f}%",
                })

            df_li = pd.DataFrame(li_table_rows)

            if li_search_filter.strip():
                query = li_search_filter.strip().lower()
                df_li = df_li[df_li["Functional Domain"].str.lower().str.contains(query)]

            if df_li.empty:
                st.info(f"No domains match filter '{li_search_filter}'.")
            else:
                st.dataframe(
                    df_li,
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                )

        # Editorial Insights Card
        st.markdown(
            """
            <div class="jmdb-card" style="margin-top: 1.25rem; padding: 1.25rem;">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C; margin-bottom: 0.35rem;">
                    ANALYTICAL SYNTHESIS // LINKEDIN FUNCTIONAL LANDSCAPE
                </div>
                <h4 style="margin: 0 0 0.5rem 0; font-family: 'Newsreader', serif; font-size: 1.15rem; color: #1C1F1D;">
                    Key Organizational Domain Patterns
                </h4>
                <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.5; margin: 0 0 0.5rem 0;">
                    • <b>Information Technology (20.39%)</b>, <b>Sales (17.06%)</b>, and <b>Management (16.51%)</b> form the top functional disciplines across LinkedIn's 123k+ postings.<br>
                    • Unlike Indeed's granular programming languages, LinkedIn's taxonomy reflects broad <b>organizational business departments</b> and industry sectors.<br>
                    • Postings map to an average of <b>1.69 functional domains per posting</b>, indicating high-level sector categorization rather than tool-level specificity.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =============================================================================
# TAB 3: TAXONOMY CONTRAST & METHODOLOGY BREAKDOWN
# =============================================================================
with tab_contrast:
    st.markdown("### Cross-Platform Taxonomy Incompatibility & Counting Methodology")
    st.markdown(
        "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.4rem; margin-bottom: 1.25rem;'>"
        "A rigorous empirical comparison demonstrates why LinkedIn's 35 functional domains and Indeed's "
        "464 technical tools cannot and must not be aggregated into a single unified ranking."
        "</p>",
        unsafe_allow_html=True,
    )

    contrast_df = pd.DataFrame({
        "Analytical Dimension": [
            "Taxonomy Concept",
            "Entity Granularity",
            "Total Vocabulary Size",
            "Evaluated Postings Population",
            "Postings with Skills Coverage",
            "Total Skill Occurrences",
            "Avg Skills per Covered Posting",
            "Top Ranked Skill / Domain",
            "Top Entity Posting Count & Share",
            "Vocabulary Name Overlap",
            "Overlapping Skill Names",
        ],
        "LinkedIn (Functional Taxonomy)": [
            "Broad Functional / Business Disciplines",
            "Department & Industry Sector (High-level)",
            "35 distinct domains",
            "123,835 postings (95.59% of dataset)",
            "122,083 postings (98.59% coverage)",
            "205,755 domain tokens",
            "1.69 domains / job",
            "Information Technology",
            "25,252 postings (20.39% of LinkedIn)",
            "4 shared names (0.81% of combined)",
            "Customer Service, Public Relations, Project Management, Marketing",
        ],
        "Indeed (Technical Taxonomy)": [
            "Specific Technical Tools & Languages",
            "Software, Framework & Library (Granular)",
            "464 distinct technical tools",
            "5,715 postings (4.41% of dataset)",
            "5,483 postings (95.94% coverage)",
            "44,598 tool tokens",
            "8.13 tools / job",
            "Python",
            "3,325 postings (58.18% of Indeed)",
            "4 shared names (0.81% of combined)",
            "Customer Service, Public Relations, Project Management, Marketing",
        ],
    })

    st.dataframe(
        contrast_df,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    # Distinct Counting Methodology & $setUnion Deduplication Explanation
    st.markdown("### Distinct Postings Counting & MongoDB `$setUnion` Deduplication")

    method_col1, method_col2 = st.columns([1, 1])

    with method_col1:
        render_editorial_callout(
            title="Distinct Postings Semantic Formula",
            text=(
                "To prevent multi-occurrence skill tokens within a single job description from inflating "
                "demand statistics, our backend calculates <b>distinct postings containing the skill</b> "
                "rather than raw keyword frequency:<br><br>"
                "<div style='font-family: \"JetBrains Mono\", monospace; font-size: 0.88rem; background: #FAF8F5; padding: 10px 14px; border-radius: 6px; border: 1px solid #E2DDD5; color: #1C1F1D; margin-bottom: 8px;'>"
                "<b>Market Share (%)</b> = [Distinct Postings with Skill S / Total Scope Postings N] × 100%"
                "</div>"
                "• <b>Denominator Integrity:</b> The denominator is strictly constrained to the corresponding "
                "platform's postings (123,835 for LinkedIn, 5,715 for Indeed), avoiding cross-contamination.<br>"
                "• <b>Zero-Skill Handling:</b> Postings lacking skill annotations (1,752 on LinkedIn, 232 on Indeed) "
                "remain in the denominator to preserve true market prevalence."
            ),
            callout_type="info",
            eyebrow="Mathematical Formula",
        )

    with method_col2:
        render_editorial_callout(
            title="MongoDB Aggregation Pipeline Architecture",
            text=(
                "The <code>get_top_demanded_skills</code> pipeline enforces mathematical deduplication in MongoDB:<br><br>"
                "1. <b>$match:</b> Pre-filters by <code>source</code> and optional <code>role_category.value</code>.<br>"
                "2. <b>$project + $setUnion:</b> <code>{\"$setUnion\": [{\"$ifNull\": [\"$skills\", []]}, []]}</code> "
                "converts the skills array to a mathematical set, deduplicating identical tokens per document.<br>"
                "3. <b>$unwind:</b> Deconstructs the distinct array into individual document-skill pairs.<br>"
                "4. <b>$group + $sum:</b> Groups by skill string and counts unique documents ($sum: 1).<br>"
                "5. <b>$sort + $limit:</b> Orders descending by frequency and returns top N results."
            ),
            callout_type="info",
            eyebrow="Pipeline Architecture",
        )

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    render_editorial_callout(
        title="Why a Combined Ranking is Statistically Misleading",
        text=(
            "If LinkedIn and Indeed skills were naively combined into a single ranking:<br>"
            "1. <b>Volume Distortion:</b> LinkedIn's 123,835 postings outnumber Indeed's 5,715 postings by <b>21.7 to 1</b>. "
            "Even if 100% of Indeed jobs required Python, its 5,715 postings would still rank <i>below</i> 10 of LinkedIn's broad domains "
            "(e.g., Information Technology at 25k, Sales at 21k, Management at 20k).<br>"
            "2. <b>Conceptual Confusion:</b> Comparing 'Information Technology' (an entire economic sector) to 'Python' (a programming language) "
            "creates category confusion that misguides job seekers and workforce planners."
        ),
        callout_type="warning",
        eyebrow="Statistical Fallacy Proof",
    )

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
st.markdown("---")
st.caption(
    "JobMarketDB · Advanced Database Management Systems Project · "
    "Module 2: Skills Intelligence · Local MongoDB Community Server @ localhost:27017"
)
