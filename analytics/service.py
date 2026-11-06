"""
JobMarketDB - Unified Analytics & Query Service (Phase 5)

Provides a clean, typed service interface uniting operational queries and analytical
aggregations over the JobMarketDB database collections ('jobs' and 'companies').
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from bson import ObjectId
from database.connection import get_database
from pymongo.database import Database

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
    get_company_overview_stats,
    get_company_profile_and_metrics,
    get_salary_by_experience_level,
    get_salary_by_state,
    get_salary_by_title,
    get_salary_distributions,
    get_salary_histogram_data,
    get_salary_overview_stats,
    get_skills_by_platform,
    get_state_choropleth_data,
    get_top_cities,
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


class JobMarketAnalyticsService:
    """
    Unified, audit-safe service interface for JobMarketDB analytics.
    Enforces read-only execution, correct provenance semantics, and proper index usage.
    """

    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db if db is not None else get_database()

    # -------------------------------------------------------------------------
    # Operational Queries (Operations 1 to 7 + Faceted Search)
    # -------------------------------------------------------------------------

    def search_jobs(
        self,
        query_text: str,
        search_mode: str = "text",
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Operation 1: Job Search by Title."""
        return search_jobs_by_title(
            self.db, query_text=query_text, search_mode=search_mode, limit=limit, skip=skip
        )

    def filter_by_location(
        self,
        state: Optional[str] = None,
        is_remote: Optional[Union[bool, str]] = "any",
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Operation 2: Location & Remote Filtering."""
        return filter_jobs_by_location(
            self.db, state=state, is_remote=is_remote, limit=limit, skip=skip
        )

    def filter_by_salary(
        self,
        salary_bucket: Optional[str] = None,
        min_annual: Optional[float] = None,
        max_annual: Optional[float] = None,
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Operation 3: Salary Range & Bucket Filtering."""
        return filter_jobs_by_salary(
            self.db,
            salary_bucket=salary_bucket,
            min_annual=min_annual,
            max_annual=max_annual,
            limit=limit,
            skip=skip,
        )

    def filter_by_skills(
        self,
        skills: Union[str, List[str]],
        match_all: bool = True,
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Operation 4: Skill Demand Filtering."""
        return filter_jobs_by_skills(
            self.db, skills=skills, match_all=match_all, limit=limit, skip=skip
        )

    def filter_by_company(
        self,
        company_name: Optional[str] = None,
        company_id: Optional[int] = None,
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Operation 5: Company Name & ID Filtering."""
        return filter_jobs_by_company(
            self.db, company_name=company_name, company_id=company_id, limit=limit, skip=skip
        )

    def filter_by_experience(
        self,
        experience_level: str,
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Operation 6: Experience Level Filtering."""
        return filter_jobs_by_experience(
            self.db, experience_level=experience_level, limit=limit, skip=skip
        )

    def filter_by_source(
        self,
        source: str,
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Operation 7: Source Platform Filtering."""
        return filter_jobs_by_source(self.db, source=source, limit=limit, skip=skip)

    def search_and_filter(
        self,
        query_text: Optional[str] = None,
        search_mode: str = "text",
        state: Optional[str] = None,
        is_remote: Optional[Union[bool, str]] = "any",
        salary_bucket: Optional[str] = None,
        min_annual: Optional[float] = None,
        max_annual: Optional[float] = None,
        skills: Optional[Union[str, List[str]]] = None,
        skills_match_all: bool = True,
        company_name: Optional[str] = None,
        experience_level: Optional[str] = None,
        role_category: Optional[str] = None,
        source: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Union[int, str] = -1,
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Multi-Facet Compound Search & Filter with Allowlisted Sorting."""
        return search_and_filter_jobs(
            self.db,
            query_text=query_text,
            search_mode=search_mode,
            state=state,
            is_remote=is_remote,
            salary_bucket=salary_bucket,
            min_annual=min_annual,
            max_annual=max_annual,
            skills=skills,
            skills_match_all=skills_match_all,
            company_name=company_name,
            experience_level=experience_level,
            role_category=role_category,
            source=source,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            skip=skip,
        )

    def get_job_by_id(
        self, job_id: Union[str, int, ObjectId]
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves an individual job posting by MongoDB ObjectId or source_job_id.
        Supports 24-character hex ObjectId strings, ObjectId instances, and source_job_id.
        """
        return get_job_by_id(self.db, job_id=job_id)

    def get_related_jobs(
        self, job_id: Union[str, int, ObjectId], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves related job postings for a given job using transparent, rule-based matching.
        Enforces same-platform taxonomy isolation, target exclusion, and hierarchical ranking.
        """
        return get_related_jobs(self.db, job_id=job_id, limit=limit)

    # -------------------------------------------------------------------------
    # Analytical Aggregations (Operations 8 to 12)
    # -------------------------------------------------------------------------

    def get_top_skills(
        self,
        limit: int = 10,
        source: Optional[str] = None,
        role_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Operation 8: Top Demanded Skills Aggregation."""
        return get_top_demanded_skills(
            self.db, limit=limit, source=source, role_category=role_category
        )

    def get_skills_by_platform(
        self,
        limit: int = 10,
        role_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Priority 2: Separate Platform Skill Demand Rankings (LinkedIn Disciplines vs Indeed Tools)."""
        return get_skills_by_platform(
            self.db, limit=limit, role_category=role_category
        )

    def get_top_companies(
        self,
        limit: int = 10,
        source: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Operation 9: Top Hiring Companies Aggregation."""
        return get_top_hiring_companies(
            self.db, limit=limit, source=source, state=state
        )

    def get_top_locations(
        self,
        limit: int = 10,
        source: Optional[str] = None,
        is_remote: Optional[Union[bool, str]] = "any",
    ) -> Dict[str, Any]:
        """Operation 10: Top Job Locations Aggregation."""
        return get_top_job_locations(
            self.db, limit=limit, source=source, is_remote=is_remote
        )

    def get_salary_distribution(
        self,
        source: Optional[str] = None,
        role_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Operation 11: Salary Distributions Aggregation."""
        return get_salary_distributions(
            self.db, source=source, role_category=role_category
        )

    def compare_platforms(self) -> Dict[str, Any]:
        """Operation 12: Cross-Platform Comparison (LinkedIn vs Indeed)."""
        return compare_sources(self.db)

    def get_company_details(self, company_name: str) -> Dict[str, Any]:
        """Retrieves comprehensive employer metrics from 'jobs' and links with 'companies' profile."""
        return get_company_profile_and_metrics(self.db, company_name=company_name)

    def get_top_cities(
        self,
        limit: int = 10,
        source: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves top hiring cities in the United States."""
        return get_top_cities(self.db, limit=limit, source=source, state=state)

    def get_state_choropleth(
        self,
        source: Optional[str] = None,
        is_remote: Optional[Union[bool, str]] = "any",
    ) -> Dict[str, Any]:
        """Retrieves complete US state distribution for choropleth mapping."""
        return get_state_choropleth_data(self.db, source=source, is_remote=is_remote)

    def get_company_overview(self) -> Dict[str, Any]:
        """Retrieves high-level employer statistics comparing canonical companies with job postings."""
        return get_company_overview_stats(self.db)

    # -------------------------------------------------------------------------
    # Phase 6 Step 7: Salary Analytics
    # -------------------------------------------------------------------------

    def get_salary_overview(self) -> Dict[str, Any]:
        """Phase 6 Step 7: Salary coverage KPIs, central tendency, and outlier audit summary."""
        return get_salary_overview_stats(self.db)

    def get_salary_by_experience(
        self,
        outlier_threshold: Optional[float] = 1_000_000,
    ) -> Dict[str, Any]:
        """Phase 6 Step 7: Salary by LinkedIn experience level (unadjusted + threshold-adjusted)."""
        return get_salary_by_experience_level(self.db, outlier_threshold=outlier_threshold)

    def get_salary_by_state(
        self,
        limit: int = 15,
        min_postings: int = 50,
        outlier_threshold: Optional[float] = 1_000_000,
    ) -> Dict[str, Any]:
        """Phase 6 Step 7: Salary by US state (LinkedIn only, >= min_postings records)."""
        return get_salary_by_state(
            self.db, limit=limit, min_postings=min_postings, outlier_threshold=outlier_threshold
        )

    def get_salary_by_title(
        self,
        limit: int = 20,
        min_postings: int = 20,
        outlier_threshold: Optional[float] = 1_000_000,
    ) -> Dict[str, Any]:
        """Phase 6 Step 7: Salary by job title (LinkedIn only, threshold-adjusted mean)."""
        return get_salary_by_title(
            self.db, limit=limit, min_postings=min_postings, outlier_threshold=outlier_threshold
        )

    def get_salary_histogram(
        self,
        source: str = "linkedin",
        outlier_threshold: Optional[float] = 1_000_000,
    ) -> Dict[str, Any]:
        """Phase 6 Step 7: Raw salary values for histogram rendering (LinkedIn or Indeed)."""
        return get_salary_histogram_data(self.db, source=source, outlier_threshold=outlier_threshold)

    # -------------------------------------------------------------------------
    # Phase 6 Step 8: Platform Comparison Analytics
    # -------------------------------------------------------------------------

    def get_platform_field_completeness(self) -> Dict[str, Any]:
        """Phase 6 Step 8: Source-specific field completeness and missing-value audit."""
        return get_platform_field_completeness(self.db)

    def get_shared_employers_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Phase 6 Step 8: Cross-platform employer overlap analysis and top shared employers."""
        return get_shared_employers_summary(self.db, limit=limit)

    def get_platform_role_distribution(self) -> Dict[str, Any]:
        """Phase 6 Step 8: Role category breakdown by platform (specialization comparison)."""
        return get_platform_role_distribution(self.db)

    def get_platform_salary_bucket_comparison(self) -> Dict[str, Any]:
        """Phase 6 Step 8: 6-tier standardized salary bucket comparison with provenance notes."""
        return get_platform_salary_bucket_comparison(self.db)

    # -------------------------------------------------------------------------
    # Phase 6 Step 9: Isolated CRUD Demo Sandbox (demo_postings only)
    # -------------------------------------------------------------------------

    def create_demo_posting(
        self,
        title: str,
        company_name: str,
        description: str,
        location_city: Optional[str] = None,
        location_state: Optional[str] = None,
        is_remote: bool = False,
        skills: Optional[List[str]] = None,
        source: str = "Demonstration Sandbox",
        experience_level: Optional[str] = None,
        salary_min: Optional[float] = None,
        salary_max: Optional[float] = None,
        salary_currency: str = "USD",
        salary_period: str = "yearly",
    ) -> Dict[str, Any]:
        """Phase 6 Step 9: Creates a demonstration posting strictly in demo_postings."""
        return create_demo_posting(
            self.db,
            title=title,
            company_name=company_name,
            description=description,
            location_city=location_city,
            location_state=location_state,
            is_remote=is_remote,
            skills=skills,
            source=source,
            experience_level=experience_level,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            salary_period=salary_period,
        )

    def get_demo_postings(
        self,
        search_query: Optional[str] = None,
        state: Optional[str] = None,
        is_remote: Optional[bool] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Phase 6 Step 9: Reads demonstration postings from demo_postings."""
        return get_demo_postings(
            self.db,
            search_query=search_query,
            state=state,
            is_remote=is_remote,
            limit=limit,
            skip=skip,
        )

    def get_demo_posting_by_id(self, identifier: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
        """Phase 6 Step 9: Fetches single demo posting by ObjectId or demo_id."""
        return get_demo_posting_by_id(self.db, identifier=identifier)

    def update_demo_posting(
        self,
        doc_id: Union[str, ObjectId],
        title: Optional[str] = None,
        company_name: Optional[str] = None,
        description: Optional[str] = None,
        location_city: Optional[str] = None,
        location_state: Optional[str] = None,
        is_remote: Optional[bool] = None,
        skills: Optional[List[str]] = None,
        experience_level: Optional[str] = None,
        salary_min: Optional[float] = None,
        salary_max: Optional[float] = None,
        salary_period: Optional[str] = None,
        remove_salary: bool = False,
    ) -> Dict[str, Any]:
        """Phase 6 Step 9: Updates specific fields of an existing posting in demo_postings."""
        return update_demo_posting(
            self.db,
            doc_id=doc_id,
            title=title,
            company_name=company_name,
            description=description,
            location_city=location_city,
            location_state=location_state,
            is_remote=is_remote,
            skills=skills,
            experience_level=experience_level,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_period=salary_period,
            remove_salary=remove_salary,
        )

    def delete_demo_posting(self, doc_id: Union[str, ObjectId]) -> bool:
        """Phase 6 Step 9: Deletes a single demonstration posting from demo_postings."""
        return delete_demo_posting(self.db, doc_id=doc_id)

    def get_demo_collection_stats(self) -> Dict[str, Any]:
        """Phase 6 Step 9: Summary metrics for demo_postings."""
        return get_demo_collection_stats(self.db)

    def get_canonical_counts(self) -> Dict[str, int]:
        """Phase 6 Step 9: Returns exact read-only document counts for canonical collections ('jobs' and 'companies')."""
        return get_canonical_counts(self.db)
