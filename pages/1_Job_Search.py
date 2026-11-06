"""
JobMarketDB — Flagship Product: Job Explorer (Phase 7 Stage 2)
Page: pages/1_Job_Search.py

A premium, editorial SaaS job discovery experience connected directly to the local
MongoDB Community Server repository (129,550 authentic postings, 24,472 companies):
- Prominent search experience with full-text indexing and regex matching modes
- Structured, categorized multi-facet filters: Platform, State, Remote, Salary, Skills, Company, Experience
- Active filter pill bar with quick-clear actions
- Allowlisted dynamic sorting (relevance, salary, posted date, title)
- Two-way pagination with zero duplicate or skipped records
- Elevated editorial job cards with typographic hierarchy and authentic badges
- Comprehensive single-job detail inspection with technical BSON provenance
- Methodologically isolated same-platform related job recommendations
"""

import html
import math
from typing import Any, Dict, List, Optional
import streamlit as st

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService
from utils.ui_components import (
    load_custom_css,
    render_header,
    render_editorial_header,
    render_metric_card,
    render_empty_state,
    render_error_state,
    render_callout,
    render_platform_badge,
    render_editorial_filter_bar,
    US_STATES,
)

# -----------------------------------------------------------------------------
# 1. Page Configuration & Editorial CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Job Explorer — JobMarketDB",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_custom_css()

# -----------------------------------------------------------------------------
# 2. Service Connection & Cached Helpers
# -----------------------------------------------------------------------------
@st.cache_resource
def get_analytics_service() -> Optional[JobMarketAnalyticsService]:
    """Provides cached database analytics service instance."""
    try:
        verify_connection()
        db = get_database()
        return JobMarketAnalyticsService(db)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_cached_popular_skills() -> List[str]:
    """Retrieves top demanded skills from the database for the filter dropdown."""
    service = get_analytics_service()
    if not service:
        return ["Python", "SQL", "Java", "AWS", "Machine Learning", "Communication", "Management", "Docker", "Git", "React"]
    try:
        data = service.get_top_skills(limit=80)
        skills_list = [item["skill"] for item in data.get("skills", []) if item.get("skill")]
        return skills_list if skills_list else ["Python", "SQL", "Java", "AWS"]
    except Exception:
        return ["Python", "SQL", "Java", "AWS", "Machine Learning", "Communication", "Management"]


# -----------------------------------------------------------------------------
# 3. Session State Management
# -----------------------------------------------------------------------------
if "selected_job_id" not in st.session_state:
    st.session_state.selected_job_id = None

if "search_page" not in st.session_state:
    st.session_state.search_page = 1

if "main_search_query" not in st.session_state:
    st.session_state.main_search_query = ""

def select_job(jid: str):
    st.session_state.selected_job_id = str(jid)

def deselect_job():
    st.session_state.selected_job_id = None

def reset_all_filters():
    st.session_state.search_page = 1
    st.session_state.main_search_query = ""
    # Clear filter widget keys if present
    for k in ["sb_query", "sb_platform", "sb_state", "sb_remote", "sb_salary_bucket",
              "sb_use_continuous", "sb_min_sal", "sb_max_sal", "sb_skills",
              "sb_skills_mode", "sb_company", "sb_exp", "sb_search_mode"]:
        if k in st.session_state:
            del st.session_state[k]

service = get_analytics_service()
if not service:
    render_header(
        title="Job Search & Multi-Facet Filtering",
        subtitle="Operational query engine connecting to local MongoDB repository.",
        badge_text="Module 1",
    )
    render_error_state(
        title="Database Connection Failure",
        message="Unable to connect to local MongoDB at mongodb://localhost:27017/jobmarketdb. Please ensure MongoDB service is active."
    )
    st.stop()


# -----------------------------------------------------------------------------
# 4. Helper Formatters (Safe Escaping & Strict Non-Fabrication)
# -----------------------------------------------------------------------------
def format_remote_badge(is_remote: Optional[bool]) -> str:
    """Renders distinct visual badges for all three authentic remote states without inference."""
    if is_remote is True:
        return '<span class="jmdb-meta-badge jmdb-meta-badge-remote">Remote</span>'
    elif is_remote is False:
        return '<span class="jmdb-meta-badge jmdb-meta-badge-onsite">Explicitly On-Site</span>'
    else:
        return '<span class="jmdb-meta-badge jmdb-meta-badge-unspecified">Not Specified</span>'


def format_salary_display(salary_dict: Optional[Dict[str, Any]]) -> str:
    """Formats salary info cleanly without fabricating missing numbers."""
    if not salary_dict or not isinstance(salary_dict, dict):
        return "Salary: Unstated"

    norm = salary_dict.get("normalized_annual")
    bucket = salary_dict.get("salary_bucket")
    min_sal = salary_dict.get("min_salary")
    max_sal = salary_dict.get("max_salary")
    period = salary_dict.get("pay_period")
    midpoint = salary_dict.get("estimated_midpoint")

    if norm is not None:
        return f"${norm:,.0f} / yr (Normalized)"
    elif min_sal is not None and max_sal is not None:
        p_str = f" / {period.lower()}" if period else ""
        return f"${min_sal:,.0f} – ${max_sal:,.0f}{p_str}"
    elif min_sal is not None:
        p_str = f" / {period.lower()}" if period else ""
        return f"From ${min_sal:,.0f}{p_str}"
    elif bucket:
        est_str = f" (~${midpoint:,.0f})" if midpoint else ""
        return f"Bucket: {html.escape(str(bucket))}{est_str}"
    return "Salary: Unstated"


# -----------------------------------------------------------------------------
# VIEW 1: SINGLE JOB DETAIL INSPECTION VIEW
# -----------------------------------------------------------------------------
if st.session_state.selected_job_id:
    job_id = st.session_state.selected_job_id
    try:
        job = service.get_job_by_id(job_id)
    except Exception:
        job = None

    if not job:
        render_header(
            title="Job Details",
            subtitle="Detailed record lookup and provenance.",
            badge_text="Record Not Found",
        )
        render_error_state("Record Not Found", f"No job document found for identifier: {job_id}")
        st.button("← Back to Search Results", on_click=deselect_job)
        st.stop()

    # Back navigation button
    col_nav1, col_nav2 = st.columns([1.5, 4.5])
    with col_nav1:
        st.button("← Back to Search Results", on_click=deselect_job, use_container_width=True)

    # Job Header Data
    title = job.get("title") or "Untitled Position"
    source = job.get("source") or "unknown"
    company_name = (job.get("company") or {}).get("name") or "Company Unstated"
    city = (job.get("location") or {}).get("city")
    state = (job.get("location") or {}).get("state")
    loc_str = f"{city}, {state}" if (city and state) else (state or city or (job.get("location") or {}).get("raw") or "Location Unspecified")
    is_remote = (job.get("location") or {}).get("is_remote")

    safe_title = html.escape(str(title))
    safe_company = html.escape(str(company_name))
    safe_loc = html.escape(str(loc_str))

    remote_badge_html = format_remote_badge(is_remote)
    platform_badge_html = render_platform_badge(source)

    # Elevated Detail Header Card
    st.markdown(
        f"""
        <div class="jmdb-detail-header">
            <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6E856C; margin-bottom: 0.35rem;">
                RECORD INSPECTION // VERIFIED DATA PROVENANCE
            </div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.75rem;">
                <div>
                    <h1 style="color: #1C1F1D; margin: 0 0 0.5rem 0; font-family: 'Newsreader', serif; font-size: 2.15rem; font-weight: 700; line-height: 1.25;">
                        {safe_title}
                    </h1>
                    <div style="font-size: 1.05rem; color: #4A524D; font-weight: 600; margin-bottom: 0.25rem;">
                        🏢 {safe_company} &nbsp;•&nbsp; 📍 {safe_loc}
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    {platform_badge_html}{remote_badge_html}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Key Metrics Bar (4 structured KPI cards)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        sal_display = format_salary_display(job.get("salary"))
        st.metric("Salary Compensation", sal_display)
    with m2:
        exp_val = (job.get("experience_level") or {}).get("value") or "Not Stated"
        st.metric("Experience Level", exp_val)
    with m3:
        emp_type = job.get("normalized_employment_type") or job.get("source_employment_type") or "Not Stated"
        st.metric("Employment Type", emp_type)
    with m4:
        posted = job.get("posted_date") or job.get("estimated_posted_date")
        posted_str = str(posted)[:10] if posted else "Unstated"
        st.metric("Posted Date", posted_str)

    # Job Actions & External Link
    job_url = job.get("job_url") or job.get("application_url")
    if job_url:
        st.markdown(
            f"""
            <div style="margin: 1.25rem 0 1.5rem 0;">
                <a href="{html.escape(job_url)}" target="_blank" style="display: inline-flex; align-items: center; gap: 0.5rem; background-color: #2E3A2D; color: #FFFFFF; padding: 0.55rem 1.35rem; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 0.92rem; box-shadow: 0 2px 6px rgba(46,58,45,0.2);">
                    🔗 Open Authentic Posting on {source.title()} ↗
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Skills Section
    skills = job.get("skills") or []
    if skills:
        st.markdown("### Required & Extracted Skills")
        skill_chips = "".join([f'<span class="jmdb-skill-chip" style="font-size: 0.82rem; padding: 0.25rem 0.75rem;">{html.escape(str(s))}</span>' for s in skills])
        st.markdown(f'<div class="jmdb-skill-container" style="margin-bottom: 1.5rem;">{skill_chips}</div>', unsafe_allow_html=True)

    # Job Description
    desc = job.get("description")
    if desc:
        st.markdown("### Full Job Description")
        safe_desc = html.escape(str(desc))
        st.markdown(f'<div class="jmdb-detail-desc">{safe_desc}</div>', unsafe_allow_html=True)
    else:
        st.info("Full textual description is not present in this source document.")

    # Technical Provenance & Document Invariants
    with st.expander("🔬 MongoDB Document Inspection & Technical Provenance", expanded=False):
        c_info = job.get("company") or {}
        s_info = job.get("salary") or {}
        l_info = job.get("location") or {}

        prov_rows = f"""
        | Field | Authentic Value in MongoDB |
        | :--- | :--- |
        | **MongoDB `_id`** | `{job.get('_id')}` |
        | **Source Platform** | `{job.get('source')}` |
        | **Source Job ID** | `{job.get('source_job_id')}` |
        | **Company ID** | `{c_info.get('company_id')}` |
        | **Company Size** | `{c_info.get('company_size') or 'null'}` |
        | **Company Industry** | `{c_info.get('industry') or 'null'}` |
        | **Raw Location** | `{l_info.get('raw') or 'null'}` |
        | **Standardized State** | `{l_info.get('state') or 'null'}` |
        | **Normalized Annual Salary** | `{s_info.get('normalized_annual') or 'null'}` |
        | **Salary Bucket** | `{s_info.get('salary_bucket') or 'null'}` |
        | **Compensation Type** | `{s_info.get('compensation_type') or 'null'}` |
        | **Views Count** | `{job.get('views_count') if job.get('views_count') is not None else 'null'}` |
        | **Applies Count** | `{job.get('applies_count') if job.get('applies_count') is not None else 'null'}` |
        | **Role Category** | `{(job.get('role_category') or {}).get('value') or 'null'}` |
        """
        st.markdown(prov_rows)

    # Related Jobs Recommendation Section (Same-Platform Strictly Enforced)
    st.markdown("---")
    st.markdown("### Related Job Recommendations (Same-Platform)")
    render_callout(
        title="Priority 2 Methodological Safeguard: Same-Platform Taxonomy Isolation",
        text=(
            f"Recommendations are strictly restricted to <b>{source.title()}</b> postings. "
            "This mathematically prevents LinkedIn's 35 broad functional domains from contaminating "
            "Indeed's 464 granular technical tools. Postings are scored and ranked transparently "
            "based on shared skills, role category matching, and state proximity."
        ),
        callout_type="info",
    )

    try:
        related_jobs = service.get_related_jobs(job_id, limit=5)
    except Exception:
        related_jobs = []

    if not related_jobs:
        st.info("No related postings found on this platform with matching attributes.")
    else:
        for rel in related_jobs:
            rel_id = rel.get("_id")
            rel_title = rel.get("title") or "Untitled Position"
            rel_comp = (rel.get("company") or {}).get("name") or "Company Unstated"
            rel_loc = (rel.get("location") or {}).get("state") or "US"
            rel_sal = format_salary_display(rel.get("salary"))

            exp = rel.get("match_explanation") or {}
            score = exp.get("match_score", 0)
            shared_s = exp.get("shared_skills", [])
            same_role = exp.get("same_role_category", False)

            shared_chips = "".join([f'<span class="jmdb-skill-chip jmdb-skill-chip-matched">{html.escape(str(s))}</span>' for s in shared_s])
            role_badge = '<span class="jmdb-meta-badge" style="background-color: #E8EDE7; color: #2E3A2D; font-weight: 600;">Shared Role Category</span>' if same_role else ''

            with st.container():
                st.markdown(
                    f"""
                    <div class="jmdb-related-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem;">
                            <div>
                                <b style="color: #1C1F1D; font-size: 1.05rem; font-family: 'Newsreader', serif;">{html.escape(str(rel_title))}</b>
                                <div style="color: #4A524D; font-size: 0.86rem; margin: 0.2rem 0;">🏢 {html.escape(str(rel_comp))} &nbsp;•&nbsp; 📍 {html.escape(str(rel_loc))} &nbsp;•&nbsp; 💰 {html.escape(str(rel_sal))}</div>
                            </div>
                            <span class="jmdb-badge jmdb-badge-pill" style="font-size: 0.74rem;">Match Score: {score}</span>
                        </div>
                        <div style="display: flex; gap: 0.4rem; align-items: center; margin-top: 0.5rem; flex-wrap: wrap;">{role_badge}{shared_chips}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.button(f"View Recommendation: {rel_title[:45]}...", key=f"rel_btn_{rel_id}", on_click=select_job, args=(rel_id,))

    st.stop()


# -----------------------------------------------------------------------------
# VIEW 2: SEARCH & RESULTS VIEW (DEFAULT FLAGSHIP DISCOVERY)
# -----------------------------------------------------------------------------

# Refined Editorial Page Header
render_editorial_header(
    title="Job Explorer — Job Search & Multi-Facet Filtering",
    subtitle="Operational query engine supporting full-text search, multi-facet filtering, and allowlisted sorting across 129,550 authentic postings.",
    eyebrow="Market Intelligence Discovery Engine",
    badge_text="Module 1",
    status_text="129,550 Live Postings",
)

# -----------------------------------------------------------------------------
# Sidebar: Structured & Grouped Filters
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🔍 Search & Filters")

# Group 1: Search Parameters
st.sidebar.markdown("#### 1. Discovery Mode")
search_mode_option = st.sidebar.radio(
    "Search Mode",
    options=["Full-Text Search (Title & Description)", "Title Regex Match"],
    index=0,
    key="sb_search_mode",
    help="Full-text searches title and description via MongoDB text index 'title_text_description_text'. Regex matches title specifically. Skills are queried separately via multikey index 'skills_1'.",
)
search_mode = "text" if "Full-Text" in search_mode_option else "regex"

platform_choice = st.sidebar.selectbox(
    "Platform Source",
    options=["Both Platforms (LinkedIn & Indeed)", "LinkedIn Only", "Indeed Only"],
    index=0,
    key="sb_platform",
)
platform_filter = None
if platform_choice == "LinkedIn Only":
    platform_filter = "linkedin"
elif platform_choice == "Indeed Only":
    platform_filter = "indeed"

# Group 2: Geography & Work Model
st.sidebar.markdown("---")
st.sidebar.markdown("#### 2. Location & Work Model")

state_choice = st.sidebar.selectbox(
    "Filter by US State",
    options=["All States"] + list(US_STATES),
    index=0,
    key="sb_state",
)
state_filter = None if state_choice == "All States" else state_choice

remote_choice = st.sidebar.selectbox(
    "Remote Status",
    options=[
        "Any Remote Status",
        "Remote (True)",
        "Explicitly On-Site (False)",
        "Not Specified (None)",
    ],
    index=0,
    key="sb_remote",
    help="Preserves authentic tri-state semantics without inference: Remote (15,236), Not Specified (114,314), Explicitly On-Site (0).",
)
remote_filter: Any = "any"
if remote_choice == "Remote (True)":
    remote_filter = True
elif remote_choice == "Explicitly On-Site (False)":
    remote_filter = False
elif remote_choice == "Not Specified (None)":
    remote_filter = None

# Group 3: Compensation & Salary
st.sidebar.markdown("---")
st.sidebar.markdown("#### 3. Compensation")

salary_bucket_choice = st.sidebar.selectbox(
    "Salary Bucket",
    options=["All Buckets", "<80000", "80000-99999", "100000-119999", "120000-139999", "140000-159999", ">160000"],
    index=0,
    key="sb_salary_bucket",
)
salary_bucket_filter = None if salary_bucket_choice == "All Buckets" else salary_bucket_choice

use_continuous_salary = st.sidebar.checkbox("Filter by Continuous Salary Range ($)", key="sb_use_continuous")
min_annual_filter = None
max_annual_filter = None
if use_continuous_salary:
    col_sal1, col_sal2 = st.sidebar.columns(2)
    with col_sal1:
        min_annual_val = st.number_input("Min $ / yr", min_value=0, max_value=500000, value=50000, step=5000, key="sb_min_sal")
        min_annual_filter = float(min_annual_val)
    with col_sal2:
        max_annual_val = st.number_input("Max $ / yr", min_value=0, max_value=500000, value=150000, step=5000, key="sb_max_sal")
        max_annual_filter = float(max_annual_val)

# Group 4: Role & Qualifications
st.sidebar.markdown("---")
st.sidebar.markdown("#### 4. Role & Qualifications")

popular_skills = get_cached_popular_skills()
selected_skills = st.sidebar.multiselect(
    "Required Skills",
    options=popular_skills,
    default=[],
    key="sb_skills",
    help="Select skills to filter postings.",
)

skills_match_mode = st.sidebar.radio(
    "Skills Matching Logic",
    options=["Match ALL Selected Skills ($all)", "Match ANY Selected Skill ($in)"],
    index=0,
    key="sb_skills_mode",
)
skills_match_all = True if "ALL" in skills_match_mode else False

company_input = st.sidebar.text_input(
    "Company Name",
    value="",
    placeholder="e.g. Google, Amazon, Express Scripts...",
    key="sb_company",
)
company_filter = company_input.strip() if company_input.strip() else None

exp_choice = st.sidebar.selectbox(
    "Experience Level",
    options=["All Experience Levels", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive", "Internship"],
    index=0,
    key="sb_exp",
)
experience_filter = None if exp_choice == "All Experience Levels" else exp_choice

# Reset Action
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset All Filters", use_container_width=True):
    reset_all_filters()
    st.rerun()


# -----------------------------------------------------------------------------
# Main View: Prominent Search Experience
# -----------------------------------------------------------------------------
search_col1, search_col2 = st.columns([4.2, 0.8])
with search_col1:
    main_query_input = st.text_input(
        "Search Postings",
        value=st.session_state.main_search_query,
        placeholder="Search job title, description, or keywords (e.g. Software Engineer, Machine Learning, Python)...",
        label_visibility="collapsed",
        key="main_search_box",
    )
with search_col2:
    if st.button("Search", type="primary", use_container_width=True):
        st.session_state.search_page = 1
        st.session_state.main_search_query = main_query_input
        st.rerun()

clean_query = main_query_input.strip() if main_query_input.strip() else None


# -----------------------------------------------------------------------------
# Main View: Sorting, Pagination Configuration & Active Constraint Pills
# -----------------------------------------------------------------------------
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1.5, 1])

with ctrl_col1:
    sort_choice = st.selectbox(
        "Sort By",
        options=[
            "Relevance (Default for Search)",
            "Salary (Normalized Annual)",
            "Posted Date",
            "Job Title",
        ],
        index=0,
    )
    sort_mapping = {
        "Relevance (Default for Search)": "relevance",
        "Salary (Normalized Annual)": "salary",
        "Posted Date": "posted_date",
        "Job Title": "title",
    }
    sort_by = sort_mapping[sort_choice]

with ctrl_col2:
    order_choice = st.selectbox(
        "Sort Order",
        options=["Descending (Highest / Newest)", "Ascending (Lowest / Oldest)"],
        index=0,
    )
    sort_order = -1 if "Descending" in order_choice else 1

with ctrl_col3:
    page_size = st.selectbox(
        "Page Size",
        options=[10, 20, 50],
        index=0,
    )


# -----------------------------------------------------------------------------
# Query Execution with Pagination
# -----------------------------------------------------------------------------
current_page = st.session_state.search_page
skip_count = (current_page - 1) * page_size

with st.spinner("Querying JobMarketDB MongoDB repository..."):
    try:
        results, total_count = service.search_and_filter(
            query_text=clean_query,
            search_mode=search_mode,
            state=state_filter,
            is_remote=remote_filter,
            salary_bucket=salary_bucket_filter,
            min_annual=min_annual_filter,
            max_annual=max_annual_filter,
            skills=selected_skills if selected_skills else None,
            skills_match_all=skills_match_all,
            company_name=company_filter,
            experience_level=experience_filter,
            source=platform_filter,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=page_size,
            skip=skip_count,
        )
    except Exception as e:
        render_error_state("Database Query Execution Error", str(e))
        st.stop()

total_pages = max(1, math.ceil(total_count / page_size)) if total_count > 0 else 1

# Reset page if out of bounds due to updated filters
if current_page > total_pages:
    st.session_state.search_page = 1
    st.rerun()


# -----------------------------------------------------------------------------
# Active Filters Summary Bar (Editorial Pills)
# -----------------------------------------------------------------------------
active_chips = []
if clean_query:
    active_chips.append({"label": "Query", "value": f'"{clean_query}" ({search_mode})'})
if platform_filter:
    active_chips.append({"label": "Platform", "value": platform_filter.title()})
if state_filter:
    active_chips.append({"label": "State", "value": state_filter})
if remote_filter is True:
    active_chips.append({"label": "Remote", "value": "Remote"})
elif remote_filter is False:
    active_chips.append({"label": "Remote", "value": "Explicitly On-Site"})
elif remote_filter is None:
    active_chips.append({"label": "Remote", "value": "Not Specified"})
if salary_bucket_filter:
    active_chips.append({"label": "Salary Bucket", "value": salary_bucket_filter})
if min_annual_filter is not None or max_annual_filter is not None:
    active_chips.append({"label": "Range", "value": f"${min_annual_filter:,.0f}–${max_annual_filter:,.0f}"})
if selected_skills:
    logic_str = "ALL" if skills_match_all else "ANY"
    active_chips.append({"label": f"Skills ({logic_str})", "value": ", ".join(selected_skills)})
if company_filter:
    active_chips.append({"label": "Company", "value": company_filter})
if experience_filter:
    active_chips.append({"label": "Experience", "value": experience_filter})

if active_chips:
    render_editorial_filter_bar(active_chips, title="Active Filter Constraints")

# Result Count & Pagination Info Header
start_idx = ((current_page - 1) * page_size) + 1 if total_count > 0 else 0
end_idx = min(current_page * page_size, total_count)
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin: 1rem 0 0.5rem 0; padding-bottom: 0.5rem; border-bottom: 1px solid #E2DDD5;">
        <span style="font-size: 1.12rem; font-weight: 700; color: #1C1F1D; font-family: 'Newsreader', serif;">
            Found <span style="color: #2E3A2D; font-weight: 800;">{total_count:,}</span> matching postings
        </span>
        <span style="font-size: 0.88rem; color: #4A524D; font-family: 'Plus Jakarta Sans', sans-serif;">
            Showing {start_idx:,}–{end_idx:,} of {total_count:,} (Page {current_page} of {total_pages})
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Empty State Handling
# -----------------------------------------------------------------------------
if total_count == 0:
    render_empty_state(
        title="No Matching Job Postings Found",
        message="No authentic records match your selected filter criteria. Try broadening keyword spelling, selecting 'Any Remote Status', or clearing specific constraints.",
        icon="🔍",
    )
    if st.button("Clear All Filters & Reset", on_click=reset_all_filters):
        st.rerun()
    st.stop()


def go_to_next_page():
    st.session_state.search_page += 1

def go_to_prev_page():
    st.session_state.search_page = max(1, st.session_state.search_page - 1)


# -----------------------------------------------------------------------------
# Top Pagination Bar
# -----------------------------------------------------------------------------
p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
with p_col1:
    st.button("← Previous Page", disabled=(current_page <= 1), on_click=go_to_prev_page, key="top_prev", use_container_width=True)
with p_col2:
    st.markdown(
        f"<div style='text-align: center; padding-top: 6px; font-size: 0.88rem; color: #4A524D; font-family: Plus Jakarta Sans, sans-serif;'>"
        f"Page <b>{current_page}</b> of <b>{total_pages}</b>"
        f"</div>",
        unsafe_allow_html=True,
    )
with p_col3:
    st.button("Next Page →", disabled=(current_page >= total_pages), on_click=go_to_next_page, key="top_next", use_container_width=True)

st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Elevated Job Cards Listing
# -----------------------------------------------------------------------------
for job in results:
    j_id = str(job.get("_id"))
    j_title = job.get("title") or "Untitled Position"
    j_source = job.get("source") or "unknown"
    j_comp = (job.get("company") or {}).get("name") or "Company Unstated"
    j_city = (job.get("location") or {}).get("city")
    j_state = (job.get("location") or {}).get("state")
    j_loc = f"{j_city}, {j_state}" if (j_city and j_state) else (j_state or j_city or (job.get("location") or {}).get("raw") or "US")
    j_is_remote = (job.get("location") or {}).get("is_remote")

    j_salary_str = format_salary_display(job.get("salary"))
    j_exp = (job.get("experience_level") or {}).get("value")
    j_emp_type = job.get("normalized_employment_type") or job.get("source_employment_type")
    j_skills = job.get("skills") or []
    j_url = job.get("job_url") or job.get("application_url")
    posted_raw = job.get("posted_date") or job.get("estimated_posted_date")
    posted_disp = str(posted_raw)[:10] if posted_raw else None

    # Safe escaping
    safe_j_title = html.escape(str(j_title))
    safe_j_comp = html.escape(str(j_comp))
    safe_j_loc = html.escape(str(j_loc))

    # Badges
    p_badge = render_platform_badge(j_source)
    r_badge = format_remote_badge(j_is_remote)
    sal_badge = (
        f'<span class="jmdb-meta-badge jmdb-meta-badge-salary">💰 {html.escape(j_salary_str)}</span>'
        if "Unstated" not in j_salary_str
        else '<span class="jmdb-meta-badge">💰 Salary Unstated</span>'
    )
    exp_badge = f'<span class="jmdb-meta-badge">Grading: {html.escape(str(j_exp))}</span>' if j_exp else ''
    emp_badge = f'<span class="jmdb-meta-badge">Type: {html.escape(str(j_emp_type))}</span>' if j_emp_type else ''
    date_badge = f'<span class="jmdb-meta-badge" style="color: #737D76;">📅 {html.escape(posted_disp)}</span>' if posted_disp else ''

    # Skills chips: prioritize matched filter skills and visually highlight them
    if selected_skills:
        matched_s = [s for s in j_skills if s in selected_skills]
        other_s = [s for s in j_skills if s not in selected_skills]
        ordered_s = matched_s + other_s
    else:
        matched_s = []
        ordered_s = j_skills

    chip_list = []
    for s in ordered_s[:8]:
        safe_s = html.escape(str(s))
        if s in matched_s:
            chip_list.append(f'<span class="jmdb-skill-chip jmdb-skill-chip-matched">{safe_s}</span>')
        else:
            chip_list.append(f'<span class="jmdb-skill-chip">{safe_s}</span>')
    if len(ordered_s) > 8:
        chip_list.append(f'<span class="jmdb-skill-chip">+{len(ordered_s)-8} more</span>')
    s_chips = "".join(chip_list)

    # Render Elevated Job Card
    with st.container():
        st.markdown(
            f"""
            <div class="jmdb-job-card">
                <div class="jmdb-job-header">
                    <div>
                        <h3 class="jmdb-job-title">{safe_j_title}</h3>
                        <div class="jmdb-job-company">🏢 <b>{safe_j_comp}</b> &nbsp;•&nbsp; 📍 {safe_j_loc}</div>
                    </div>
                    <div style="display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap;">{p_badge}{r_badge}</div>
                </div>
                <div class="jmdb-job-meta-row">{sal_badge}{exp_badge}{emp_badge}{date_badge}</div>
                <div class="jmdb-skill-container">{s_chips}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Card action buttons row
        btn_c1, btn_c2 = st.columns([1.5, 4.5])
        with btn_c1:
            st.button("📄 View Full Details", key=f"view_{j_id}", on_click=select_job, args=(j_id,), use_container_width=True)
        with btn_c2:
            if j_url:
                st.markdown(
                    f'<div style="padding-top: 6px;"><a href="{html.escape(j_url)}" target="_blank" style="color: #2E3A2D; text-decoration: none; font-size: 0.88rem; font-weight: 600;">🔗 Open Original {j_source.title()} Posting ↗</a></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='margin-bottom: 0.4rem;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Bottom Pagination Bar
# -----------------------------------------------------------------------------
st.markdown("---")
b_col1, b_col2, b_col3 = st.columns([1, 2, 1])
with b_col1:
    st.button("← Previous Page", disabled=(current_page <= 1), on_click=go_to_prev_page, key="bot_prev", use_container_width=True)
with b_col2:
    st.markdown(
        f"<div style='text-align: center; padding-top: 6px; font-size: 0.88rem; color: #4A524D; font-family: Plus Jakarta Sans, sans-serif;'>"
        f"Page <b>{current_page}</b> of <b>{total_pages}</b> ({start_idx:,}–{end_idx:,} of {total_count:,})"
        f"</div>",
        unsafe_allow_html=True,
    )
with b_col3:
    st.button("Next Page →", disabled=(current_page >= total_pages), on_click=go_to_next_page, key="bot_next", use_container_width=True)
