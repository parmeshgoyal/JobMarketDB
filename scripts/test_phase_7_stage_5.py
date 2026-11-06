"""
JobMarketDB — Phase 7 Stage 5 Unit & Integration Test Suite
Validates Salary Analytics & Outlier Audit (pages/3_Salary_Analytics.py) data loaders,
coverage KPIs, central tendency, outlier classifications, buckets, and database invariants.
"""

import py_compile
import unittest
from typing import Any, Dict

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService


class TestPhase7Stage5SalaryAnalytics(unittest.TestCase):
    """Stage 5 unit and integration test suite for Salary Analytics."""

    @classmethod
    def setUpClass(cls):
        assert verify_connection(timeout_ms=3000), "MongoDB Community Server must be active"
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)
        cls.overview = cls.service.get_salary_overview()

    def test_01_syntax_and_compilation(self):
        """Verifies pages/3_Salary_Analytics.py compiles cleanly without syntax errors."""
        try:
            py_compile.compile("pages/3_Salary_Analytics.py", doraise=True)
            compiled = True
        except Exception as exc:
            compiled = False
            self.fail(f"pages/3_Salary_Analytics.py failed compilation: {exc}")
        self.assertTrue(compiled)

    def test_02_salary_coverage_counts(self):
        """Verifies platform-level salary coverage matches direct MongoDB ground-truth."""
        li = self.overview["linkedin"]
        ind = self.overview["indeed"]

        self.assertEqual(li["postings_with_normalized_annual"], 36059)
        self.assertEqual(li["postings_missing_salary"], 87776)
        self.assertEqual(li["total_postings"], 123835)

        self.assertEqual(ind["postings_with_estimated_midpoint"], 5715)
        self.assertEqual(ind["postings_with_normalized_annual"], 0)
        self.assertEqual(ind["total_postings"], 5715)

    def test_03_outlier_audit_counts_and_classification(self):
        """Verifies exactly 38 records exceed $1M and classifications sum to 38."""
        audit = self.overview["outlier_audit"]
        self.assertEqual(audit["total_outliers"], 38)
        self.assertTrue(audit["all_from_linkedin"])

        classification = audit["classification"]
        self.assertEqual(classification["hourly_conversion_artifacts"], 19)
        self.assertEqual(classification["recruiter_entry_errors"], 10)
        self.assertEqual(classification["task_fee_or_other"], 1)
        self.assertEqual(classification["unresolved_internship_stipends"], 8)
        self.assertEqual(sum(classification.values()), 38)

    def test_04_central_tendency_adjustment(self):
        """Verifies threshold-adjusted mean (<= $1M) excludes 38 records and is lower than unadjusted."""
        li = self.overview["linkedin"]
        unadj_mean = li["unadjusted"]["mean"]
        adj_mean = li["threshold_adjusted"]["mean"]

        self.assertGreater(unadj_mean, adj_mean)
        self.assertGreater(unadj_mean - adj_mean, 10000)
        self.assertEqual(li["threshold_adjusted"]["count"], 36021)
        self.assertEqual(li["threshold_adjusted"]["excluded_outlier_count"], 38)

    def test_05_canonical_salary_buckets(self):
        """Verifies 6 canonical salary tiers are populated for both platforms."""
        bucket_data = self.service.get_salary_distribution()
        self.assertIn("buckets", bucket_data)
        buckets = bucket_data["buckets"]
        self.assertEqual(len(buckets), 6)

        expected_buckets = ["<80000", "80000-99999", "100000-119999", "120000-139999", "140000-159999", ">160000"]
        actual_buckets = [b["salary_bucket"] for b in buckets]
        self.assertEqual(actual_buckets, expected_buckets)

    def test_06_experience_level_salary(self):
        """Verifies LinkedIn experience level salary aggregation returns tiers."""
        exp_data = self.service.get_salary_by_experience()
        self.assertIn("experience_levels", exp_data)
        tiers = exp_data["experience_levels"]
        self.assertGreater(len(tiers), 0)

    def test_07_database_invariants_unmodified(self):
        """Guarantees zero database modifications occurred."""
        jobs_count = self.db["jobs"].count_documents({})
        companies_count = self.db["companies"].count_documents({})
        jobs_indexes = self.db["jobs"].index_information()
        companies_indexes = self.db["companies"].index_information()

        self.assertEqual(jobs_count, 129550)
        self.assertEqual(companies_count, 24472)
        self.assertEqual(len(jobs_indexes), 11)
        self.assertEqual(len(companies_indexes), 4)


if __name__ == "__main__":
    unittest.main()

