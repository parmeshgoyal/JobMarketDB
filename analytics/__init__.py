"""
JobMarketDB - Analytics and Query Package (Phase 5)

Exports the unified analytics service, operational query functions, and aggregation pipelines.
"""

from analytics.service import JobMarketAnalyticsService
from analytics.queries import (
    filter_jobs_by_company,
    filter_jobs_by_experience,
    filter_jobs_by_location,
    filter_jobs_by_salary,
    filter_jobs_by_skills,
    filter_jobs_by_source,
    get_job_by_id,
    get_related_jobs,
    search_and_filter_jobs,
    search_jobs_by_title,
)
from analytics.aggregations import (
    compare_sources,
    get_salary_distributions,
    get_skills_by_platform,
    get_top_demanded_skills,
    get_top_hiring_companies,
    get_top_job_locations,
    get_platform_field_completeness,
    get_shared_employers_summary,
    get_platform_role_distribution,
    get_platform_salary_bucket_comparison,
)
from analytics.crud import (
    create_demo_posting,
    get_demo_postings,
    get_demo_posting_by_id,
    update_demo_posting,
    delete_demo_posting,
    get_demo_collection_stats,
    get_canonical_counts,
)

__all__ = [
    "JobMarketAnalyticsService",
    "get_canonical_counts",
    "search_jobs_by_title",
    "filter_jobs_by_location",
    "filter_jobs_by_salary",
    "filter_jobs_by_skills",
    "filter_jobs_by_company",
    "filter_jobs_by_experience",
    "filter_jobs_by_source",
    "search_and_filter_jobs",
    "get_job_by_id",
    "get_related_jobs",
    "get_skills_by_platform",
    "get_top_demanded_skills",
    "get_top_hiring_companies",
    "get_top_job_locations",
    "get_salary_distributions",
    "compare_sources",
    "get_platform_field_completeness",
    "get_shared_employers_summary",
    "get_platform_role_distribution",
    "get_platform_salary_bucket_comparison",
    "create_demo_posting",
    "get_demo_postings",
    "get_demo_posting_by_id",
    "update_demo_posting",
    "delete_demo_posting",
    "get_demo_collection_stats",
]
