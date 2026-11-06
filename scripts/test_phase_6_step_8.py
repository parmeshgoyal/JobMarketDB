"""
JobMarketDB - Phase 6 Step 8 Test Suite: Platform Comparison

Comprehensive verification of:
1. Platform posting volume totals and proportions.
2. Source-specific field completeness and exact denominators across 14 attributes.
3. Missing/null handling and tri-state modality isolation.
4. Salary structure separation (continuous annualized pay vs derived search-band midpoints).
5. Skills taxonomy boundary isolation (35 functional disciplines vs 464 tools).
6. Indeed experience-level omission disclosure (0.0% populated).
7. Cross-platform employer intersection (570 shared employers).
8. Role category specialization comparison (Indeed 100% data roles vs LinkedIn general).
9. Robust input validation and edge cases.
10. Database invariants before and after test execution.
"""

import unittest
from typing import Any, Dict, List
import pymongo

from database.connection import get_database
from analytics.service import JobMarketAnalyticsService
from analytics.aggregations import (
    compare_sources,
    get_platform_field_completeness,
    get_shared_employers_summary,
    get_platform_role_distribution,
    get_platform_salary_bucket_comparison,
    get_skills_by_platform,
)
from utils.plots import (
    create_grouped_bar_chart,
    create_shared_employers_chart,
    create_platform_salary_bucket_chart,
    create_platform_comparison_chart,
)


class TestPhase6Step8PlatformComparison(unittest.TestCase):
    """Phase 6 Step 8 automated verification suite."""

    @classmethod
    def setUpClass(cls):
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)
        cls.raw_client = pymongo.MongoClient("mongodb://localhost:27017/")
        cls.raw_db = cls.raw_client["jobmarketdb"]

        # Initial invariant assertion
        cls._verify_invariants()

    @classmethod
    def tearDownClass(cls):
        # Post-execution invariant assertion
        cls._verify_invariants()
        cls.raw_client.close()

    @classmethod
    def _verify_invariants(cls):
        jobs_count = cls.raw_db.jobs.count_documents({})
        companies_count = cls.raw_db.companies.count_documents({})
        jobs_indexes = len(cls.raw_db.jobs.index_information())
        companies_indexes = len(cls.raw_db.companies.index_information())

        assert jobs_count == 129550, f"Jobs invariant violated! Expected 129,550, got {jobs_count}"
        assert companies_count == 24472, f"Companies invariant violated! Expected 24,472, got {companies_count}"
        assert (jobs_indexes + companies_indexes) == 15, (
            f"Total indexes invariant violated! Expected 15 (11 jobs + 4 companies), got {jobs_indexes + companies_indexes}"
        )


    # -------------------------------------------------------------------------
    # 1. Platform Totals & Proportions
    # -------------------------------------------------------------------------
    def test_platform_totals_and_proportions(self):
        """Verify LinkedIn and Indeed counts and proportions against ground truth."""
        res = self.service.compare_platforms()
        self.assertEqual(res.get("operation"), "linkedin_vs_indeed_comparison")

        platforms = res.get("platforms", {})
        li = platforms.get("linkedin", {})
        ind = platforms.get("indeed", {})

        total_li = li.get("total_postings", 0)
        total_ind = ind.get("total_postings", 0)
        total_all = total_li + total_ind

        self.assertEqual(total_li, 123835)
        self.assertEqual(total_ind, 5715)
        self.assertEqual(total_all, 129550)

        pct_li = round(total_li / total_all * 100, 2)
        pct_ind = round(total_ind / total_all * 100, 2)
        self.assertEqual(pct_li, 95.59)
        self.assertEqual(pct_ind, 4.41)

    # -------------------------------------------------------------------------
    # 2. Source-Specific Field Completeness & Denominators
    # -------------------------------------------------------------------------
    def test_field_completeness_and_denominators(self):
        """Verify field completeness audit across all 14 evaluated attributes."""
        res = self.service.get_platform_field_completeness()
        self.assertEqual(res.get("operation"), "platform_field_completeness")
        self.assertEqual(res.get("total_jobs"), 129550)

        plat = res.get("platforms", {})
        self.assertEqual(plat["linkedin"]["total_postings"], 123835)
        self.assertEqual(plat["indeed"]["total_postings"], 5715)

        fields = {f["field"]: f for f in res.get("fields", [])}
        self.assertEqual(len(fields), 14)

        # 1. Company Name
        self.assertEqual(fields["company.name"]["linkedin_count"], 122116)
        self.assertEqual(fields["company.name"]["linkedin_pct"], 98.61)
        self.assertEqual(fields["company.name"]["indeed_count"], 5611)
        self.assertEqual(fields["company.name"]["indeed_pct"], 98.18)

        # 2. State
        self.assertEqual(fields["location.state"]["linkedin_count"], 112159)
        self.assertEqual(fields["location.state"]["linkedin_pct"], 90.57)
        self.assertEqual(fields["location.state"]["indeed_count"], 5381)
        self.assertEqual(fields["location.state"]["indeed_pct"], 94.16)

        # 3. City (Indeed upstream gap)
        self.assertEqual(fields["location.city"]["linkedin_count"], 108855)
        self.assertEqual(fields["location.city"]["linkedin_pct"], 87.9)
        self.assertEqual(fields["location.city"]["indeed_count"], 0)
        self.assertEqual(fields["location.city"]["indeed_pct"], 0.0)

        # 4. Remote Explicit
        self.assertEqual(fields["location.is_remote"]["linkedin_count"], 15236)
        self.assertEqual(fields["location.is_remote"]["linkedin_pct"], 12.3)
        self.assertEqual(fields["location.is_remote"]["indeed_count"], 0)
        self.assertEqual(fields["location.is_remote"]["indeed_pct"], 0.0)

        # 5. Continuous Salary (normalized_annual)
        self.assertEqual(fields["salary.normalized_annual"]["linkedin_count"], 36059)
        self.assertEqual(fields["salary.normalized_annual"]["linkedin_pct"], 29.12)
        self.assertEqual(fields["salary.normalized_annual"]["indeed_count"], 0)
        self.assertEqual(fields["salary.normalized_annual"]["indeed_pct"], 0.0)

        # 6. Derived Midpoint (estimated_midpoint)
        self.assertEqual(fields["salary.estimated_midpoint"]["linkedin_count"], 0)
        self.assertEqual(fields["salary.estimated_midpoint"]["linkedin_pct"], 0.0)
        self.assertEqual(fields["salary.estimated_midpoint"]["indeed_count"], 5715)
        self.assertEqual(fields["salary.estimated_midpoint"]["indeed_pct"], 100.0)

        # 7. Standardized Salary Bucket
        self.assertEqual(fields["salary.salary_bucket"]["linkedin_count"], 36059)
        self.assertEqual(fields["salary.salary_bucket"]["linkedin_pct"], 29.12)
        self.assertEqual(fields["salary.salary_bucket"]["indeed_count"], 5715)
        self.assertEqual(fields["salary.salary_bucket"]["indeed_pct"], 100.0)

        # 8. Skills
        self.assertEqual(fields["skills"]["linkedin_count"], 122083)
        self.assertEqual(fields["skills"]["linkedin_pct"], 98.59)
        self.assertEqual(fields["skills"]["indeed_count"], 5483)
        self.assertEqual(fields["skills"]["indeed_pct"], 95.94)

        # 9. Experience Level
        self.assertEqual(fields["experience_level"]["linkedin_count"], 94439)
        self.assertEqual(fields["experience_level"]["linkedin_pct"], 76.26)
        self.assertEqual(fields["experience_level"]["indeed_count"], 0)
        self.assertEqual(fields["experience_level"]["indeed_pct"], 0.0)

        # 10. Employment Type
        self.assertEqual(fields["normalized_employment_type"]["linkedin_count"], 123835)
        self.assertEqual(fields["normalized_employment_type"]["linkedin_pct"], 100.0)
        self.assertEqual(fields["normalized_employment_type"]["indeed_count"], 0)
        self.assertEqual(fields["normalized_employment_type"]["indeed_pct"], 0.0)

        # 11. Role Category
        self.assertEqual(fields["role_category"]["linkedin_count"], 123835)
        self.assertEqual(fields["role_category"]["linkedin_pct"], 100.0)
        self.assertEqual(fields["role_category"]["indeed_count"], 5715)
        self.assertEqual(fields["role_category"]["indeed_pct"], 100.0)

        # 12. Description
        self.assertEqual(fields["description"]["linkedin_count"], 123828)
        self.assertEqual(fields["description"]["linkedin_pct"], 99.99)
        self.assertEqual(fields["description"]["indeed_count"], 5413)
        self.assertEqual(fields["description"]["indeed_pct"], 94.72)

        # 13. Posted Date
        self.assertEqual(fields["posted_date"]["linkedin_count"], 123835)
        self.assertEqual(fields["posted_date"]["linkedin_pct"], 100.0)
        self.assertEqual(fields["posted_date"]["indeed_count"], 0)
        self.assertEqual(fields["posted_date"]["indeed_pct"], 0.0)

        # 14. Job URL
        self.assertEqual(fields["job_url"]["linkedin_count"], 123835)
        self.assertEqual(fields["job_url"]["linkedin_pct"], 100.0)
        self.assertEqual(fields["job_url"]["indeed_count"], 5715)
        self.assertEqual(fields["job_url"]["indeed_pct"], 100.0)

    # -------------------------------------------------------------------------
    # 3. Missing / Null Accounting & Invariants
    # -------------------------------------------------------------------------
    def test_missing_and_null_accounting(self):
        """Verify that Populated + Missing == Denominator for all fields on both platforms."""
        res = self.service.get_platform_field_completeness()
        fields = res.get("fields", [])

        for f in fields:
            li_total = f["linkedin_count"] + f["linkedin_missing"]
            ind_total = f["indeed_count"] + f["indeed_missing"]
            self.assertEqual(
                li_total,
                123835,
                f"LinkedIn denominator mismatch on {f['field']}: {li_total} != 123,835",
            )
            self.assertEqual(
                ind_total,
                5715,
                f"Indeed denominator mismatch on {f['field']}: {ind_total} != 5,715",
            )

    # -------------------------------------------------------------------------
    # 4. Workplace Modality Tri-State Model
    # -------------------------------------------------------------------------
    def test_workplace_modality_tri_state_isolation(self):
        """Confirm that Null is never coerced into False for remote work."""
        res = self.service.compare_platforms()
        platforms = res.get("platforms", {})
        li_rem = platforms["linkedin"]["remote_work_breakdown"]
        ind_rem = platforms["indeed"]["remote_work_breakdown"]

        # LinkedIn: 15,236 True, 0 False, 108,599 Null
        self.assertEqual(li_rem["explicitly_remote"], 15236)
        self.assertEqual(li_rem["explicitly_on_site"], 0)
        self.assertEqual(li_rem["unknown_unspecified"], 108599)
        self.assertEqual(
            li_rem["explicitly_remote"] + li_rem["explicitly_on_site"] + li_rem["unknown_unspecified"],
            123835,
        )

        # Indeed: 0 True, 0 False, 5,715 Null
        self.assertEqual(ind_rem["explicitly_remote"], 0)
        self.assertEqual(ind_rem["explicitly_on_site"], 0)
        self.assertEqual(ind_rem["unknown_unspecified"], 5715)
        self.assertEqual(
            ind_rem["explicitly_remote"] + ind_rem["explicitly_on_site"] + ind_rem["unknown_unspecified"],
            5715,
        )

    # -------------------------------------------------------------------------
    # 5. Salary Structure Separation & Correct Labels
    # -------------------------------------------------------------------------
    def test_salary_structure_separation(self):
        """Verify that continuous pay and derived midpoints are never conflated."""
        res = self.service.get_platform_salary_bucket_comparison()
        self.assertEqual(res.get("operation"), "platform_salary_bucket_comparison")

        li_m = res.get("linkedin_metrics", {})
        ind_m = res.get("indeed_metrics", {})

        # Confirm distinct labels and semantics
        self.assertEqual(
            li_m["metric_type"], "Continuous Annualized Compensation (normalized_annual)"
        )
        self.assertEqual(
            ind_m["metric_type"], "Derived Search-Band Midpoint (estimated_midpoint)"
        )

        # Confirm LinkedIn audited values
        self.assertEqual(li_m["coverage_count"], 36059)
        self.assertEqual(li_m["adjusted_postings_count"], 36021)
        self.assertEqual(li_m["adjusted_mean"], 95515.00)
        self.assertEqual(li_m["median"], 81375.0)
        self.assertEqual(li_m["outliers_count"], 38)
        self.assertEqual(li_m["min_val"], 1.0)
        self.assertEqual(li_m["max_val"], 960000.0)

        # Confirm Indeed audited values
        self.assertEqual(ind_m["coverage_count"], 5715)
        self.assertEqual(ind_m["mean"], 116501.31)
        self.assertEqual(ind_m["median"], 110000.0)
        self.assertEqual(ind_m["min_val"], 70000.0)
        self.assertEqual(ind_m["max_val"], 175000.0)
        self.assertEqual(ind_m["outliers_count"], 0)

        # Confirm 6 buckets sum to salary-bearing totals
        buckets = res.get("buckets", [])
        self.assertEqual(len(buckets), 6)
        total_li_b = sum(b["linkedin_count"] for b in buckets)
        total_ind_b = sum(b["indeed_count"] for b in buckets)
        self.assertEqual(total_li_b, 36059)
        self.assertEqual(total_ind_b, 5715)

        # Verify methodology warning
        self.assertIn("Methodological Incompatibility Notice", res.get("methodology_warning", ""))

    # -------------------------------------------------------------------------
    # 6. Skills Taxonomy Separation
    # -------------------------------------------------------------------------
    def test_skills_taxonomy_separation(self):
        """Verify that LinkedIn 35 functional domains and Indeed 464 tools remain isolated."""
        res = self.service.get_skills_by_platform(limit=5)
        self.assertEqual(res.get("operation"), "skills_by_platform")

        li_data = res.get("linkedin", {})
        ind_data = res.get("indeed", {})

        self.assertIn("35 distinct codes", li_data.get("granularity", ""))
        self.assertIn("464 distinct tools", ind_data.get("granularity", ""))

        self.assertEqual(li_data["total_postings"], 123835)
        self.assertEqual(ind_data["total_postings"], 5715)

        # LinkedIn skills should be broad disciplines
        li_skills = [s["skill"] for s in li_data.get("skills", [])]
        self.assertIn("Information Technology", li_skills)

        # Indeed skills should be technical tools
        ind_skills = [s["skill"] for s in ind_data.get("skills", [])]
        self.assertTrue(any(tool in ind_skills for tool in ["Python", "SQL", "Machine Learning", "R"]))

        # Cross-platform taxonomy warning
        self.assertIn("Taxonomy Warning", res.get("cross_platform_taxonomy_warning", ""))

    # -------------------------------------------------------------------------
    # 7. Cross-Platform Shared Employers Overlap
    # -------------------------------------------------------------------------
    def test_shared_employers_overlap(self):
        """Verify the exact 570 shared employers intersection and top rankings."""
        res = self.service.get_shared_employers_summary(limit=10)
        self.assertEqual(res.get("operation"), "shared_employers_summary")

        self.assertEqual(res["distinct_linkedin_employers"], 24415)
        self.assertEqual(res["distinct_indeed_employers"], 2231)
        self.assertEqual(res["shared_employers_count"], 570)
        self.assertEqual(res["shared_overlap_pct_indeed"], 25.55)
        self.assertEqual(res["shared_overlap_pct_linkedin"], 2.33)

        top_emps = res.get("top_shared_employers", [])
        self.assertGreaterEqual(len(top_emps), 5)

        # Top employer is Capital One
        cap_one = top_emps[0]
        self.assertEqual(cap_one["company_name"], "Capital One")
        self.assertEqual(cap_one["total_postings"], 550)
        self.assertEqual(cap_one["linkedin_postings"], 496)
        self.assertEqual(cap_one["indeed_postings"], 54)

    # -------------------------------------------------------------------------
    # 8. Role Category Specialization Comparison
    # -------------------------------------------------------------------------
    def test_role_category_distribution(self):
        """Verify Indeed 100% data roles vs LinkedIn broad market distribution."""
        res = self.service.get_platform_role_distribution()
        self.assertEqual(res.get("operation"), "platform_role_distribution")

        categories = {c["role_category"]: c for c in res.get("categories", [])}

        # Indeed data roles sum to 5,715
        ind_ds = categories.get("Data Scientist", {}).get("indeed_postings", 0)
        ind_da = categories.get("Data Analyst", {}).get("indeed_postings", 0)
        ind_de = categories.get("Data Engineer", {}).get("indeed_postings", 0)
        self.assertEqual(ind_ds, 2543)
        self.assertEqual(ind_da, 1793)
        self.assertEqual(ind_de, 1379)
        self.assertEqual(ind_ds + ind_da + ind_de, 5715)

        # Confirm Indeed has 0 postings in non-data roles
        self.assertEqual(categories.get("Sales", {}).get("indeed_postings", 0), 0)
        self.assertEqual(categories.get("Healthcare", {}).get("indeed_postings", 0), 0)
        self.assertEqual(categories.get("Other", {}).get("indeed_postings", 0), 0)

        # Confirm LinkedIn has broad market presence
        self.assertGreater(categories.get("Other", {}).get("linkedin_postings", 0), 90000)
        self.assertGreater(categories.get("Sales", {}).get("linkedin_postings", 0), 9000)
        self.assertGreater(categories.get("Healthcare", {}).get("linkedin_postings", 0), 8000)

    # -------------------------------------------------------------------------
    # 9. Input Validation & Edge Case Handling
    # -------------------------------------------------------------------------
    def test_invalid_inputs_and_edge_cases(self):
        """Verify that service methods reject invalid inputs gracefully."""
        with self.assertRaises(ValueError):
            self.service.get_shared_employers_summary(limit=0)

        with self.assertRaises(ValueError):
            self.service.get_shared_employers_summary(limit=-5)

        with self.assertRaises(ValueError):
            self.service.get_shared_employers_summary(limit="ten")  # type: ignore

    # -------------------------------------------------------------------------
    # 10. UI Plot Builders Safety
    # -------------------------------------------------------------------------
    def test_plot_builders_safety(self):
        """Verify that UI chart builders handle empty and none inputs without raising exceptions."""
        fig_empty1 = create_grouped_bar_chart([], [], [])
        self.assertIsNotNone(fig_empty1)

        fig_empty2 = create_shared_employers_chart([])
        self.assertIsNotNone(fig_empty2)

        fig_empty3 = create_platform_salary_bucket_chart([])
        self.assertIsNotNone(fig_empty3)

        fig_empty4 = create_platform_comparison_chart(None)
        self.assertIsNotNone(fig_empty4)


if __name__ == "__main__":
    unittest.main()
