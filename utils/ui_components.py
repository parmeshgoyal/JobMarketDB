"""
JobMarketDB — Reusable UI Components & Layout Utilities (Phase 7 Editorial SaaS)

Provides modular, high-contrast, theme-consistent UI components for Streamlit pages:
- CSS injector (load_custom_css)
- Header & section banners (render_header, EditorialHeader, render_editorial_header)
- Metric KPI cards (render_metric_card, EditorialStatCard, render_editorial_stat_card)
- Platform badges (render_platform_badge)
- State & geography selectors (render_state_selector)
- Reusable pagination controls (render_pagination_controls)
- Empty, loading, and error states (render_empty_state, render_loading_state, render_error_state)
- Provenance & methodology callouts (render_callout, EditorialCallout, render_editorial_callout)
- Active filter bar (EditorialFilterBar, render_editorial_filter_bar)
- Elevated job card renderer (ElevatedJobCard, render_elevated_job_card)

All dynamic user-controlled strings are safely escaped before HTML insertion.
"""

import html
import os
from typing import Any, Dict, List, Optional, Tuple, Union
import streamlit as st

US_STATES: Tuple[str, ...] = (
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
)


def load_custom_css() -> None:
    """Injects the unified JobMarketDB editorial CSS stylesheet into the active Streamlit page."""
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        except Exception:
            pass


def render_header(
    title: str,
    subtitle: Optional[str] = None,
    badge_text: Optional[str] = None,
) -> None:
    """
    Renders a unified page header with title, optional badge, and descriptive subtitle.
    Maintains backward compatibility with all Phase 6 callers.
    """
    safe_title = html.escape(str(title))
    badge_html = (
        f'<span class="jmdb-badge jmdb-badge-pill">{html.escape(str(badge_text))}</span>'
        if badge_text
        else ""
    )
    sub_html = (
        f'<p class="jmdb-header-subtitle">{html.escape(str(subtitle))}</p>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div class="jmdb-header-container">
            <h1 class="jmdb-header-title">
                {safe_title} {badge_html}
            </h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_editorial_header(
    title: str,
    subtitle: Optional[str] = None,
    eyebrow: Optional[str] = None,
    badge_text: Optional[str] = None,
    status_text: Optional[str] = None,
) -> None:
    """
    Renders an elevated editorial header featuring an eyebrow category tag,
    editorial serif title, optional status pill, and subtitle.
    """
    safe_title = html.escape(str(title))
    eyebrow_html = (
        f'<div class="jmdb-editorial-eyebrow">{html.escape(str(eyebrow))}</div>'
        if eyebrow
        else ""
    )
    badge_html = (
        f'<span class="jmdb-badge jmdb-badge-pill">{html.escape(str(badge_text))}</span>'
        if badge_text
        else ""
    )
    status_html = (
        f'<span class="jmdb-badge jmdb-badge-neutral" style="margin-left: 0.5rem;">{html.escape(str(status_text))}</span>'
        if status_text
        else ""
    )
    sub_html = (
        f'<p class="jmdb-editorial-subtitle">{html.escape(str(subtitle))}</p>'
        if subtitle
        else ""
    )

    st.markdown(
        f"""
        <div class="jmdb-editorial-header">
            {eyebrow_html}
            <h1 class="jmdb-editorial-title">
                {safe_title} {badge_html}{status_html}
            </h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# Alias for class-style component invocation
EditorialHeader = render_editorial_header


def render_metric_card(
    title: str,
    value: Any,
    subtitle: Optional[str] = None,
    delta: Optional[str] = None,
    delta_color: str = "normal",
) -> None:
    """
    Renders a styled metric KPI card with border, bold tabular value, and subtitle.
    Handles empty, zero, or missing values cleanly with safe HTML escaping.
    """
    display_value = "N/A" if value is None else str(value)
    safe_title = html.escape(str(title))
    safe_value = html.escape(display_value)

    delta_class = (
        "jmdb-metric-delta-positive"
        if delta_color in ("normal", "positive", "success")
        else "jmdb-metric-delta-neutral"
    )
    delta_html = (
        f' <span class="{delta_class}">({html.escape(str(delta))})</span>'
        if delta
        else ""
    )
    sub_html = (
        f'<p class="jmdb-metric-subtitle">{html.escape(str(subtitle))}{delta_html}</p>'
        if (subtitle or delta)
        else ""
    )

    st.markdown(
        f"""
        <div class="jmdb-metric-card">
            <div class="jmdb-metric-title">{safe_title}</div>
            <div class="jmdb-metric-value">{safe_value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_editorial_stat_card(
    title: str,
    value: Any,
    subtitle: Optional[str] = None,
    delta: Optional[str] = None,
    delta_type: str = "positive",
) -> None:
    """
    Renders an elevated Phase 7 Editorial KPI Stat Card with warm ivory/card styling.
    """
    render_metric_card(
        title=title,
        value=value,
        subtitle=subtitle,
        delta=delta,
        delta_color=delta_type,
    )


EditorialStatCard = render_editorial_stat_card


def render_platform_badge(source: Optional[str]) -> str:
    """
    Returns an HTML badge string with authentic brand coloration for LinkedIn, Indeed, or Combined.
    Safe for empty or None inputs.
    """
    if not source:
        return '<span class="jmdb-badge jmdb-badge-neutral">Unknown</span>'

    clean_source = str(source).strip().lower()
    if clean_source == "linkedin":
        return '<span class="jmdb-badge jmdb-badge-linkedin">LinkedIn</span>'
    elif clean_source == "indeed":
        return '<span class="jmdb-badge jmdb-badge-indeed">Indeed</span>'
    elif clean_source in ("combined", "all", "cross-platform"):
        return '<span class="jmdb-badge jmdb-badge-neutral">Cross-Platform</span>'
    else:
        return f'<span class="jmdb-badge jmdb-badge-neutral">{html.escape(str(source))}</span>'


def render_state_selector(
    label: str = "Filter by US State",
    key: str = "state_selector",
    default: str = "All States",
    include_all_option: bool = True,
) -> Optional[str]:
    """
    Renders a standardized dropdown for selecting US states.
    Returns None if 'All States' is selected, or the 2-letter state code.
    """
    options = list(US_STATES)
    if include_all_option:
        options = ["All States"] + options

    default_index = options.index(default) if default in options else 0
    selected = st.selectbox(label, options=options, index=default_index, key=key)

    if selected == "All States":
        return None
    return selected


def render_pagination_controls(
    current_page: int,
    total_pages: int,
    total_items: int,
    items_per_page: int = 20,
    key_prefix: str = "pagination",
) -> int:
    """
    Renders pagination navigation buttons and info.
    Returns the updated active page number (1-indexed).
    """
    if total_pages <= 1:
        st.markdown(
            f"""
            <div class="jmdb-pagination-container">
                <span class="jmdb-pagination-info">Showing {total_items:,} result{'s' if total_items != 1 else ''}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return 1

    col1, col2, col3 = st.columns([1, 2, 1])

    start_idx = ((current_page - 1) * items_per_page) + 1
    end_idx = min(current_page * items_per_page, total_items)

    with col1:
        prev_clicked = st.button("← Previous", disabled=(current_page <= 1), key=f"{key_prefix}_prev")
    with col2:
        st.markdown(
            f"<div style='text-align: center; padding-top: 6px; font-size: 0.88rem; color: #4A524D;'>"
            f"Page <b>{current_page}</b> of <b>{total_pages}</b> ({start_idx:,}–{end_idx:,} of {total_items:,})"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col3:
        next_clicked = st.button("Next →", disabled=(current_page >= total_pages), key=f"{key_prefix}_next")

    if prev_clicked and current_page > 1:
        return current_page - 1
    if next_clicked and current_page < total_pages:
        return current_page + 1
    return current_page


def render_empty_state(
    title: str = "No Postings Found",
    message: str = "Try expanding your search criteria, clearing specific filters, or checking keyword spelling.",
    icon: str = "🔍",
) -> None:
    """
    Renders an elegant empty state container with icon and helpful message.
    """
    safe_title = html.escape(str(title))
    safe_msg = html.escape(str(message))
    st.markdown(
        f"""
        <div class="jmdb-empty-state">
            <span class="jmdb-empty-icon">{icon}</span>
            <div class="jmdb-empty-title">{safe_title}</div>
            <div class="jmdb-empty-message">{safe_msg}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_loading_state(message: str = "Querying MongoDB...") -> None:
    """Renders a standard loading state spinner placeholder."""
    st.info(f"⏳ {html.escape(str(message))}")


def render_error_state(title: str = "Error Encountered", message: str = "") -> None:
    """Renders an error callout box with description."""
    safe_title = html.escape(str(title))
    safe_msg = html.escape(str(message))
    st.error(f"**{safe_title}**: {safe_msg}" if safe_msg else f"**{safe_title}**")


def render_callout(
    title: str,
    text: str,
    callout_type: str = "info",
) -> None:
    """
    Renders a styled informational or warning banner for methodology notes or taxonomy disclosures.
    callout_type: 'info' or 'warning'
    Safely permits intentional inline markup like <b>, <strong>, <code> while styling cleanly.
    """
    type_class = "jmdb-callout-warning" if callout_type == "warning" else "jmdb-callout-info"
    # Title is strictly escaped
    safe_title = html.escape(str(title))

    st.markdown(
        f"""
        <div class="jmdb-callout {type_class}">
            <div class="jmdb-callout-title">{safe_title}</div>
            <p class="jmdb-callout-text">{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_editorial_callout(
    title: str,
    text: str,
    callout_type: str = "info",
    eyebrow: Optional[str] = None,
) -> None:
    """
    Phase 7 elevated editorial callout with optional category eyebrow.
    """
    type_class = "jmdb-callout-warning" if callout_type == "warning" else "jmdb-callout-info"
    eyebrow_html = (
        f'<div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #6E856C; margin-bottom: 0.2rem;">{html.escape(str(eyebrow))}</div>'
        if eyebrow
        else ""
    )
    safe_title = html.escape(str(title))

    st.markdown(
        f"""
        <div class="jmdb-callout {type_class}">
            {eyebrow_html}
            <div class="jmdb-callout-title">{safe_title}</div>
            <p class="jmdb-callout-text">{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


EditorialCallout = render_editorial_callout


def render_editorial_filter_bar(
    active_filters: List[Dict[str, str]],
    title: str = "Active Filters",
) -> None:
    """
    Renders an editorial active filter bar showing filter label/value pills.
    active_filters: list of dicts with {"label": "...", "value": "..."}
    """
    if not active_filters:
        return

    pills_html = []
    for f in active_filters:
        lbl = html.escape(str(f.get("label", "")))
        val = html.escape(str(f.get("value", "")))
        pills_html.append(
            f'<span class="jmdb-editorial-filter-pill"><b>{lbl}:</b> {val}</span>'
        )

    all_pills = "".join(pills_html)
    safe_title = html.escape(str(title))
    st.markdown(
        f"""
        <div class="jmdb-editorial-filter-bar">
            <span style="font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #4A524D; margin-right: 0.35rem;">{safe_title}:</span>
            {all_pills}
        </div>
        """,
        unsafe_allow_html=True,
    )


EditorialFilterBar = render_editorial_filter_bar


def render_elevated_job_card(
    job: Dict[str, Any],
    selected_skills: Optional[List[str]] = None,
) -> str:
    """
    Generates HTML markup for an elevated editorial job card with clean typography,
    distinct salary presentation, and highlighted skill chips.
    Safe for direct inclusion in Streamlit markdown.
    """
    j_title = html.escape(str(job.get("title") or "Untitled Position"))
    j_source = str(job.get("source") or "unknown").lower()
    j_comp = html.escape(str((job.get("company") or {}).get("name") or "Company Unstated"))
    
    city = (job.get("location") or {}).get("city")
    state = (job.get("location") or {}).get("state")
    loc_str = f"{city}, {state}" if (city and state) else (state or city or (job.get("location") or {}).get("raw") or "US")
    j_loc = html.escape(str(loc_str))

    is_remote = (job.get("location") or {}).get("is_remote")
    if is_remote is True:
        r_badge = '<span class="jmdb-meta-badge jmdb-meta-badge-remote">Remote</span>'
    elif is_remote is False:
        r_badge = '<span class="jmdb-meta-badge jmdb-meta-badge-onsite">Explicitly On-Site</span>'
    else:
        r_badge = '<span class="jmdb-meta-badge jmdb-meta-badge-unspecified">Not Specified</span>'

    p_badge = render_platform_badge(j_source)

    # Salary formatting
    s_info = job.get("salary") or {}
    norm = s_info.get("normalized_annual")
    bucket = s_info.get("salary_bucket")
    if norm is not None:
        sal_badge = f'<span class="jmdb-meta-badge jmdb-meta-badge-salary">${norm:,.0f} / yr</span>'
    elif bucket:
        sal_badge = f'<span class="jmdb-meta-badge jmdb-meta-badge-salary">{html.escape(str(bucket))}</span>'
    else:
        sal_badge = '<span class="jmdb-meta-badge">Salary Unstated</span>'

    # Skills chips
    all_skills = [str(s) for s in (job.get("skills") or [])]
    sel_set = set(selected_skills or [])
    chips = []
    for s in all_skills[:8]:
        safe_s = html.escape(s)
        if s in sel_set:
            chips.append(f'<span class="jmdb-skill-chip jmdb-skill-chip-matched">{safe_s}</span>')
        else:
            chips.append(f'<span class="jmdb-skill-chip">{safe_s}</span>')
    if len(all_skills) > 8:
        chips.append(f'<span class="jmdb-skill-chip">+{len(all_skills)-8} more</span>')
    chips_html = "".join(chips)

    return f"""
    <div class="jmdb-job-card">
        <div class="jmdb-job-header">
            <div>
                <h3 class="jmdb-job-title">{j_title}</h3>
                <div class="jmdb-job-company">🏢 <b>{j_comp}</b> &nbsp;•&nbsp; 📍 {j_loc}</div>
            </div>
            <div style="display: flex; gap: 0.4rem; align-items: center;">{p_badge}{r_badge}</div>
        </div>
        <div class="jmdb-job-meta-row">{sal_badge}</div>
        <div class="jmdb-skill-container">{chips_html}</div>
    </div>
    """


ElevatedJobCard = render_elevated_job_card
