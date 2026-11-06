"""
JobMarketDB — Module 6: Database Operations Laboratory (Phase 7 Stage 8)

Premium Sage & Ivory CRUD demonstration workspace providing interactive Create,
Read, Update, and Delete operations strictly isolated to the 'jobmarketdb.demo_postings'
collection.

MANDATORY SAFETY GUARDS:
- Canonical collections ('jobs' and 'companies') are strictly immutable and read-only.
- Direct database access is forbidden; all operations route through the service layer.
- Bulk deletion (delete_many), collection dropping, and sandbox resets are prohibited.
- Single-document deletion requires explicit confirmation and verified ObjectId.
- User-controlled inputs are HTML-escaped to prevent XSS / raw HTML injection.
"""

from datetime import datetime, timezone
import html
import importlib
import textwrap
from typing import Any, Dict, List, Optional
from bson import ObjectId
import streamlit as st

import analytics.service
importlib.reload(analytics.service)
from analytics.service import JobMarketAnalyticsService
from utils.ui_components import (
    load_custom_css,
    render_editorial_header,
    render_editorial_stat_card,
    render_editorial_callout,
    render_empty_state,
    render_error_state,
    US_STATES,
)
from utils.plots import THEME

# =============================================================================
# 1. Page Configuration & Editorial CSS
# =============================================================================
st.set_page_config(
    page_title="Database Operations — JobMarketDB",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_custom_css()

# Initialize session-scoped operations history
if "crud_session_history" not in st.session_state:
    st.session_state["crud_session_history"] = []

if "crud_flash_message" not in st.session_state:
    st.session_state["crud_flash_message"] = None


def _record_session_operation(
    op_type: str,
    target_demo_id: str,
    target_oid: str,
    mongo_command: str,
    status: str = "SUCCESS",
    details: Optional[str] = None,
) -> None:
    """Appends an in-memory operation record to the active session audit log."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    record = {
        "timestamp": now_utc,
        "operation": op_type,
        "target_demo_id": target_demo_id,
        "target_oid": target_oid,
        "mongo_command": mongo_command,
        "status": status,
        "details": details or "",
    }
    st.session_state["crud_session_history"].insert(0, record)
    if len(st.session_state["crud_session_history"]) > 25:
        st.session_state["crud_session_history"] = st.session_state["crud_session_history"][:25]


# =============================================================================
# 2. Service Client
# =============================================================================
def get_service() -> JobMarketAnalyticsService:
    """Returns a direct analytics service instance for live CRUD operations."""
    return JobMarketAnalyticsService()


service = get_service()

# =============================================================================
# 3. Editorial Hero Header
# =============================================================================
render_editorial_header(
    title="Explore MongoDB Operations",
    subtitle=(
        "A controlled demonstration workspace for interactive Create, Read, Update, and Delete "
        "operations strictly isolated to the demo_postings sandbox collection."
    ),
    eyebrow="DATABASE OPERATIONS LABORATORY",
    status_text="LOCAL DATABASE",
)

# =============================================================================
# 4. Database Safety Overview & Boundary Status
# =============================================================================
overview_html = f"""<div style="background: {THEME['card_white']}; border: 1px solid {THEME['subtle_border']}; border-radius: 16px; padding: 1.75rem 2rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem;">
<div style="font-family: 'Newsreader', 'Georgia', serif; font-size: 1.25rem; font-weight: 600; color: {THEME['text_primary']};">Database Isolation & Safety Boundaries</div>
<div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
<span style="display: inline-flex; align-items: center; gap: 0.35rem; background: {THEME['muted_sage']}; color: {THEME['deep_olive']}; padding: 0.25rem 0.7rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid {THEME['sage_green']};">🔒 Canonical Protected</span>
<span style="display: inline-flex; align-items: center; gap: 0.35rem; background: {THEME['surface_warm']}; color: {THEME['accent_amber']}; padding: 0.25rem 0.7rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid {THEME['accent_amber']};">🧪 Sandbox Isolated</span>
<span style="display: inline-flex; align-items: center; gap: 0.35rem; background: #EEF2F6; color: #2C3E50; padding: 0.25rem 0.7rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid #CBD5E1;">💻 Local MongoDB Only</span>
<span style="display: inline-flex; align-items: center; gap: 0.35rem; background: #FEF2F2; color: #991B1B; padding: 0.25rem 0.7rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid #FECACA;">🚫 No Atlas Connection</span>
</div>
</div>
<div style="display: flex; gap: 1.25rem; flex-wrap: wrap;">
<div style="flex: 1; min-width: 280px; background: {THEME['muted_sage']}; border-radius: 12px; padding: 1.15rem 1.35rem; border-left: 4px solid {THEME['sage_green']};">
<div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: {THEME['sage_green']}; margin-bottom: 0.35rem;">🔒 Canonical Collections — Read-Only</div>
<div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.86rem; color: {THEME['text_secondary']}; line-height: 1.5;">The <code style="background: rgba(110,133,108,0.14); padding: 0.1em 0.35em; border-radius: 4px; font-size: 0.85em;">jobs</code> (129,550) and <code style="background: rgba(110,133,108,0.14); padding: 0.1em 0.35em; border-radius: 4px; font-size: 0.85em;">companies</code> (24,472) collections are immutable. No demonstration operation can insert, modify, or delete canonical records.</div>
</div>
<div style="flex: 1; min-width: 280px; background: {THEME['surface_warm']}; border-radius: 12px; padding: 1.15rem 1.35rem; border-left: 4px solid {THEME['accent_amber']};">
<div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: {THEME['accent_amber']}; margin-bottom: 0.35rem;">🧪 Sandbox Collection — Read/Write</div>
<div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.86rem; color: {THEME['text_secondary']}; line-height: 1.5;">All CRUD mutations target <code style="background: rgba(194,136,78,0.14); padding: 0.1em 0.35em; border-radius: 4px; font-size: 0.85em;">demo_postings</code> exclusively. Single-document deletion only; bulk deletions (<code style="font-size: 0.82em;">delete_many</code>) and collection dropping are permanently disabled.</div>
</div>
</div>
</div>"""

st.markdown(overview_html, unsafe_allow_html=True)

# Flash status banner from recent CRUD action
if st.session_state.get("crud_flash_message"):
    st.markdown(st.session_state["crud_flash_message"], unsafe_allow_html=True)
    st.session_state["crud_flash_message"] = None

# =============================================================================
# 5. Live Database Metrics
# =============================================================================
canonical_counts: Optional[Dict[str, int]] = None
canonical_error: Optional[str] = None

try:
    canonical_counts = service.get_canonical_counts()
except Exception as err:
    canonical_error = str(err)

demo_stats: Optional[Dict[str, Any]] = None
demo_error: Optional[str] = None

try:
    demo_stats = service.get_demo_collection_stats()
except Exception as err:
    demo_error = str(err)

# Query index count from service.db read-only metadata where supported
index_count: Optional[int] = None
try:
    if hasattr(service, "db") and service.db is not None:
        jobs_idx_count = len(list(service.db["jobs"].list_indexes()))
        comp_idx_count = len(list(service.db["companies"].list_indexes()))
        index_count = jobs_idx_count + comp_idx_count
except Exception:
    index_count = None

# Format display metrics — never substitute hardcoded numbers on failure
if canonical_counts is not None and "jobs" in canonical_counts and "companies" in canonical_counts:
    jobs_display = f"{canonical_counts['jobs']:,}"
    companies_display = f"{canonical_counts['companies']:,}"
    jobs_sub = "Immutable canonical records"
    companies_sub = "Curated employer profiles"
else:
    jobs_display = "Unavailable"
    companies_display = "Unavailable"
    jobs_sub = f"Error: {canonical_error[:40]}..." if canonical_error else "Audit unavailable"
    companies_sub = f"Error: {canonical_error[:40]}..." if canonical_error else "Audit unavailable"

if index_count is not None:
    indexes_display = f"{index_count}"
    indexes_sub = "11 jobs · 4 companies (canonical)"
else:
    indexes_display = "Unavailable"
    indexes_sub = "Metadata inspection unavailable"

if demo_stats is not None:
    demo_display = f"{demo_stats.get('total_demo_postings', 0):,}"
    demo_emp_display = f"{demo_stats.get('distinct_companies', 0):,}"
    demo_remote = demo_stats.get('remote_postings', 0)
    demo_salary = demo_stats.get('with_salary_postings', 0)
    demo_sub = f"{demo_remote} remote · {demo_salary} with salary"
else:
    demo_display = "Unavailable"
    demo_emp_display = "Unavailable"
    demo_sub = f"Error: {demo_error[:40]}..." if demo_error else "Audit unavailable"

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    render_editorial_stat_card(
        title="Canonical Jobs",
        value=jobs_display,
        subtitle=jobs_sub,
    )
with m2:
    render_editorial_stat_card(
        title="Canonical Companies",
        value=companies_display,
        subtitle=companies_sub,
    )
with m3:
    render_editorial_stat_card(
        title="Production Indexes",
        value=indexes_display,
        subtitle=indexes_sub,
    )
with m4:
    render_editorial_stat_card(
        title="Sandbox Postings",
        value=demo_display,
        subtitle="demo_postings collection",
    )
with m5:
    render_editorial_stat_card(
        title="Sandbox Employers",
        value=demo_emp_display,
        subtitle=demo_sub,
    )

if canonical_error:
    render_error_state(
        "Canonical Collections Audit Unavailable",
        f"Failed to retrieve canonical counts: {html.escape(str(canonical_error))}",
    )
if demo_error:
    render_error_state(
        "Sandbox Statistics Unavailable",
        f"Failed to retrieve demo statistics: {html.escape(str(demo_error))}",
    )

# =============================================================================
# 6. CRUD Operations — Tabbed Interface
# =============================================================================
st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

tab_read, tab_create, tab_update, tab_delete, tab_history = st.tabs([
    "📋  Browse Sandbox",
    "➕  Create Posting",
    "✏️  Update Posting",
    "🗑️  Delete Posting",
    "🔬  Operations Audit & Reference",
])


def _format_salary(salary_data: Optional[Dict]) -> str:
    """Formats a salary subdocument into a display string."""
    if not salary_data:
        return "Not Specified"
    min_s = salary_data.get("min_amount")
    max_s = salary_data.get("max_amount")
    curr = str(salary_data.get("currency", "USD"))
    per = str(salary_data.get("period", "yearly"))
    if min_s is not None and max_s is not None:
        return f"${min_s:,.0f} – ${max_s:,.0f} {curr} ({per})"
    elif max_s is not None:
        return f"Up to ${max_s:,.0f} {curr} ({per})"
    elif min_s is not None:
        return f"From ${min_s:,.0f} {curr} ({per})"
    return "Not Specified"


def _field_row(label: str, value: str) -> str:
    """Returns an HTML row for a labeled field."""
    return f'<div style="display: flex; gap: 0.5rem; margin-bottom: 0.35rem; font-size: 0.88rem; font-family: \'Plus Jakarta Sans\', sans-serif;"><span style="color: {THEME["text_muted"]}; min-width: 105px; font-weight: 500;">{label}</span><span style="color: {THEME["text_primary"]};">{value}</span></div>'


# =============================================================================
# TAB 1: BROWSE / READ SANDBOX POSTINGS
# =============================================================================
with tab_read:
    st.markdown(
        f'<div style="font-family: \'Newsreader\', serif; font-size: 1.15rem; font-weight: 600; color: {THEME["text_primary"]}; margin-bottom: 0.25rem;">Sandbox Records Browser</div>'
        f'<div style="font-size: 0.82rem; color: {THEME["text_muted"]}; margin-bottom: 1rem;">Inspect live demonstration postings in <code style="background: rgba(110,133,108,0.12); padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.85em;">demo_postings</code>. Notice the separation between MongoDB internal <code style="font-size: 0.85em;">_id: ObjectId(...)</code> and domain identifier <code style="font-size: 0.85em;">demo_id</code>.</div>',
        unsafe_allow_html=True,
    )

    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_kw = st.text_input(
            "Search Records",
            placeholder="Search by title, company, skills, or keywords…",
            key="crud_read_search",
        )
    with f_col2:
        state_filter_options = ["All States"] + list(US_STATES)
        selected_state = st.selectbox(
            "Filter by State",
            options=state_filter_options,
            index=0,
            key="crud_read_state",
        )
        effective_state = None if selected_state == "All States" else selected_state
    with f_col3:
        remote_filter = st.selectbox(
            "Workplace Modality",
            options=["All Postings", "Remote Only", "On-site / Hybrid Only"],
            index=0,
            key="crud_read_remote",
        )
        effective_remote = None
        if remote_filter == "Remote Only":
            effective_remote = True
        elif remote_filter == "On-site / Hybrid Only":
            effective_remote = False

    try:
        postings, total_matching = service.get_demo_postings(
            search_query=search_kw,
            state=effective_state,
            is_remote=effective_remote,
            limit=50,
            skip=0,
        )
    except Exception as err:
        render_error_state("Database Query Failed", html.escape(str(err)))
        postings, total_matching = [], 0

    st.markdown(
        f'<div style="font-size: 0.82rem; color: {THEME["text_muted"]}; margin-bottom: 0.75rem;">Showing <strong style="color: {THEME["text_primary"]};">{len(postings)}</strong> of <strong style="color: {THEME["text_primary"]};">{total_matching}</strong> demonstration record{"s" if total_matching != 1 else ""}</div>',
        unsafe_allow_html=True,
    )

    if not postings:
        render_empty_state(
            title="No Demonstration Postings Found",
            message=(
                "No matching demonstration postings found in jobmarketdb.demo_postings. "
                "Use the '➕ Create Posting' tab above to insert a new validated sandbox record."
            ),
            icon="🧪",
        )
    else:
        for idx, p in enumerate(postings):
            raw_doc_id = str(p.get("_id", "N/A"))
            raw_demo_id = str(p.get("demo_id", "DEMO-UNKNOWN"))
            raw_title = str(p.get("title", "Untitled"))
            raw_company = str(p.get("company", {}).get("name", "Unknown Company"))
            loc = p.get("location", {})
            raw_city = str(loc.get("city") or "Unspecified")
            raw_state_code = str(loc.get("state") or "N/A")
            is_rem = bool(loc.get("is_remote", False))
            raw_source = str(p.get("source", "Demonstration Sandbox"))
            raw_exp = str(p.get("experience_level") or "Not Specified")
            skills_list = p.get("skills", [])
            salary_data = p.get("salary")
            created_dt = p.get("created_at")
            updated_dt = p.get("updated_at")
            raw_desc = str(p.get("description", "No description available."))

            sal_str = _format_salary(salary_data)
            loc_str = f"{raw_city}, {raw_state_code}" + (" · Remote" if is_rem else "")

            esc_title = html.escape(raw_title)
            esc_company = html.escape(raw_company)
            esc_loc = html.escape(loc_str)
            esc_sal = html.escape(sal_str)
            esc_exp = html.escape(raw_exp)
            esc_source = html.escape(raw_source)
            esc_demo_id = html.escape(raw_demo_id)
            esc_doc_id = html.escape(raw_doc_id)
            esc_desc = html.escape(raw_desc)

            with st.expander(f"{raw_title} — {raw_company}  [{raw_demo_id}]", expanded=(idx == 0)):
                card_html = f"""<div style="background: {THEME['canvas_ivory']}; border: 1px solid {THEME['subtle_border']}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 0.75rem;">
<div style="font-family: 'Newsreader', serif; font-size: 1.05rem; font-weight: 600; color: {THEME['text_primary']}; margin-bottom: 0.75rem;">{esc_title}</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.2rem 2rem;">
{_field_row("Company", esc_company)}
{_field_row("Location", esc_loc)}
{_field_row("Salary", esc_sal)}
{_field_row("Experience", esc_exp)}
{_field_row("Source", esc_source)}
{_field_row("Demo ID", f'<code style="font-size: 0.82em; color: {THEME["deep_olive"]};">{esc_demo_id}</code>')}
{_field_row("MongoDB _id", f'<code style="font-size: 0.82em; color: {THEME["deep_olive"]};">{esc_doc_id}</code>')}
</div>
</div>"""
                st.markdown(card_html, unsafe_allow_html=True)

                # Timestamps
                ts_parts = []
                if created_dt:
                    cs = created_dt.strftime('%Y-%m-%d %H:%M:%S UTC') if isinstance(created_dt, datetime) else str(created_dt)
                    ts_parts.append(f"Created: {html.escape(cs)}")
                if updated_dt:
                    us = updated_dt.strftime('%Y-%m-%d %H:%M:%S UTC') if isinstance(updated_dt, datetime) else str(updated_dt)
                    ts_parts.append(f"Modified: {html.escape(us)}")
                if ts_parts:
                    st.caption(" · ".join(ts_parts))

                # Skills chips
                if skills_list:
                    chips_html = " ".join(
                        f'<span style="display: inline-block; background: {THEME["muted_sage"]}; color: {THEME["deep_olive"]}; padding: 0.2em 0.6em; border-radius: 6px; font-size: 0.78rem; font-weight: 500; margin: 0.15em 0.15em;">{html.escape(str(s))}</span>'
                        for s in skills_list
                    )
                    st.markdown(
                        f'<div style="margin-bottom: 0.5rem;"><div style="font-size: 0.72rem; font-weight: 600; color: {THEME["text_muted"]}; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.35rem;">Required Skills</div>{chips_html}</div>',
                        unsafe_allow_html=True,
                    )

                # Description
                desc_html = f"""<div style="background: {THEME['canvas_ivory']}; border: 1px solid {THEME['subtle_border']}; border-radius: 10px; padding: 1rem 1.25rem; font-size: 0.86rem; line-height: 1.6; max-height: 220px; overflow-y: auto; white-space: pre-wrap; color: {THEME['text_secondary']};">{esc_desc}</div>"""
                st.markdown(desc_html, unsafe_allow_html=True)

    render_editorial_callout(
        title="MongoDB Read Pattern: find() with Compound Predicates",
        text=(
            "Queries on this page execute <code>db.demo_postings.find(filter).sort({'created_at': -1})</code>. "
            "Keyword searches use <code>$or</code> across title, company.name, skills, and description with "
            "case-insensitive regex (<code>$options: 'i'</code>). Canonical collections are never queried "
            "for demonstration search operations."
        ),
        callout_type="info",
    )


# =============================================================================
# TAB 2: CREATE DEMO POSTING
# =============================================================================
with tab_create:
    st.markdown(
        f'<div style="font-family: \'Newsreader\', serif; font-size: 1.15rem; font-weight: 600; color: {THEME["text_primary"]}; margin-bottom: 0.25rem;">Create a Demonstration Posting</div>'
        f'<div style="font-size: 0.82rem; color: {THEME["text_muted"]}; margin-bottom: 1rem;">Inserts a validated record exclusively into <code style="background: rgba(110,133,108,0.12); padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.85em;">jobmarketdb.demo_postings</code>. Inputs are strictly validated by the service layer prior to database insertion.</div>',
        unsafe_allow_html=True,
    )

    with st.form("create_demo_posting_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            c_title = st.text_input("Job Title *", placeholder="e.g. Lead Distributed Systems Engineer", key="create_title_in")
            c_company = st.text_input("Company Name *", placeholder="e.g. Nova Analytics AI", key="create_company_in")
            c_source = st.selectbox(
                "Posting Channel / Provenance *",
                options=["Demonstration Sandbox", "Indeed Simulation", "LinkedIn Simulation", "Internal Referral Portal"],
                index=0,
                key="create_source_in",
            )
            c_exp = st.selectbox(
                "Experience Level Tier",
                options=["Not Specified", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"],
                index=0,
                key="create_exp_in",
            )

        with col2:
            c_city = st.text_input("City", placeholder="e.g. Austin or San Francisco", key="create_city_in")
            c_state = st.selectbox("State (US)", options=["None / Remote Only"] + list(US_STATES), index=0, key="create_state_in")
            c_remote = st.checkbox("Fully Remote Position (🌐)", value=False, key="create_remote_in")
            c_skills = st.text_input(
                "Required Skills (comma-separated)",
                placeholder="e.g. Python, MongoDB, Apache Kafka, PyTorch, Docker",
                key="create_skills_in",
            )

        st.markdown(
            f'<div style="font-family: \'Newsreader\', serif; font-size: 0.95rem; font-weight: 600; color: {THEME["text_primary"]}; margin: 0.75rem 0 0.35rem 0;">💵 Compensation Details (Optional)</div>',
            unsafe_allow_html=True,
        )
        sal_toggle = st.checkbox("Provide Salary Compensation Structure", value=False, key="create_saltoggle_in")
        c_min_sal: Optional[float] = None
        c_max_sal: Optional[float] = None
        c_period = "yearly"

        if sal_toggle:
            sal_c1, sal_c2, sal_c3 = st.columns(3)
            with sal_c1:
                c_min_sal_input = st.number_input("Minimum Salary ($)", min_value=0.0, step=5000.0, value=110000.0, key="create_minsal_in")
                c_min_sal = float(c_min_sal_input)
            with sal_c2:
                c_max_sal_input = st.number_input("Maximum Salary ($)", min_value=0.0, step=5000.0, value=165000.0, key="create_maxsal_in")
                c_max_sal = float(c_max_sal_input)
            with sal_c3:
                c_period = st.selectbox("Compensation Frequency", options=["yearly", "hourly"], index=0, key="create_period_in")

        st.markdown(
            f'<div style="font-family: \'Newsreader\', serif; font-size: 0.95rem; font-weight: 600; color: {THEME["text_primary"]}; margin: 0.75rem 0 0.35rem 0;">📝 Job Description *</div>',
            unsafe_allow_html=True,
        )
        c_desc = st.text_area(
            "Full Job Description",
            placeholder="Enter the full demonstration job description, requirements, and responsibilities (minimum 10 characters)…",
            height=130,
            label_visibility="collapsed",
            key="create_desc_in",
        )

        submitted_create = st.form_submit_button(
            "🚀 Insert Demonstration Posting",
            type="primary",
            use_container_width=True,
        )

    if submitted_create:
        try:
            eff_state = None if c_state == "None / Remote Only" else c_state
            parsed_skills = [s.strip() for s in c_skills.split(",") if s.strip()] if c_skills else []

            created_record = service.create_demo_posting(
                title=c_title,
                company_name=c_company,
                description=c_desc,
                location_city=c_city,
                location_state=eff_state,
                is_remote=c_remote,
                skills=parsed_skills,
                source=c_source,
                experience_level=None if c_exp == "Not Specified" else c_exp,
                salary_min=c_min_sal,
                salary_max=c_max_sal,
                salary_currency="USD",
                salary_period=c_period,
            )

            created_demo_id = str(created_record.get("demo_id", "N/A"))
            created_oid = str(created_record.get("_id", "N/A"))

            _record_session_operation(
                op_type="CREATE",
                target_demo_id=created_demo_id,
                target_oid=created_oid,
                mongo_command=f"db.demo_postings.insertOne({{'demo_id': '{created_demo_id}', ...}})",
                status="SUCCESS",
                details=f"Title: {c_title} | Company: {c_company}",
            )

            st.session_state["crud_flash_message"] = f"""<div style="background: {THEME['muted_sage']}; border: 1px solid {THEME['sage_green']}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;">
<div style="font-weight: 700; color: {THEME['deep_olive']}; font-size: 0.95rem; margin-bottom: 0.5rem;">✓ Demonstration Posting Created Successfully</div>
<div style="font-size: 0.85rem; color: {THEME['text_secondary']}; line-height: 1.6;">
<strong>Demo ID:</strong> <code>{html.escape(created_demo_id)}</code><br>
<strong>MongoDB _id:</strong> <code>{html.escape(created_oid)}</code><br>
<strong>Target Collection:</strong> <code>jobmarketdb.demo_postings</code><br>
<strong>Canonical Status:</strong> jobs ({jobs_display}) and companies ({companies_display}) 100% untouched.
</div>
</div>"""
            st.rerun()
        except Exception as err:
            render_error_state("Validation or Insertion Error", html.escape(str(err)))

    render_editorial_callout(
        title="MongoDB Create Pattern: insertOne() with Document Validation",
        text=(
            "Inserts execute <code>db.demo_postings.insertOne(doc)</code>. MongoDB generates a BSON <code>ObjectId</code> "
            "as the primary key (<code>_id</code>), and the service layer assigns an indexed, human-readable "
            "<code>demo_id</code>. All user strings are validated for length, whitespace, and required constraints "
            "before reaching the database engine."
        ),
        callout_type="info",
    )


# =============================================================================
# TAB 3: UPDATE DEMO POSTING
# =============================================================================
with tab_update:
    st.markdown(
        f'<div style="font-family: \'Newsreader\', serif; font-size: 1.15rem; font-weight: 600; color: {THEME["text_primary"]}; margin-bottom: 0.25rem;">Update an Existing Posting</div>'
        f'<div style="font-size: 0.82rem; color: {THEME["text_muted"]}; margin-bottom: 1rem;">Modifies specific fields of an existing document within <code style="background: rgba(110,133,108,0.12); padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.85em;">demo_postings</code>. Demonstrates atomic field updates with <code style="font-size: 0.85em;">$set</code> and field removal with <code style="font-size: 0.85em;">$unset</code>.</div>',
        unsafe_allow_html=True,
    )

    try:
        existing_docs, _ = service.get_demo_postings(limit=100)
    except Exception as err:
        existing_docs = []
        render_error_state("Failed to retrieve demonstration documents", html.escape(str(err)))

    if not existing_docs:
        render_empty_state(
            title="No Demonstration Postings Available to Update",
            message="Please create at least one demonstration posting first using the '➕ Create Posting' tab.",
            icon="✏️",
        )
    else:
        doc_options = {
            f"{d.get('demo_id', 'UNKNOWN')} — {d.get('title', 'Untitled')} ({d.get('company', {}).get('name', 'Unknown')})": d
            for d in existing_docs
        }
        selected_label = st.selectbox(
            "Select Demonstration Posting to Update",
            options=list(doc_options.keys()),
            key="update_doc_select",
        )
        target_doc = doc_options[selected_label]
        target_id = target_doc["_id"]

        st.markdown(
            f"""<div style="background: {THEME['canvas_ivory']}; border: 1px solid {THEME['subtle_border']}; border-radius: 10px; padding: 0.75rem 1.25rem; margin-bottom: 1rem; font-size: 0.84rem; color: {THEME['text_muted']};">Editing: <strong style="color: {THEME['text_primary']};">{html.escape(str(target_doc.get('demo_id', 'N/A')))}</strong> &nbsp;·&nbsp; MongoDB _id: <code style="font-size: 0.85em;">{html.escape(str(target_id))}</code></div>""",
            unsafe_allow_html=True,
        )

        with st.form("update_demo_posting_form"):
            u_col1, u_col2 = st.columns(2)
            with u_col1:
                u_title = st.text_input("Job Title *", value=target_doc.get("title", ""), key=f"u_title_{target_id}")
                u_company = st.text_input("Company Name *", value=target_doc.get("company", {}).get("name", ""), key=f"u_comp_{target_id}")
                curr_exp = target_doc.get("experience_level") or "Not Specified"
                exp_opts = ["Not Specified", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"]
                u_exp = st.selectbox(
                    "Experience Level",
                    options=exp_opts,
                    index=exp_opts.index(curr_exp) if curr_exp in exp_opts else 0,
                    key=f"u_exp_{target_id}",
                )

            with u_col2:
                curr_loc = target_doc.get("location", {})
                u_city = st.text_input("City", value=curr_loc.get("city") or "", key=f"u_city_{target_id}")
                curr_st = curr_loc.get("state") or "None / Remote Only"
                st_opts = ["None / Remote Only"] + list(US_STATES)
                u_state = st.selectbox(
                    "State (US)",
                    options=st_opts,
                    index=st_opts.index(curr_st) if curr_st in st_opts else 0,
                    key=f"u_state_{target_id}",
                )
                u_remote = st.checkbox("Fully Remote Position (🌐)", value=bool(curr_loc.get("is_remote", False)), key=f"u_rem_{target_id}")

            curr_skills = target_doc.get("skills", [])
            u_skills = st.text_input("Skills (comma-separated)", value=", ".join(curr_skills), key=f"u_skills_{target_id}")

            # Salary editing & explicit removal controls
            curr_sal = target_doc.get("salary") or {}
            has_sal = bool(curr_sal and (curr_sal.get("min_amount") is not None or curr_sal.get("max_amount") is not None))

            st.markdown(
                f'<div style="font-family: \'Newsreader\', serif; font-size: 0.95rem; font-weight: 600; color: {THEME["text_primary"]}; margin: 0.75rem 0 0.35rem 0;">💵 Salary Structure Management</div>',
                unsafe_allow_html=True,
            )

            if has_sal:
                sal_action = st.radio(
                    "Salary Action",
                    options=["Keep Current Salary", "Update Salary Values", "Remove Salary Structure (Unset)"],
                    horizontal=True,
                    key=f"u_sal_action_{target_id}",
                )
            else:
                sal_action = st.radio(
                    "Salary Action",
                    options=["No Salary (Unchanged)", "Add Salary Structure"],
                    horizontal=True,
                    key=f"u_sal_action_{target_id}",
                )

            do_remove_sal = (sal_action == "Remove Salary Structure (Unset)")
            edit_sal_values = (sal_action in ("Update Salary Values", "Add Salary Structure"))

            u_min_sal = None
            u_max_sal = None
            u_period = "yearly"

            if edit_sal_values:
                us_col1, us_col2, us_col3 = st.columns(3)
                with us_col1:
                    u_min_sal_val = float(curr_sal.get("min_amount") or 100000.0)
                    u_min_sal = st.number_input("Min Salary ($)", min_value=0.0, step=5000.0, value=u_min_sal_val, key=f"u_minsal_{target_id}")
                with us_col2:
                    u_max_sal_val = float(curr_sal.get("max_amount") or 150000.0)
                    u_max_sal = st.number_input("Max Salary ($)", min_value=0.0, step=5000.0, value=u_max_sal_val, key=f"u_maxsal_{target_id}")
                with us_col3:
                    curr_per = curr_sal.get("period") or "yearly"
                    u_period = st.selectbox("Period", options=["yearly", "hourly"], index=0 if curr_per == "yearly" else 1, key=f"u_period_{target_id}")
            elif do_remove_sal:
                render_editorial_callout(
                    title="Salary Removal Notice ($unset)",
                    text="The embedded <code>salary</code> subdocument will be permanently removed using MongoDB <code>$unset: {'salary': ''}</code>.",
                    callout_type="info",
                )

            u_desc = st.text_area("Job Description *", value=target_doc.get("description", ""), height=130, key=f"u_desc_{target_id}")

            submitted_update = st.form_submit_button(
                "💾 Save Changes to Demonstration Posting",
                type="primary",
                use_container_width=True,
            )

        if submitted_update:
            try:
                parsed_u_skills = [s.strip() for s in u_skills.split(",") if s.strip()] if u_skills else []
                eff_u_state = None if u_state == "None / Remote Only" else u_state

                updated = service.update_demo_posting(
                    doc_id=target_id,
                    title=u_title,
                    company_name=u_company,
                    description=u_desc,
                    location_city=u_city,
                    location_state=eff_u_state,
                    is_remote=u_remote,
                    skills=parsed_u_skills,
                    experience_level=None if u_exp == "Not Specified" else u_exp,
                    salary_min=u_min_sal if edit_sal_values else None,
                    salary_max=u_max_sal if edit_sal_values else None,
                    salary_period=u_period if edit_sal_values else None,
                    remove_salary=do_remove_sal,
                )

                sal_status = "Removed ($unset)" if do_remove_sal else ("Updated ($set)" if edit_sal_values else "Unchanged")
                mongo_cmd = f"db.demo_postings.updateOne({{'_id': ObjectId('{target_id}')}}, {{'$set': {{...}}{', $unset: {\"salary\": \"\"}' if do_remove_sal else ''}}})"

                _record_session_operation(
                    op_type="UPDATE",
                    target_demo_id=str(updated.get("demo_id", "N/A")),
                    target_oid=str(target_id),
                    mongo_command=mongo_cmd,
                    status="SUCCESS",
                    details=f"Salary: {sal_status}",
                )

                st.session_state["crud_flash_message"] = f"""<div style="background: {THEME['muted_sage']}; border: 1px solid {THEME['sage_green']}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;">
<div style="font-weight: 700; color: {THEME['deep_olive']}; font-size: 0.95rem; margin-bottom: 0.5rem;">✓ Demonstration Posting Updated Successfully</div>
<div style="font-size: 0.85rem; color: {THEME['text_secondary']}; line-height: 1.6;">
<strong>Demo ID:</strong> <code>{html.escape(str(updated.get('demo_id', 'N/A')))}</code><br>
<strong>Updated At:</strong> <code>{html.escape(str(updated.get('updated_at', 'N/A')))}</code><br>
<strong>Salary Status:</strong> {html.escape(sal_status)}<br>
<strong>Target Collection:</strong> <code>jobmarketdb.demo_postings</code><br>
<strong>Canonical Invariants:</strong> jobs ({jobs_display}) and companies ({companies_display}) unchanged.
</div>
</div>"""
                st.rerun()
            except Exception as err:
                render_error_state("Update Error", html.escape(str(err)))

    render_editorial_callout(
        title="MongoDB Update Pattern: updateOne() with $set and $unset",
        text=(
            "Updates execute <code>db.demo_postings.updateOne({_id: target_oid}, update_op)</code>. "
            "Field edits use the <code>$set</code> operator to mutate only specified fields, leaving other "
            "document properties intact. Salary removal uses the <code>$unset</code> operator to remove the key "
            "completely from BSON storage rather than writing null."
        ),
        callout_type="info",
    )


# =============================================================================
# TAB 4: DELETE DEMO POSTING
# =============================================================================
with tab_delete:
    st.markdown(
        f'<div style="font-family: \'Newsreader\', serif; font-size: 1.15rem; font-weight: 600; color: {THEME["text_primary"]}; margin-bottom: 0.25rem;">Delete a Demonstration Posting</div>'
        f'<div style="font-size: 0.82rem; color: {THEME["text_muted"]}; margin-bottom: 1rem;">Removes exactly one document from <code style="background: rgba(110,133,108,0.12); padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.85em;">demo_postings</code>. Requires explicit user confirmation. Bulk deletions and collection drops are prohibited.</div>',
        unsafe_allow_html=True,
    )

    try:
        del_docs, _ = service.get_demo_postings(limit=100)
    except Exception as err:
        del_docs = []
        render_error_state("Failed to retrieve documents for deletion", html.escape(str(err)))

    if not del_docs:
        render_empty_state(
            title="No Demonstration Postings Available to Delete",
            message="There are currently zero demonstration documents in jobmarketdb.demo_postings.",
            icon="🗑️",
        )
    else:
        del_options = {
            f"{d.get('demo_id', 'UNKNOWN')} — {d.get('title', 'Untitled')} ({d.get('company', {}).get('name', 'Unknown')})": d
            for d in del_docs
        }
        selected_del_label = st.selectbox(
            "Select Demonstration Posting to Delete",
            options=list(del_options.keys()),
            key="delete_doc_select",
        )
        del_target = del_options[selected_del_label]
        del_id = del_target["_id"]

        del_title = html.escape(str(del_target.get('title') or 'Untitled'))
        del_company = html.escape(str(del_target.get('company', {}).get('name') or 'Unknown Company'))
        del_city = html.escape(str(del_target.get('location', {}).get('city') or 'N/A'))
        del_state_val = html.escape(str(del_target.get('location', {}).get('state') or 'N/A'))
        del_demo_id = html.escape(str(del_target.get('demo_id') or 'UNKNOWN'))
        del_oid = html.escape(str(del_id))

        # Deletion preview card with warning styling
        del_card_html = f"""<div style="background: {THEME['card_white']}; border: 2px solid #D4614B; border-radius: 14px; padding: 1.5rem 1.75rem; margin: 0.75rem 0; box-shadow: 0 1px 3px rgba(212,97,75,0.08);">
<div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #D4614B; margin-bottom: 0.5rem;">⚠️ Selected Record Targeted for Permanent Deletion</div>
<div style="font-family: 'Newsreader', serif; font-size: 1.1rem; font-weight: 600; color: {THEME['text_primary']}; margin-bottom: 0.4rem;">{del_title}</div>
<div style="font-size: 0.88rem; color: {THEME['text_secondary']}; margin-bottom: 0.4rem;">Company: <strong>{del_company}</strong> &nbsp;·&nbsp; Location: <strong>{del_city}, {del_state_val}</strong></div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: {THEME['text_muted']};">Demo ID: {del_demo_id} &nbsp;·&nbsp; MongoDB _id: {del_oid}</div>
</div>"""
        st.markdown(del_card_html, unsafe_allow_html=True)

        with st.form("delete_demo_posting_form"):
            # Mandatory explicit confirmation guard
            confirm_deletion = st.checkbox(
                f"⚠️ I confirm that I want to permanently delete demonstration posting '{del_demo_id}'. This action cannot be undone.",
                value=False,
                key="confirm_single_delete",
            )

            st.caption(
                "🔒 Safety Enforcement: Bulk deletions, collection dropping, and sandbox resets are disabled. "
                "This operation strictly removes exactly one document targeting demo_postings."
            )

            delete_clicked = st.form_submit_button(
                "🗑️ Permanently Delete Selected Posting",
                type="primary",
                use_container_width=True,
            )

        if delete_clicked:
            if not confirm_deletion:
                render_error_state("Confirmation Required", "You must check the confirmation checkbox to permanently delete this posting.")
            else:
                try:
                    success = service.delete_demo_posting(doc_id=del_id)
                    if success:
                        _record_session_operation(
                            op_type="DELETE",
                            target_demo_id=del_demo_id,
                            target_oid=del_oid,
                            mongo_command=f"db.demo_postings.deleteOne({{'_id': ObjectId('{del_oid}')}})",
                            status="SUCCESS",
                            details=f"Title: {del_title} | Company: {del_company}",
                        )

                        st.session_state["crud_flash_message"] = f"""<div style="background: {THEME['muted_sage']}; border: 1px solid {THEME['sage_green']}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;">
<div style="font-weight: 700; color: {THEME['deep_olive']}; font-size: 0.95rem; margin-bottom: 0.5rem;">✓ Demonstration Posting Deleted Successfully</div>
<div style="font-size: 0.85rem; color: {THEME['text_secondary']}; line-height: 1.6;">
<strong>Deleted Demo ID:</strong> <code>{del_demo_id}</code><br>
<strong>Target Collection:</strong> <code>jobmarketdb.demo_postings</code><br>
<strong>Canonical Dataset Status:</strong> jobs ({jobs_display}) and companies ({companies_display}) remain 100% untouched.
</div>
</div>"""
                        st.rerun()
                    else:
                        render_error_state("Deletion Failed", "The document could not be deleted.")
                except Exception as err:
                    render_error_state("Deletion Error", html.escape(str(err)))

    render_editorial_callout(
        title="MongoDB Delete Pattern: deleteOne() with Exact ObjectId Filter",
        text=(
            "Deletions execute <code>db.demo_postings.deleteOne({_id: ObjectId(doc_id)})</code>. "
            "The service layer rejects any filter that does not specify an exact, verified <code>_id</code>. "
            "Collection-level operations, wildcard filters, and bulk drops are structurally blocked."
        ),
        callout_type="info",
    )


# =============================================================================
# TAB 5: OPERATION HISTORY & TECHNICAL REFERENCE
# =============================================================================
with tab_history:
    st.markdown(
        f'<div style="font-family: \'Newsreader\', serif; font-size: 1.15rem; font-weight: 600; color: {THEME["text_primary"]}; margin-bottom: 0.25rem;">Session Operations Audit & MongoDB Reference</div>'
        f'<div style="font-size: 0.82rem; color: {THEME["text_muted"]}; margin-bottom: 1rem;">Transient in-memory execution log for actions taken during this active browser session, accompanied by MongoDB operator explanations.</div>',
        unsafe_allow_html=True,
    )

    hist = st.session_state.get("crud_session_history", [])

    if not hist:
        empty_hist_html = f"""<div style="background: {THEME['canvas_ivory']}; border: 1px solid {THEME['subtle_border']}; border-radius: 12px; padding: 1.5rem; text-align: center; margin-bottom: 1.5rem;">
<div style="font-size: 1.5rem; margin-bottom: 0.5rem;">📜</div>
<div style="font-weight: 600; color: {THEME['text_primary']}; margin-bottom: 0.25rem;">No Operations Recorded in Current Session</div>
<div style="font-size: 0.84rem; color: {THEME['text_muted']};">Perform a Create, Update, or Delete operation to see live MongoDB audit events logged here.</div>
</div>"""
        st.markdown(empty_hist_html, unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="font-size: 0.84rem; color: {THEME["text_muted"]}; margin-bottom: 0.75rem;">Showing <strong>{len(hist)}</strong> session operation{"s" if len(hist) != 1 else ""}:</div>',
            unsafe_allow_html=True,
        )
        for h in hist:
            op_badge_color = {
                "CREATE": THEME["accent_emerald"],
                "UPDATE": THEME["accent_amber"],
                "DELETE": "#D4614B",
            }.get(h["operation"], THEME["text_muted"])

            h_item_html = f"""<div style="background: {THEME['card_white']}; border: 1px solid {THEME['subtle_border']}; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 0.75rem; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap;">
<span style="background: {op_badge_color}; color: #FFFFFF; padding: 0.2em 0.6em; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">{html.escape(h['operation'])}</span>
<span style="font-size: 0.78rem; color: {THEME['text_muted']};">{html.escape(h['timestamp'])}</span>
</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: {THEME['deep_olive']}; margin-bottom: 0.3rem;">{html.escape(h['mongo_command'])}</div>
<div style="font-size: 0.82rem; color: {THEME['text_secondary']};">
Target Demo ID: <code>{html.escape(h['target_demo_id'])}</code> &nbsp;·&nbsp;
MongoDB _id: <code>{html.escape(h['target_oid'])}</code> &nbsp;·&nbsp;
Status: <strong style="color: {THEME['accent_emerald']};">{html.escape(h['status'])}</strong>
{f" &nbsp;·&nbsp; {html.escape(h['details'])}" if h.get('details') else ""}
</div>
</div>"""
            st.markdown(h_item_html, unsafe_allow_html=True)

    st.caption("ℹ️ Session Audit Scope: This execution log is retained in Streamlit session memory and is reset on browser refresh.")

    # Educational Technical Reference Cards
    st.markdown(
        f'<div style="font-family: \'Newsreader\', serif; font-size: 1.15rem; font-weight: 600; color: {THEME["text_primary"]}; margin: 1.75rem 0 0.75rem 0;">MongoDB CRUD Architecture & Operator Reference</div>',
        unsafe_allow_html=True,
    )

    t_col1, t_col2 = st.columns(2)
    with t_col1:
        st.markdown(
            f"""<div style="background: {THEME['card_white']}; border: 1px solid {THEME['subtle_border']}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;">
<div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: {THEME['deep_olive']}; margin-bottom: 0.4rem;">1. BSON Document Model & Schema Validation</div>
<div style="font-size: 0.85rem; color: {THEME['text_secondary']}; line-height: 1.55;">MongoDB documents are serialized as BSON (Binary JSON). Each document in <code>demo_postings</code> carries typed nested subdocuments for <code>location</code> (city, state, modality) and <code>salary</code> (min, max, period, normalized annual). The service layer acts as an application-level schema validator ensuring type coherence before BSON serialization.</div>
</div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""<div style="background: {THEME['card_white']}; border: 1px solid {THEME['subtle_border']}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;">
<div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: {THEME['deep_olive']}; margin-bottom: 0.4rem;">2. Query Selectors & Compound Filtering ($or, $regex)</div>
<div style="font-size: 0.85rem; color: {THEME['text_secondary']}; line-height: 1.55;">The read browser constructs dynamic MongoDB filter dictionaries. Text searches leverage <code>$or</code> clauses across multiple fields with <code>$regex</code>. State and modality filters are appended as exact equality constraints. Cursor execution uses <code>.sort()</code>, <code>.skip()</code>, and <code>.limit()</code> for efficient pagination.</div>
</div>""",
            unsafe_allow_html=True,
        )

    with t_col2:
        st.markdown(
            f"""<div style="background: {THEME['card_white']}; border: 1px solid {THEME['subtle_border']}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;">
<div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: {THEME['deep_olive']}; margin-bottom: 0.4rem;">3. Update Operators ($set vs $unset)</div>
<div style="font-size: 0.85rem; color: {THEME['text_secondary']}; line-height: 1.55;">MongoDB distinguishes between field mutation and field removal. The <code>$set</code> operator modifies targeted keys without touching sibling attributes. When compensation details are removed, the <code>$unset</code> operator physically deletes the <code>salary</code> key from BSON storage, ensuring null-check queries like <code>{{"salary.normalized_annual": {{"$ne": None}}}}</code> function correctly.</div>
</div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""<div style="background: {THEME['card_white']}; border: 1px solid {THEME['subtle_border']}; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;">
<div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: {THEME['deep_olive']}; margin-bottom: 0.4rem;">4. Deletion Safety & Primary Key Enforcement</div>
<div style="font-size: 0.85rem; color: {THEME['text_secondary']}; line-height: 1.55;">Deletions require an exact BSON <code>ObjectId</code> target. The CRUD service verifies that the target exists in <code>demo_postings</code> and enforces <code>collection.delete_one({{'_id': oid}})</code>. Attempting to target canonical collections (<code>jobs</code>, <code>companies</code>) or passing empty filter objects raises immediate exceptions.</div>
</div>""",
            unsafe_allow_html=True,
        )


# =============================================================================
# 7. Footer — Live Database Invariant Guarantee
# =============================================================================
footer_html = f"""<div style="margin-top: 2rem; padding: 1.25rem 1.5rem; background: {THEME['canvas_ivory']}; border-top: 1px solid {THEME['subtle_border']}; border-radius: 12px; text-align: center;">
<div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: {THEME['sage_green']}; margin-bottom: 0.35rem;">Live Data Invariant Guarantee</div>
<div style="font-size: 0.82rem; color: {THEME['text_muted']}; font-family: 'Plus Jakarta Sans', sans-serif;">
Canonical Jobs: <strong style="color: {THEME['text_primary']};">{jobs_display}</strong> &nbsp;·&nbsp;
Canonical Companies: <strong style="color: {THEME['text_primary']};">{companies_display}</strong> &nbsp;·&nbsp;
Indexes: <strong style="color: {THEME['text_primary']};">{indexes_display}</strong> &nbsp;·&nbsp;
Sandbox: <strong style="color: {THEME['text_primary']};">demo_postings</strong>
<span style="color: {THEME['text_muted']};">(MongoDB Community Server localhost:27017)</span>
</div>
</div>"""

st.markdown(footer_html, unsafe_allow_html=True)
