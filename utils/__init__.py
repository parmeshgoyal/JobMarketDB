"""
JobMarketDB - UI Utilities and Plotting Package (Phase 6)
"""

from utils.ui_components import (
    US_STATES,
    load_custom_css,
    render_header,
    render_metric_card,
    render_platform_badge,
    render_state_selector,
    render_pagination_controls,
    render_empty_state,
    render_loading_state,
    render_error_state,
    render_callout,
)

from utils.plots import (
    THEME,
    apply_theme,
    create_empty_chart,
    create_horizontal_ranking_chart,
    create_salary_distribution_chart,
    create_skills_demand_chart,
    create_geographic_comparison_chart,
    create_us_choropleth_map,
    create_platform_comparison_chart,
)

__all__ = [
    "US_STATES",
    "load_custom_css",
    "render_header",
    "render_metric_card",
    "render_platform_badge",
    "render_state_selector",
    "render_pagination_controls",
    "render_empty_state",
    "render_loading_state",
    "render_error_state",
    "render_callout",
    "THEME",
    "apply_theme",
    "create_empty_chart",
    "create_horizontal_ranking_chart",
    "create_salary_distribution_chart",
    "create_skills_demand_chart",
    "create_geographic_comparison_chart",
    "create_us_choropleth_map",
    "create_platform_comparison_chart",
]
