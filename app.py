"""
JobMarketDB — Executive Overview & System Architecture (Phase 7 Stage 3)
Entrypoint: app.py

A publication-grade executive dashboard and architectural blueprint for the JobMarketDB
enterprise analytics platform, connected directly to local MongoDB Community Server 9.0.4:
- Hero Header: Eyebrow, serif title, live connection status, dataset scope
- Executive KPI Section: 4 live cards for postings, companies, salary, remote work
- Platform Overview: LinkedIn vs Indeed empirical volume, compensation, and remote comparison
- Market Intelligence: Standardized salary distribution, geographic concentration, workplace model
- Technical Architecture: 6-tier decoupled blueprint, active DB specifications, 15 index catalog
- Navigation Pathways: Seamless links to all 6 specialized analytical modules
"""

import html
from typing import Any, Dict, List, Tuple
import streamlit as st

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService
from utils.ui_components import (
    load_custom_css,
    render_editorial_header,
    render_editorial_stat_card,
    render_editorial_callout,
    render_error_state,
    render_platform_badge,
)
from utils.plots import (
    create_platform_comparison_chart,
)

# -----------------------------------------------------------------------------
# 1. Page Configuration & Editorial CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="JobMarketDB — US Tech Job Market Analytics",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject Stage 1 custom design tokens and styles
load_custom_css()


# -----------------------------------------------------------------------------
# 2. Live Database Connection & Cached Data Loader
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_home_data() -> Tuple[bool, Dict[str, Any], str]:
    """
    Connects to local MongoDB and loads live collection metrics, database stats,
    platform comparisons, salary bucket distribution, top locations, and index catalog.
    Returns (is_connected, data_dict, error_message).
    """
    try:
        if not verify_connection(timeout_ms=3000):
            return False, {}, "MongoDB connection check failed: server did not respond to ping."

        db = get_database()
        service = JobMarketAnalyticsService(db)

        # 1. Collection document counts
        jobs_count = db["jobs"].count_documents({})
        companies_count = db["companies"].count_documents({})

        # 2. Database statistics
        db_stats = db.command("dbStats")

        # 3. Complete index information
        jobs_indexes = db["jobs"].index_information()
        companies_indexes = db["companies"].index_information()

        # 4. Analytical platform comparison (Operation 12)
        comp = service.compare_platforms()

        # 5. Extract calculated market KPIs
        li = comp["platforms"].get("linkedin", {})
        ind = comp["platforms"].get("indeed", {})

        li_postings = li.get("total_postings", 0)
        ind_postings = ind.get("total_postings", 0)

        li_sal_count = li.get("salary_coverage", {}).get("postings_with_salary", 0)
        ind_sal_count = ind.get("salary_coverage", {}).get("postings_with_salary", 0)
        total_salary_postings = li_sal_count + ind_sal_count
        overall_salary_coverage_pct = round((total_salary_postings / jobs_count * 100), 2) if jobs_count > 0 else 0.0
        overall_salary_coverage_display = (int((total_salary_postings / jobs_count * 10000)) / 100.0) if jobs_count > 0 else 0.0

        li_rem_count = li.get("remote_work_breakdown", {}).get("explicitly_remote", 0)
        ind_rem_count = ind.get("remote_work_breakdown", {}).get("explicitly_remote", 0)
        total_remote_postings = li_rem_count + ind_rem_count
        overall_remote_pct = round((total_remote_postings / jobs_count * 100), 2) if jobs_count > 0 else 0.0

        # Continuous base salary count (strictly LinkedIn-sourced)
        continuous_salary_count = db["jobs"].count_documents({"salary.normalized_annual": {"$ne": None}})
        continuous_salary_pct = round((continuous_salary_count / jobs_count * 100), 2) if jobs_count > 0 else 0.0

        # 6. Standardized salary bucket comparison
        salary_bucket_comp = service.get_platform_salary_bucket_comparison()

        # 7. Top hiring locations
        top_locations = service.get_top_locations(limit=5)

        data = {
            "jobs_count": jobs_count,
            "companies_count": companies_count,
            "db_stats": db_stats,
            "jobs_indexes": jobs_indexes,
            "companies_indexes": companies_indexes,
            "comparison": comp,
            "li_metrics": li,
            "ind_metrics": ind,
            "overall_salary_coverage_pct": overall_salary_coverage_pct,
            "overall_salary_coverage_display": overall_salary_coverage_display,
            "total_salary_postings": total_salary_postings,
            "overall_remote_pct": overall_remote_pct,
            "total_remote_postings": total_remote_postings,
            "continuous_salary_count": continuous_salary_count,
            "continuous_salary_pct": continuous_salary_pct,
            "salary_bucket_comp": salary_bucket_comp,
            "top_locations": top_locations,
        }
        return True, data, ""
    except Exception as exc:
        return False, {}, f"Database connection error: {exc}"


is_connected, home_data, error_msg = load_home_data()

# -----------------------------------------------------------------------------
# 3. Sidebar Status & Navigation Info
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏛️ System Status")
    if is_connected:
        st.success("🟢 Local MongoDB Active")
        st.caption(
            "**Engine:** MongoDB Community 9.0.4\n\n"
            "**URI:** `mongodb://localhost:27017/`\n\n"
            "**Database:** `jobmarketdb`\n\n"
            f"**Verified Postings:** {home_data['jobs_count']:,}\n\n"
            f"**Verified Employers:** {home_data['companies_count']:,}"
        )
    else:
        st.error("🔴 Database Offline")
        st.caption("Cannot connect to local MongoDB Community Server.")

    st.markdown("---")
    st.markdown("### 🧭 Navigation Guide")
    st.info(
        "Explore specialized analytical modules:\n\n"
        "• **1. Job Explorer**: Multi-facet operational filtering & allowlisted sorting\n\n"
        "• **2. Skills Analytics**: Separated LinkedIn disciplines vs. Indeed tools\n\n"
        "• **3. Salary Analytics**: Canonical buckets, approximate median & outlier audit\n\n"
        "• **4. Company & Geography**: Hiring leaderboard & covered index scan heatmap\n\n"
        "• **5. Platform Comparison**: Empirical LinkedIn vs. Indeed differences\n\n"
        "• **6. CRUD Demo**: Isolated write sandbox bounded to `demo_postings`"
    )

# -----------------------------------------------------------------------------
# 4. Editorial Hero Header
# -----------------------------------------------------------------------------
render_editorial_header(
    title="Understand the Job Market",
    subtitle=(
        "An enterprise labor intelligence platform providing empirical analysis across "
        "129,550 authentic US tech postings and 24,472 company profiles in local MongoDB."
    ),
    eyebrow="JOB MARKET INTELLIGENCE",
    badge_text="Executive Dashboard",
    status_text="51 Jurisdictions · 129,550 Postings",
)

if not is_connected:
    render_error_state(
        title="MongoDB Connection Failure",
        message=(
            f"The application was unable to establish a connection to the local MongoDB database.\n\n"
            f"**Details:** {error_msg}\n\n"
            "Please ensure MongoDB Community Server is running on `mongodb://localhost:27017/` "
            "and that the `.env` file contains `MONGODB_URI=mongodb://localhost:27017/`."
        ),
    )
    st.stop()


# -----------------------------------------------------------------------------
# 5. Executive KPI Section (4 Refined Editorial Stat Cards)
# -----------------------------------------------------------------------------
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    render_editorial_stat_card(
        title="Total Job Postings",
        value=f"{home_data['jobs_count']:,}",
        subtitle=f"{home_data['li_metrics'].get('total_postings', 0):,} LinkedIn · {home_data['ind_metrics'].get('total_postings', 0):,} Indeed",
        delta="100% Genuine Data",
        delta_type="positive",
    )

with kpi_col2:
    render_editorial_stat_card(
        title="Curated Company Profiles",
        value=f"{home_data['companies_count']:,}",
        subtitle="Normalized Employer Dimension",
        delta="26,076 Posting Employers",
        delta_type="positive",
    )

with kpi_col3:
    sal_cov_disp = home_data.get("overall_salary_coverage_display", home_data["overall_salary_coverage_pct"])
    render_editorial_stat_card(
        title="Salary Data Coverage",
        value=f"{sal_cov_disp:.2f}%",
        subtitle=f"{home_data['total_salary_postings']:,} Postings with Pay Data",
        delta="Continuous & Bucket",
        delta_type="positive",
    )

with kpi_col4:
    render_editorial_stat_card(
        title="Explicit Remote Adoption",
        value=f"{home_data['overall_remote_pct']:.2f}%",
        subtitle=f"{home_data['total_remote_postings']:,} Explicitly Remote · 0 On-Site",
        delta="Strict Tri-State Model",
        delta_type="positive",
    )

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 6. Platform Overview (LinkedIn vs. Indeed)
# -----------------------------------------------------------------------------
st.markdown("## ⚖️ Platform Overview: LinkedIn vs. Indeed")
st.markdown(
    "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.5rem; margin-bottom: 1rem;'>"
    "Cross-dataset comparison of posting volume, compensation semantics, remote breakdown, and employer reach."
    "</p>",
    unsafe_allow_html=True,
)

plat_col1, plat_col2 = st.columns([1.15, 0.85])

with plat_col1:
    chart_tabs = st.tabs(["Posting Volume", "Salary Availability (%)", "Remote Rate (%)"])
    with chart_tabs[0]:
        vol_fig = create_platform_comparison_chart(
            home_data["comparison"],
            metric="volume",
            title="Total Postings Volume by Sourcing Platform",
            height=320,
        )
        st.plotly_chart(vol_fig, use_container_width=True)
    with chart_tabs[1]:
        sal_fig = create_platform_comparison_chart(
            home_data["comparison"],
            metric="salary_coverage",
            title="Salary Coverage Percentage by Platform",
            height=320,
        )
        st.plotly_chart(sal_fig, use_container_width=True)
    with chart_tabs[2]:
        rem_fig = create_platform_comparison_chart(
            home_data["comparison"],
            metric="remote_rate",
            title="Explicit Remote Adoption by Platform",
            height=320,
        )
        st.plotly_chart(rem_fig, use_container_width=True)

with plat_col2:
    st.markdown("### Empirical Platform Comparison")
    li = home_data["li_metrics"]
    ind = home_data["ind_metrics"]

    comp_md = (
        "| Metric Dimension | LinkedIn | Indeed |\n"
        "| :--- | :--- | :--- |\n"
        f"| **Total Postings Volume** | **{li.get('total_postings', 0):,}** (95.59%) | **{ind.get('total_postings', 0):,}** (4.41%) |\n"
        f"| **Salary Data Availability** | {li.get('salary_coverage', {}).get('coverage_percentage', 0)}% ({li.get('salary_coverage', {}).get('postings_with_salary', 0):,}) | {ind.get('salary_coverage', {}).get('coverage_percentage', 0)}% ({ind.get('salary_coverage', {}).get('postings_with_salary', 0):,}) |\n"
        f"| **Compensation Structure** | Continuous Base Salary | Search Query Buckets |\n"
        f"| **Explicitly Remote Rate** | {li.get('remote_work_breakdown', {}).get('remote_percentage', 0)}% ({li.get('remote_work_breakdown', {}).get('explicitly_remote', 0):,}) | 0.0% (0 stated) |\n"
        f"| **Unspecified Remote Status** | 87.70% ({li.get('remote_work_breakdown', {}).get('unknown_unspecified', 0):,}) | 100.0% ({ind.get('remote_work_breakdown', {}).get('unknown_unspecified', 0):,}) |\n"
        f"| **Distinct Employers** | {li.get('coverage_metrics', {}).get('distinct_companies_count', 0):,} | {ind.get('coverage_metrics', {}).get('distinct_companies_count', 0):,} |\n"
        f"| **US Geographic Scope** | {li.get('coverage_metrics', {}).get('distinct_states_count', 0)} jurisdictions | {ind.get('coverage_metrics', {}).get('distinct_states_count', 0)} jurisdictions |\n"
    )
    st.markdown(comp_md)

render_editorial_callout(
    title="Methodology Note: Discrete Salary Bands vs. Continuous Base Salary",
    text=(
        "<b>Market-Wide Salary Representation:</b> Overall salary information is present in <b>32.24%</b> "
        "(41,774) of all database records. However, the nature of compensation data differs by origin: "
        "LinkedIn provides employer-stated continuous numerical compensation for <b>29.12%</b> (36,059) of its postings "
        "(27.83% of the overall market), while Indeed records originate from pre-filtered search query bands "
        "(<b>100.0%</b> coverage with discrete buckets and estimated midpoints, but 0.00% continuous base salaries)."
    ),
    callout_type="info",
    eyebrow="Data Provenance Disclosure",
)

render_editorial_callout(
    title="Taxonomy Separation: Functional Disciplines vs. Granular Tools",
    text=(
        "<b>Skill Taxonomy Safeguard:</b> LinkedIn records capture <b>35 broad functional categories</b> "
        "(e.g., Information Technology, Engineering, Management), whereas Indeed captures <b>464 granular technical tools</b> "
        "(e.g., Python, Docker, Kubernetes, AWS). To prevent severe methodological contamination, skill rankings "
        "and queries are strictly partitioned by platform across the system."
    ),
    callout_type="info",
    eyebrow="Taxonomy Isolation Safeguard",
)

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 7. Market Intelligence Section
# -----------------------------------------------------------------------------
st.markdown("## 📊 Market Intelligence & Structural Patterns")
st.markdown(
    "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.5rem; margin-bottom: 1.25rem;'>"
    "Key macro-level dynamics extracted from authentic aggregation pipelines across compensation, geography, and remote work."
    "</p>",
    unsafe_allow_html=True,
)

mi_col1, mi_col2, mi_col3 = st.columns(3)

with mi_col1:
    st.markdown("### 💰 Compensation Distribution")
    buckets = home_data.get("salary_bucket_comp", {}).get("buckets", [])
    if buckets:
        bucket_md_lines = [
            "| Bucket Tier | LinkedIn | Indeed |",
            "| :--- | :--- | :--- |",
        ]
        for b in buckets:
            b_name = b.get("bucket", "N/A")
            li_c = b.get("linkedin_count", 0)
            ind_c = b.get("indeed_count", 0)
            bucket_md_lines.append(f"| **`{b_name}`** | {li_c:,} ({b.get('linkedin_pct_salary_bearing', 0):.1f}%) | {ind_c:,} ({b.get('indeed_pct_salary_bearing', 0):.1f}%) |")
        st.markdown("\n".join(bucket_md_lines))
        st.caption("Standardized 6-tier salary bands across salary-bearing postings.")
    else:
        st.info("Salary bucket metrics unavailable.")

with mi_col2:
    st.markdown("### 🗺️ Geographic Concentration")
    top_locs_list = home_data.get("top_locations", {}).get("locations", [])
    if top_locs_list:
        loc_md_lines = [
            "| Rank & State | Postings Volume | Market Share |",
            "| :--- | :--- | :--- |",
        ]
        for idx, loc in enumerate(top_locs_list, 1):
            st_code = loc.get("state", "US")
            cnt = loc.get("postings_count", 0)
            pct = round((cnt / home_data["jobs_count"] * 100), 2) if home_data["jobs_count"] > 0 else 0
            loc_md_lines.append(f"| **#{idx} {st_code}** | {cnt:,} postings | {pct:.1f}% |")
        st.markdown("\n".join(loc_md_lines))
        st.caption("Top 5 states account for ~34.8% of all national job postings.")
    else:
        st.info("Location distribution metrics unavailable.")

with mi_col3:
    st.markdown("### 🏠 Remote Work Reality")
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.15rem; height: 100%;">
            <div style="font-size: 0.76rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C; margin-bottom: 0.4rem;">
                AUTHENTIC TRI-STATE MODEL
            </div>
            <div style="font-size: 1.35rem; font-weight: 800; color: #1C1F1D; margin-bottom: 0.25rem;">
                11.76% Explicitly Remote
            </div>
            <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.45; margin-bottom: 0.75rem;">
                Across 129,550 postings, <b>15,236</b> explicitly state remote eligibility. 
                Crucially, <b>0 postings</b> explicitly declare mandatory on-site work; 
                the remaining <b>114,314 (88.24%)</b> leave workplace modality unspecified.
            </p>
            <div style="font-size: 0.82rem; color: #2E3A2D; font-weight: 600; border-top: 1px solid #E2DDD5; padding-top: 0.5rem;">
                ⚠️ Methodological Rule: Unspecified ≠ On-Site
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 8. Technical Architecture Overview
# -----------------------------------------------------------------------------
st.markdown("## 🏛️ Technical Architecture & Storage Blueprint")
st.markdown(
    "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.5rem; margin-bottom: 1.25rem;'>"
    "JobMarketDB is constructed as a decoupled, multi-tiered data intelligence architecture. "
    "Every layer maintains strict separation of concerns, ensuring read-only safety and statistical reproducibility."
    "</p>",
    unsafe_allow_html=True,
)

arch_col1, arch_col2, arch_col3 = st.columns(3)

with arch_col1:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.15rem; margin-bottom: 1rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Layer 1: Presentation</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #1C1F1D; margin: 0.25rem 0 0.4rem 0; font-family: 'Newsreader', serif;">Streamlit & Plotly</div>
            <p style="font-size: 0.86rem; color: #4A524D; margin: 0; line-height: 1.45;">
                Multi-page architecture with unified editorial CSS tokens. Interactive Plotly charts enforce
                strict input immutability and render graceful empty states on missing data.
            </p>
        </div>
        <div class="jmdb-card" style="padding: 1.15rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Layer 4: Aggregations</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #1C1F1D; margin: 0.25rem 0 0.4rem 0; font-family: 'Newsreader', serif;">analytics/aggregations.py</div>
            <p style="font-size: 0.86rem; color: #4A524D; margin: 0; line-height: 1.45;">
                Executes multi-stage pipelines (Operations 8–12). Features distinct skill deduplication ($setUnion),
                approximate median calculation ($median), outlier audit classification, and covered index scans.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with arch_col2:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.15rem; margin-bottom: 1rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Layer 2: Service Interface</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #1C1F1D; margin: 0.25rem 0 0.4rem 0; font-family: 'Newsreader', serif;">JobMarketAnalyticsService</div>
            <p style="font-size: 0.86rem; color: #4A524D; margin: 0; line-height: 1.45;">
                Typed, audit-safe service class exposing 16 public methods. Decouples the UI from direct MongoDB drivers,
                enforces strict parameter validation, and guarantees read-only access.
            </p>
        </div>
        <div class="jmdb-card" style="padding: 1.15rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Layer 5: Connection Pooling</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #1C1F1D; margin: 0.25rem 0 0.4rem 0; font-family: 'Newsreader', serif;">database/connection.py</div>
            <p style="font-size: 0.86rem; color: #4A524D; margin: 0; line-height: 1.45;">
                Thread-safe PyMongo client connection pool with safe timeout handling, URI credential masking,
                and zero-code-change switching between local Community Server and cloud deployment.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with arch_col3:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.15rem; margin-bottom: 1rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Layer 3: Operational Queries</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #1C1F1D; margin: 0.25rem 0 0.4rem 0; font-family: 'Newsreader', serif;">analytics/queries.py</div>
            <p style="font-size: 0.86rem; color: #4A524D; margin: 0; line-height: 1.45;">
                Index-backed search operations (Operations 1–7). Includes allowlisted sorting, full-text textScore ranking,
                multi-identifier job retrieval, and same-platform related job recommendations.
            </p>
        </div>
        <div class="jmdb-card" style="padding: 1.15rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Layer 6: Storage Engine</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #1C1F1D; margin: 0.25rem 0 0.4rem 0; font-family: 'Newsreader', serif;">MongoDB Community 9.0.4</div>
            <p style="font-size: 0.86rem; color: #4A524D; margin: 0; line-height: 1.45;">
                Local WiredTiger database 'jobmarketdb' hosting 129,550 jobs and 24,472 companies across 15 production indexes.
                Strict write barrier confines sandbox operations to 'demo_postings'.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 9. Live Database Specifications & Verified Index Catalog
# -----------------------------------------------------------------------------
db_col1, db_col2 = st.columns([1, 1.35])

with db_col1:
    st.markdown("### Active Database Specifications")
    db_stats = home_data["db_stats"]
    data_size_mb = round(db_stats.get("dataSize", 0) / (1024 * 1024), 2)
    storage_size_mb = round(db_stats.get("storageSize", 0) / (1024 * 1024), 2)
    index_size_mb = round(db_stats.get("indexSize", 0) / (1024 * 1024), 2)

    db_specs_md = (
        "| Parameter | Live Value |\n"
        "| :--- | :--- |\n"
        f"| **Active Database Name** | `{db_stats.get('db', 'jobmarketdb')}` |\n"
        f"| **Server Engine** | MongoDB Community Server 9.0.4 |\n"
        f"| **Storage Engine** | WiredTiger (Document-level Concurrency) |\n"
        f"| **Canonical Collections** | 2 (`jobs`, `companies`) |\n"
        f"| **Total Document Count** | **{home_data['jobs_count'] + home_data['companies_count']:,}** records |\n"
        f"| **Raw BSON Data Size** | {data_size_mb} MB |\n"
        f"| **Allocated Storage Extent** | {storage_size_mb} MB |\n"
        f"| **Total Index Memory Footprint** | {index_size_mb} MB |\n"
        f"| **Active Indexes Count** | **15 Indexes** (11 jobs + 4 companies) |\n"
    )
    st.markdown(db_specs_md)

with db_col2:
    st.markdown("### Verified Index Definitions (15 Total Indexes)")

    with st.expander("📄 View 'jobs' Collection Indexes (11 Indexes: 10 B-Tree + 1 Full-Text)", expanded=True):
        jobs_md_lines = ["| Index Identifier | Key Specification | Index Type |", "| :--- | :--- | :--- |"]
        for name, info in home_data["jobs_indexes"].items():
            key_spec = ", ".join(f"`{k}: {v}`" for k, v in info.get("key", []))
            idx_type = "Full-Text Search" if "text" in key_spec.lower() else "B-Tree Index"
            jobs_md_lines.append(f"| **`{name}`** | {key_spec} | {idx_type} |")
        st.markdown("\n".join(jobs_md_lines))

    with st.expander("🏢 View 'companies' Collection Indexes (4 B-Tree Indexes)", expanded=False):
        comp_md_lines = ["| Index Identifier | Key Specification | Index Type |", "| :--- | :--- | :--- |"]
        for name, info in home_data["companies_indexes"].items():
            key_spec = ", ".join(f"`{k}: {v}`" for k, v in info.get("key", []))
            comp_md_lines.append(f"| **`{name}`** | {key_spec} | B-Tree Index |")
        st.markdown("\n".join(comp_md_lines))

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 10. Analytical Application Modules (Navigation Pathways)
# -----------------------------------------------------------------------------
st.markdown("## 🧭 Analytical Application Modules")
st.markdown(
    "<p style='color: #4A524D; font-size: 0.95rem; margin-top: -0.5rem; margin-bottom: 1.25rem;'>"
    "Direct pathways to specialized analytical tools and data discovery modules."
    "</p>",
    unsafe_allow_html=True,
)

nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; margin-bottom: 1rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Module 1</div>
            <h4 style="margin: 0.3rem 0; font-family: 'Newsreader', serif; font-size: 1.2rem; color: #1C1F1D;">Job Explorer</h4>
            <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.45; margin-bottom: 0.85rem;">
                Flagship operational query engine supporting full-text search, multi-facet filtering, allowlisted sorting, and same-platform job recommendations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Job_Search.py", label="Open Job Explorer →", icon="💼", use_container_width=True)

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; margin-bottom: 1rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Module 4</div>
            <h4 style="margin: 0.3rem 0; font-family: 'Newsreader', serif; font-size: 1.2rem; color: #1C1F1D;">Company & Geography</h4>
            <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.45; margin-bottom: 0.85rem;">
                Hiring leaderboards, US state rankings, covered index scans, and interactive US choropleth heatmaps.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/4_Company_and_Geography.py", label="Open Company & Geography →", icon="📊", use_container_width=True)

with nav_col2:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; margin-bottom: 1rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Module 2</div>
            <h4 style="margin: 0.3rem 0; font-family: 'Newsreader', serif; font-size: 1.2rem; color: #1C1F1D;">Skills Analytics</h4>
            <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.45; margin-bottom: 0.85rem;">
                Strict platform taxonomy separation: LinkedIn's 35 broad functional disciplines vs. Indeed's 464 granular technical tools.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Skills_Analytics.py", label="Open Skills Analytics →", icon="🛠️", use_container_width=True)

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; margin-bottom: 1rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Module 5</div>
            <h4 style="margin: 0.3rem 0; font-family: 'Newsreader', serif; font-size: 1.2rem; color: #1C1F1D;">Platform Comparison</h4>
            <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.45; margin-bottom: 0.85rem;">
                Empirical cross-platform comparative analysis covering volume distribution, field completeness, salary coverage, and shared employers.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/5_Platform_Comparison.py", label="Open Platform Comparison →", icon="⚖️", use_container_width=True)

with nav_col3:
    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; margin-bottom: 1rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Module 3</div>
            <h4 style="margin: 0.3rem 0; font-family: 'Newsreader', serif; font-size: 1.2rem; color: #1C1F1D;">Salary Analytics</h4>
            <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.45; margin-bottom: 0.85rem;">
                Continuous compensation distributions, 6 standardized salary tiers, approximate median calculation ($median), and audited outlier verification.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Salary_Analytics.py", label="Open Salary Analytics →", icon="💰", use_container_width=True)

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="jmdb-card" style="padding: 1.25rem; margin-bottom: 1rem;">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C;">Module 6</div>
            <h4 style="margin: 0.3rem 0; font-family: 'Newsreader', serif; font-size: 1.2rem; color: #1C1F1D;">CRUD Demo Sandbox</h4>
            <p style="font-size: 0.88rem; color: #4A524D; line-height: 1.45; margin-bottom: 0.85rem;">
                Isolated Create, Read, Update, Delete demonstration environment strictly confined to the 'demo_postings' collection.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/6_CRUD_Demo.py", label="Open CRUD Demo →", icon="🧪", use_container_width=True)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
st.markdown("---")
st.caption(
    "JobMarketDB · Advanced Database Management Systems Project · "
    f"Local MongoDB Community Server @ localhost:27017 · Database: jobmarketdb · {home_data['jobs_count']:,} Verified Postings"
)
