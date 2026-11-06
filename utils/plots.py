"""
JobMarketDB — Reusable Plotly Visualization Builders (Phase 7 Editorial SaaS)

Provides modular, audit-safe chart-building functions for Phase 5 aggregation outputs:
- Standard editorial Plotly styling (warm ivory canvas, white surface, charcoal text)
- Refined deep olive, sage green, and earthy accent tones
- Horizontal ranking charts (top skills, top companies, top locations)
- Salary distribution bucket visualizations
- Skills demand charts with platform taxonomy distinctions
- Geographic comparisons & US State choropleth visualizations
- Platform comparison visualizations (LinkedIn vs Indeed)

All builders accept raw data from the analytics/service layer, handle empty or None
inputs gracefully without raising unhandled exceptions, and strictly preserve input immutability.
"""

from typing import Any, Dict, List, Optional, Union
import plotly.graph_objects as go
import plotly.express as px

# Consistent Editorial Theme Palette
THEME: Dict[str, str] = {
    # Surface & Text Tokens
    "bg_paper": "#FFFFFF",                 # Pure White Card Surface
    "bg_plot": "#FAF8F5",                  # Warm Ivory Plot Canvas
    "canvas_ivory": "#FAF8F5",             # Warm Ivory Background
    "card_white": "#FFFFFF",               # White Card Surface
    "surface_warm": "#F5F2EB",             # Warm Secondary Surface
    "text_primary": "#1C1F1D",             # Deep Charcoal
    "text_secondary": "#4A524D",           # Refined Muted Charcoal
    "text_muted": "#737D76",               # Soft Slate
    "grid_color": "#E8EDE7",               # Muted Sage Hairline Grid
    "subtle_border": "#E2DDD5",            # Warm Subtle Border

    # Brand & Accent Tokens
    "deep_olive": "#2E3A2D",               # Primary Deep Olive
    "sage_green": "#6E856C",               # Primary Sage Green
    "muted_sage": "#E8EDE7",               # Soft Muted Sage
    "accent_blue": "#2E3A2D",              # Primary Accent (Deep Olive)
    "accent_olive": "#2E3A2D",             # Deep Olive Accent
    "accent_sage": "#6E856C",              # Sage Green Accent
    "accent_emerald": "#5A8257",           # Earthy Sage / Success
    "accent_amber": "#C2884E",             # Warm Terracotta / Amber
    "accent_purple": "#7A6F8A",            # Refined Slate Purple
    "accent_slate": "#516574",             # Restrained Slate Navy

    # Authentic Platform Branding
    "linkedin_blue": "#0A66C2",            # Authentic LinkedIn Blue
    "indeed_blue": "#2164F3",              # Authentic Indeed Blue

    # Typography
    "font_family": "'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
}


def apply_theme(fig: go.Figure, title: Optional[str] = None, height: int = 420) -> go.Figure:
    """Applies unified JobMarketDB editorial styling tokens to any Plotly figure."""
    fig.update_layout(
        title={
            "text": f"<b>{title}</b>" if title else "",
            "font": {"size": 16, "color": THEME["text_primary"], "family": THEME["font_family"]},
            "x": 0.0,
            "xanchor": "left",
            "y": 0.96,
        },
        paper_bgcolor=THEME["bg_paper"],
        plot_bgcolor=THEME["bg_plot"],
        font={"family": THEME["font_family"], "color": THEME["text_secondary"], "size": 12},
        margin={"l": 44, "r": 28, "t": 52, "b": 44},
        height=height,
        autosize=True,
        hoverlabel={
            "bgcolor": "#FFFFFF",
            "font_size": 12,
            "font_family": THEME["font_family"],
            "font_color": THEME["text_primary"],
            "bordercolor": THEME["subtle_border"],
        },
        legend={
            "font": {"family": THEME["font_family"], "color": THEME["text_primary"], "size": 11},
            "bgcolor": "rgba(255, 255, 255, 0.9)",
            "bordercolor": THEME["subtle_border"],
            "borderwidth": 1,
        },
    )
    fig.update_xaxes(
        gridcolor=THEME["grid_color"],
        zerolinecolor=THEME["grid_color"],
        tickfont={"color": THEME["text_secondary"], "size": 11},
        title_font={"color": THEME["text_primary"], "size": 12},
    )
    fig.update_yaxes(
        gridcolor=THEME["grid_color"],
        zerolinecolor=THEME["grid_color"],
        tickfont={"color": THEME["text_secondary"], "size": 11},
        title_font={"color": THEME["text_primary"], "size": 12},
    )
    return fig


def create_empty_chart(
    title: str = "Visualization",
    message: str = "No data available for the selected criteria.",
    height: int = 380,
) -> go.Figure:
    """Renders a clean, accessible empty-state figure when input data is missing or empty."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"<b>{message}</b>",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 14, "color": THEME["text_secondary"], "family": THEME["font_family"]},
    )
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
    return apply_theme(fig, title=title, height=height)


def create_horizontal_ranking_chart(
    items: Optional[List[Dict[str, Any]]],
    label_key: str,
    value_key: str,
    title: str = "Ranking",
    x_axis_title: str = "Count",
    max_items: int = 10,
    color_hex: str = THEME["accent_blue"],
    height: int = 420,
) -> go.Figure:
    """
    Builds a clean horizontal ranking bar chart from an array of dictionaries.
    Ensures input immutability and sorts ascending so top items appear at top of chart.
    """
    if not items:
        return create_empty_chart(title=title, height=height)

    # Immutability copy & slicing
    safe_items = [dict(d) for d in items[:max_items]]
    # Reverse order so highest rank displays at top in horizontal layout
    safe_items.reverse()

    labels = [str(d.get(label_key, "Unknown")) for d in safe_items]
    values = [float(d.get(value_key, 0) or 0) for d in safe_items]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(
                color=color_hex,
                line=dict(color="rgba(46, 58, 45, 0.15)", width=1),
            ),
            text=[f"{v:,.0f}" for v in values],
            textposition="auto",
            hovertemplate=f"<b>%{{y}}</b><br>{x_axis_title}: %{{x:,.0f}}<extra></extra>",
        )
    )

    fig = apply_theme(fig, title=title, height=height)
    fig.update_xaxes(title_text=x_axis_title)
    return fig


def create_salary_distribution_chart(
    distribution_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
    title: str = "Salary Bucket Distribution",
    height: int = 420,
) -> go.Figure:
    """
    Builds a vertical bar chart from Operation 11 (get_salary_distributions) bucket data.
    Safely extracts buckets array, formats currency intervals, and calculates percentages.
    """
    if not distribution_data:
        return create_empty_chart(title=title, height=height)

    # Extract bucket list whether passed full result dict or direct list
    if isinstance(distribution_data, dict):
        raw_buckets = distribution_data.get("buckets", [])
    elif isinstance(distribution_data, list):
        raw_buckets = distribution_data
    else:
        raw_buckets = []

    if not raw_buckets:
        return create_empty_chart(title=title, height=height)

    safe_buckets = [dict(b) for b in raw_buckets]

    # Friendly bucket label mapping
    label_map = {
        "<60000": "< $60k",
        "60000-79999": "$60k – $80k",
        "80000-99999": "$80k – $100k",
        "100000-119999": "$100k – $120k",
        "120000-159999": "$120k – $160k",
        ">=160000": "≥ $160k",
    }

    labels = [label_map.get(b.get("salary_bucket"), b.get("salary_bucket", "Unknown")) for b in safe_buckets]
    counts = [int(b.get("count", 0) or 0) for b in safe_buckets]
    avg_salaries = [float(b.get("avg_salary", 0) or 0) for b in safe_buckets]
    total_postings = sum(counts)

    percentages = [(c / total_postings * 100) if total_postings > 0 else 0 for c in counts]

    # Warm gradient of sage and deep olive tones
    bucket_colors = [
        "#8EA08B",  # Light Sage
        "#7A8E77",  # Medium Sage
        "#677C64",  # Rich Sage
        "#536A51",  # Soft Olive
        "#40573F",  # Deep Olive
        "#2E3A2D",  # Dark Olive
    ]
    # Match colors length to bucket length
    colors = [bucket_colors[i % len(bucket_colors)] for i in range(len(labels))]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=counts,
            marker=dict(
                color=colors,
                line=dict(color="rgba(46, 58, 45, 0.2)", width=1),
            ),
            text=[f"{c:,}<br>({p:.1f}%)" for c, p in zip(counts, percentages)],
            textposition="auto",
            customdata=[f"${a:,.0f}" if a > 0 else "N/A" for a in avg_salaries],
            hovertemplate="<b>Bucket:</b> %{x}<br><b>Postings:</b> %{y:,} (%{text})<br><b>Avg Midpoint:</b> %{customdata}<extra></extra>",
        )
    )

    fig = apply_theme(fig, title=title, height=height)
    fig.update_xaxes(title_text="Annual Salary Tier (USD)")
    fig.update_yaxes(title_text="Total Postings")
    return fig


def create_skills_demand_chart(
    skills_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
    title: str = "Top Demanded Skills",
    platform: Optional[str] = None,
    source: Optional[str] = None,
    max_skills: int = 12,
    height: int = 440,
) -> go.Figure:
    """
    Builds a horizontal ranking chart for skill demand from Operation 8 or Priority 2 platform breakdown.
    Applies authentic platform colors (LinkedIn blue or Indeed blue) and displays percentage tags.
    """
    if not skills_data:
        return create_empty_chart(title=title, height=height)

    if isinstance(skills_data, dict):
        raw_skills = skills_data.get("skills", [])
    elif isinstance(skills_data, list):
        raw_skills = skills_data
    else:
        raw_skills = []

    if not raw_skills:
        return create_empty_chart(title=title, height=height)

    # Immutability copy
    safe_skills = [dict(s) for s in raw_skills[:max_skills]]
    safe_skills.reverse()

    labels = [str(s.get("skill", s.get("name", "Unknown"))) for s in safe_skills]
    counts = [int(s.get("count", 0) or 0) for s in safe_skills]
    percentages = [float(s.get("percentage_of_postings", s.get("percentage", 0)) or 0) for s in safe_skills]

    # Platform theme selection
    effective_platform = (platform or source or "").strip().lower()
    if effective_platform == "linkedin":
        bar_color = THEME["linkedin_blue"]
    elif effective_platform == "indeed":
        bar_color = THEME["indeed_blue"]
    else:
        bar_color = THEME["accent_olive"]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=labels,
            orientation="h",
            marker=dict(
                color=bar_color,
                line=dict(color="rgba(46, 58, 45, 0.15)", width=1),
            ),
            text=[f"{c:,} ({p:.1f}%)" if p > 0 else f"{c:,}" for c, p in zip(counts, percentages)],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Postings: %{x:,}<br>Market Share: %{text}<extra></extra>",
        )
    )

    fig = apply_theme(fig, title=title, height=height)
    fig.update_xaxes(title_text="Unique Postings Requiring Skill")
    return fig


def create_geographic_comparison_chart(
    locations_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
    title: str = "Top Job Locations by US State",
    max_states: int = 15,
    height: int = 460,
) -> go.Figure:
    """
    Builds a horizontal bar chart of top state locations from Operation 10 (get_top_job_locations).
    """
    if not locations_data:
        return create_empty_chart(title=title, height=height)

    if isinstance(locations_data, dict):
        raw_locs = locations_data.get("locations", [])
    elif isinstance(locations_data, list):
        raw_locs = locations_data
    else:
        raw_locs = []

    if not raw_locs:
        return create_empty_chart(title=title, height=height)

    safe_locs = [dict(loc) for loc in raw_locs[:max_states]]
    safe_locs.reverse()

    states = [str(loc.get("state", "Unknown")) for loc in safe_locs]
    counts = [int(loc.get("postings_count") if loc.get("postings_count") is not None else (loc.get("count", 0) or 0)) for loc in safe_locs]
    total_in_subset = sum(counts)
    percentages = [
        float(loc.get("percentage") if loc.get("percentage") is not None else ((c / total_in_subset * 100) if total_in_subset > 0 else 0.0))
        for loc, c in zip(safe_locs, counts)
    ]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=states,
            orientation="h",
            marker=dict(
                color=THEME["accent_olive"],
                line=dict(color="rgba(46, 58, 45, 0.15)", width=1),
            ),
            text=[f"{c:,} ({p:.1f}%)" if p > 0 else f"{c:,}" for c, p in zip(counts, percentages)],
            textposition="auto",
            hovertemplate="<b>State: %{y}</b><br>Postings: %{x:,}<br>National Share: %{text}<extra></extra>",
        )
    )

    fig = apply_theme(fig, title=title, height=height)
    fig.update_xaxes(title_text="Total Postings")
    return fig


def create_us_choropleth_map(
    locations_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
    title: str = "US Job Demand Geography Heatmap",
    height: int = 500,
) -> go.Figure:
    """
    Builds an interactive US choropleth heatmap from state distribution data.
    Uses refined warm ivory and sage-olive tonal progression.
    """
    if not locations_data:
        return create_empty_chart(title=title, height=height)

    if isinstance(locations_data, dict):
        raw_locs = locations_data.get("locations", [])
    elif isinstance(locations_data, list):
        raw_locs = locations_data
    else:
        raw_locs = []

    if not raw_locs:
        return create_empty_chart(title=title, height=height)

    safe_locs = [dict(loc) for loc in raw_locs if loc.get("state")]

    states = [loc["state"] for loc in safe_locs]
    counts = [int(loc.get("postings_count") if loc.get("postings_count") is not None else (loc.get("count", 0) or 0)) for loc in safe_locs]

    # Editorial warm ivory to deep olive colorscale
    editorial_colorscale = [
        [0.0, "#FAF8F5"],
        [0.15, "#E8EDE7"],
        [0.35, "#A4B5A2"],
        [0.65, "#6E856C"],
        [1.0, "#2E3A2D"],
    ]

    fig = go.Figure(
        data=go.Choropleth(
            locations=states,
            z=counts,
            locationmode="USA-states",
            colorscale=editorial_colorscale,
            colorbar=dict(
                title=dict(text="Postings", font=dict(family=THEME["font_family"], color=THEME["text_primary"])),
                tickfont=dict(family=THEME["font_family"], color=THEME["text_secondary"]),
            ),
            marker_line_color="#E2DDD5",
            marker_line_width=1.0,
            hovertemplate="<b>State: %{location}</b><br>Postings: %{z:,}<extra></extra>",
        )
    )

    fig.update_layout(
        geo=dict(
            scope="usa",
            projection_type="albers usa",
            showlakes=True,
            lakecolor="#FAF8F5",
            bgcolor="#FAF8F5",
            countrycolor="#E2DDD5",
        ),
        paper_bgcolor=THEME["bg_paper"],
        plot_bgcolor=THEME["bg_plot"],
        font={"family": THEME["font_family"], "color": THEME["text_secondary"]},
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        height=height,
        title={
            "text": f"<b>{title}</b>",
            "font": {"size": 16, "color": THEME["text_primary"], "family": THEME["font_family"]},
            "x": 0.05,
        },
    )
    return fig


def create_platform_comparison_chart(
    comparison_data: Optional[Dict[str, Any]],
    metric: str = "volume",
    title: str = "Cross-Platform Market Comparison",
    height: int = 400,
) -> go.Figure:
    """
    Builds comparative bar charts for LinkedIn vs Indeed metrics from Operation 12 (compare_sources).
    metric options: 'volume' (postings count), 'salary_coverage' (%), 'remote_rate' (%).
    """
    if not comparison_data:
        return create_empty_chart(title=title, height=height)

    # Copy to ensure immutability
    comp = dict(comparison_data)
    platforms_dict = comp.get("platforms", comp)
    linkedin_metrics = platforms_dict.get("linkedin", {})
    indeed_metrics = platforms_dict.get("indeed", {})

    if metric == "volume":
        y_values = [
            linkedin_metrics.get("total_postings", 0),
            indeed_metrics.get("total_postings", 0),
        ]
        y_axis_title = "Total Postings"
        text_labels = [f"{v:,}" for v in y_values]
    elif metric == "salary_coverage":
        def _get_sal_pct(m: Dict[str, Any]) -> float:
            if "salary_coverage_pct" in m:
                return float(m["salary_coverage_pct"] or 0)
            return float(m.get("salary_coverage", {}).get("coverage_percentage", 0) or 0)

        y_values = [_get_sal_pct(linkedin_metrics), _get_sal_pct(indeed_metrics)]
        y_axis_title = "Salary Stated / Derived (%)"
        text_labels = [f"{v:.1f}%" for v in y_values]
    elif metric == "remote_rate":
        def _get_rem_pct(m: Dict[str, Any]) -> float:
            if "remote_pct" in m:
                return float(m["remote_pct"] or 0)
            return float(m.get("remote_work_breakdown", {}).get("remote_percentage", 0) or 0)

        y_values = [_get_rem_pct(linkedin_metrics), _get_rem_pct(indeed_metrics)]
        y_axis_title = "Explicitly Remote (%)"
        text_labels = [f"{v:.1f}%" for v in y_values]
    else:
        return create_empty_chart(title=title, message=f"Unsupported metric: {metric}", height=height)

    platforms = ["LinkedIn", "Indeed"]
    colors = [THEME["linkedin_blue"], THEME["indeed_blue"]]

    fig = go.Figure(
        go.Bar(
            x=platforms,
            y=y_values,
            marker=dict(
                color=colors,
                line=dict(color="rgba(46, 58, 45, 0.2)", width=1),
            ),
            text=text_labels,
            textposition="auto",
            hovertemplate="<b>Platform: %{x}</b><br>" + y_axis_title + ": %{text}<extra></extra>",
        )
    )

    fig = apply_theme(fig, title=title, height=height)
    fig.update_yaxes(title_text=y_axis_title)
    return fig


def create_grouped_bar_chart(
    categories: List[str],
    series_a: List[float],
    series_b: List[float],
    name_a: str = "LinkedIn",
    name_b: str = "Indeed",
    color_a: str = THEME["linkedin_blue"],
    color_b: str = "#2164F3",
    title: str = "Comparative Distribution",
    y_axis_title: str = "Percentage (%)",
    x_axis_title: Optional[str] = None,
    format_pct: bool = True,
    height: int = 440,
) -> go.Figure:
    """
    Builds a themed side-by-side grouped bar chart comparing two platform metrics.
    Safe for empty inputs.
    """
    if not categories or not series_a or not series_b:
        return create_empty_chart(title=title, height=height)

    fig = go.Figure()

    text_a = [f"{v:.1f}%" if format_pct else f"{int(v):,}" for v in series_a]
    text_b = [f"{v:.1f}%" if format_pct else f"{int(v):,}" for v in series_b]

    fig.add_trace(
        go.Bar(
            name=name_a,
            x=categories,
            y=series_a,
            marker_color=color_a,
            text=text_a,
            textposition="auto",
            hovertemplate=f"<b>{name_a}</b><br>%{{x}}: %{{text}}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            name=name_b,
            x=categories,
            y=series_b,
            marker_color=color_b,
            text=text_b,
            textposition="auto",
            hovertemplate=f"<b>{name_b}</b><br>%{{x}}: %{{text}}<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=THEME["text_primary"]),
        ),
    )

    fig = apply_theme(fig, title=title, height=height)
    fig.update_yaxes(title_text=y_axis_title)
    if x_axis_title:
        fig.update_xaxes(title_text=x_axis_title)

    return fig


def create_shared_employers_chart(
    employers: List[Dict[str, Any]],
    title: str = "Top Cross-Platform Employers (Posting Volume)",
    height: int = 440,
) -> go.Figure:
    """
    Builds a grouped horizontal bar chart showing LinkedIn vs Indeed postings for shared employers.
    """
    if not employers:
        return create_empty_chart(title=title, height=height)

    # Reverse for top-to-bottom ranking in horizontal bar chart
    sorted_emps = list(reversed(employers))
    names = [e["company_name"] for e in sorted_emps]
    li_counts = [e["linkedin_postings"] for e in sorted_emps]
    ind_counts = [e["indeed_postings"] for e in sorted_emps]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="LinkedIn",
            y=names,
            x=li_counts,
            orientation="h",
            marker_color=THEME["linkedin_blue"],
            text=[f"{v:,}" for v in li_counts],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>LinkedIn: %{x:,} postings<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Indeed",
            y=names,
            x=ind_counts,
            orientation="h",
            marker_color=THEME["indeed_blue"],
            text=[f"{v:,}" for v in ind_counts],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Indeed: %{x:,} postings<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="stack",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=THEME["text_primary"]),
        ),
    )

    fig = apply_theme(fig, title=title, height=height)
    fig.update_xaxes(title_text="Total Job Postings")
    fig.update_yaxes(title_text="")

    return fig


def create_platform_salary_bucket_chart(
    buckets: List[Dict[str, Any]],
    view_mode: str = "pct_salary_bearing",
    title: str = "Salary Bucket Distribution by Platform",
    height: int = 440,
) -> go.Figure:
    """
    Builds a side-by-side comparative bar chart for the 6 standardized salary tiers.
    view_mode options:
    - 'pct_salary_bearing': Percentage of salary-bearing postings (denominator: LI 36,059; Indeed 5,715)
    - 'pct_total': Percentage of total postings (denominator: LI 123,835; Indeed 5,715)
    - 'count': Raw count of postings in bucket
    """
    if not buckets:
        return create_empty_chart(title=title, height=height)

    labels = [b["bucket"] for b in buckets]

    if view_mode == "pct_salary_bearing":
        li_vals = [b["linkedin_pct_salary_bearing"] for b in buckets]
        ind_vals = [b["indeed_pct_salary_bearing"] for b in buckets]
        y_axis_title = "% of Salary-Bearing Postings"
        format_pct = True
    elif view_mode == "pct_total":
        li_vals = [b["linkedin_pct_total"] for b in buckets]
        ind_vals = [b["indeed_pct_total"] for b in buckets]
        y_axis_title = "% of Total Postings"
        format_pct = True
    else:  # count
        li_vals = [b["linkedin_count"] for b in buckets]
        ind_vals = [b["indeed_count"] for b in buckets]
        y_axis_title = "Postings Count"
        format_pct = False

    return create_grouped_bar_chart(
        categories=labels,
        series_a=li_vals,
        series_b=ind_vals,
        name_a="LinkedIn",
        name_b="Indeed",
        color_a=THEME["linkedin_blue"],
        color_b=THEME["indeed_blue"],
        title=title,
        y_axis_title=y_axis_title,
        x_axis_title="Standardized Salary Tier (USD)",
        format_pct=format_pct,
        height=height,
    )
