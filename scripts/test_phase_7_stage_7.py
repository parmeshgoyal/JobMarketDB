"""
JobMarketDB - Phase 7 Stage 7 Unit & Integration Test Suite
Validates Platform Comparison (pages/5_Platform_Comparison.py) data loaders,
volume reconciliation, salary source-method validation, skills taxonomy separation,
shared employer overlap, remote tri-state semantics, geographic completeness, and database invariants.
"""

import py_compile
import unittest
from typing import Any, Dict

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService


class TestPhase7Stage7PlatformComparison(unittest.TestCase):
    """Stage 7 unit and integration test suite for Platform Comparison (LinkedIn vs Indeed)."""

    @classmethod
    def setUpClass(cls):
        assert verify_connection(timeout_ms=3000), "MongoDB Community Server must be active"
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)
        cls.comparison = cls.service.compare_platforms()
        cls.completeness = cls.service.get_platform_field_completeness()
        cls.salary_buckets = cls.service.get_platform_salary_bucket_comparison()
        cls.shared_employers = cls.service.get_shared_employers_summary(limit=10)
        cls.skills = cls.service.get_skills_by_platform(limit=10)

    def test_01_syntax_and_compilation(self):
        """Verifies pages/5_Platform_Comparison.py compiles cleanly without syntax errors."""
        try:
            py_compile.compile("pages/5_Platform_Comparison.py", doraise=True)
            compiled = True
        except Exception as exc:
            compiled = False
            self.fail(f"pages/5_Platform_Comparison.py failed compilation: {exc}")
        self.assertTrue(compiled)

    def test_02_database_invariants(self):
        """Verifies canonical collections and indexes remain completely unmodified."""
        jobs_count = self.db.jobs.count_documents({})
        companies_count = self.db.companies.count_documents({})
        self.assertEqual(jobs_count, 129550, "jobs collection must have exactly 129,550 documents")
        self.assertEqual(companies_count, 24472, "companies collection must have exactly 24,472 documents")

        job_indexes = list(self.db.jobs.list_indexes())
        comp_indexes = list(self.db.companies.list_indexes())
        self.assertEqual(len(job_indexes), 11, "jobs must have exactly 11 indexes")
        self.assertEqual(len(comp_indexes), 4, "companies must have exactly 4 indexes")

    def test_03_posting_volume_reconciliation(self):
        """Verifies volume reconciliation across platforms matches ground truth."""
        li_vol = self.comparison["platforms"]["linkedin"]["total_postings"]
        ind_vol = self.comparison["platforms"]["indeed"]["total_postings"]
        total_vol = self.completeness["total_jobs"]

        self.assertEqual(li_vol, 123835)
        self.assertEqual(ind_vol, 5715)
        self.assertEqual(total_vol, 129550)
        self.assertEqual(li_vol + ind_vol, total_vol)

        pct_li = li_vol / total_vol * 100
        pct_ind = ind_vol / total_vol * 100
        self.assertAlmostEqual(pct_li, 95.59, places=2)
        self.assertAlmostEqual(pct_ind, 4.41, places=2)

    def test_04_salary_source_method_validation(self):
        """Verifies platform-specific salary definitions and central tendency metrics."""
        li_metrics = self.salary_buckets["linkedin_metrics"]
        ind_metrics = self.salary_buckets["indeed_metrics"]

        # LinkedIn: Continuous Annualized Compensation
        self.assertEqual(li_metrics["coverage_count"], 36059)
        self.assertEqual(li_metrics["adjusted_postings_count"], 36021)
        self.assertEqual(li_metrics["outliers_count"], 38)
        self.assertAlmostEqual(li_metrics["adjusted_mean"], 95515.00, places=2)
        self.assertAlmostEqual(li_metrics["median"], 81375.00, places=2)

        # Indeed: Derived Search-Band Midpoint
        self.assertEqual(ind_metrics["coverage_count"], 5715)
        self.assertAlmostEqual(ind_metrics["mean"], 116501.31, places=2)
        self.assertAlmostEqual(ind_metrics["median"], 110000.00, places=2)

        # Indeed normalized annual must be 100% null
        ind_norm_count = self.db.jobs.count_documents({
            "source": "indeed",
            "salary.normalized_annual": {"$ne": None},
        })
        self.assertEqual(ind_norm_count, 0, "Indeed normalized annual salary must be strictly 0")

    def test_05_skills_taxonomy_separation(self):
        """Verifies distinct taxonomy scopes: LinkedIn 35 domains vs Indeed 464 tools."""
        li_skills = self.skills["linkedin"]["skills"]
        ind_skills = self.skills["indeed"]["skills"]

        self.assertTrue(len(li_skills) > 0)
        self.assertTrue(len(ind_skills) > 0)

        # LinkedIn top skill is Information Technology (broad functional domain)
        self.assertEqual(li_skills[0]["skill"], "Information Technology")

        # Indeed top skill is Python or SQL (granular technical tool)
        self.assertIn(ind_skills[0]["skill"], ["Python", "SQL"])

        # Count total distinct skills in database per platform
        li_distinct_skills = len(self.db.jobs.distinct("skills", {"source": "linkedin"}))
        ind_distinct_skills = len(self.db.jobs.distinct("skills", {"source": "indeed"}))
        self.assertEqual(li_distinct_skills, 35, "LinkedIn must have exactly 35 distinct functional domains")
        self.assertEqual(ind_distinct_skills, 464, "Indeed must have exactly 464 distinct technical tools")

    def test_06_shared_employer_validation(self):
        """Verifies cross-platform employer overlap metrics."""
        self.assertEqual(self.shared_employers["shared_employers_count"], 570)
        self.assertEqual(self.shared_employers["distinct_linkedin_employers"], 24415)
        self.assertEqual(self.shared_employers["distinct_indeed_employers"], 2231)

        # Top shared employer must be Capital One with 550 postings
        top_emp = self.shared_employers["top_shared_employers"][0]
        self.assertEqual(top_emp["company_name"], "Capital One")
        self.assertEqual(top_emp["total_postings"], 550)
        self.assertEqual(top_emp["linkedin_postings"], 496)
        self.assertEqual(top_emp["indeed_postings"], 54)

    def test_07_remote_tristate_validation(self):
        """Verifies tri-state remote work semantics across platforms."""
        li_rem = self.comparison["platforms"]["linkedin"]["remote_work_breakdown"]
        ind_rem = self.comparison["platforms"]["indeed"]["remote_work_breakdown"]

        self.assertEqual(li_rem["explicitly_remote"], 15236)
        self.assertEqual(li_rem["explicitly_on_site"], 0)
        self.assertEqual(li_rem["unknown_unspecified"], 108599)

        self.assertEqual(ind_rem["explicitly_remote"], 0)
        self.assertEqual(ind_rem["explicitly_on_site"], 0)
        self.assertEqual(ind_rem["unknown_unspecified"], 5715)

    def test_08_geographic_field_completeness(self):
        """Verifies state and city field completeness rates per platform."""
        fields_by_name = {f["field"]: f for f in self.completeness["fields"]}

        state_field = fields_by_name["location.state"]
        self.assertEqual(state_field["linkedin_count"], 112159)
        self.assertEqual(state_field["linkedin_missing"], 11676)
        self.assertEqual(state_field["indeed_count"], 5381)
        self.assertEqual(state_field["indeed_missing"], 334)

        city_field = fields_by_name["location.city"]
        self.assertEqual(city_field["linkedin_count"], 108855)
        self.assertEqual(city_field["linkedin_missing"], 14980)
        self.assertEqual(city_field["indeed_count"], 0)
        self.assertEqual(city_field["indeed_missing"], 5715)

    def test_09_salary_buckets_integrity(self):
        """Verifies 6 standardized salary tiers across platforms."""
        buckets = self.salary_buckets["buckets"]
        self.assertEqual(len(buckets), 6, "Must contain exactly 6 salary tiers")
        total_li_bucketed = sum(b["linkedin_count"] for b in buckets)
        total_ind_bucketed = sum(b["indeed_count"] for b in buckets)
        self.assertEqual(total_li_bucketed, 36059)
        self.assertEqual(total_ind_bucketed, 5715)


if __name__ == "__main__":
    unittest.main()

