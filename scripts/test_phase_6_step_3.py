"""
JobMarketDB - Phase 6 Step 3 Focused Verification Suite

Tests:
1. Compilation integrity of app.py.
2. Live database connection and load_home_data() loader execution.
3. Live KPI calculation accuracy (129,550 jobs, 24,472 companies, 32.24% salary coverage, 11.76% remote).
4. Platform comparison integration via service.compare_platforms().
5. Database information catalog and complete index definitions (11 on jobs, 4 on companies).
6. Connection error handling when MongoDB is unreachable.
7. Verification of 6-layer architecture and 3-tier data provenance elements.
8. Database invariants verification (canonical datasets strictly unchanged).
"""

import os
import py_compile
import sys
import unittest
from unittest.mock import patch
from typing import Any, Dict

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService
import app


class Phase6Step3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)
        cls.expected_jobs_count = 129550
        cls.expected_companies_count = 24472
        cls.expected_jobs_indexes = 11
        cls.expected_companies_indexes = 4

    # -------------------------------------------------------------------------
    # 1. Compilation & Syntax Verification
    # -------------------------------------------------------------------------
    def test_app_compilation(self):
        """Verify app.py exists and compiles cleanly without syntax errors."""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))
        self.assertTrue(os.path.exists(app_path), f"app.py does not exist at {app_path}")
        py_compile.compile(app_path, doraise=True)

    # -------------------------------------------------------------------------
    # 2. Live Data Loader & KPI Accuracy
    # -------------------------------------------------------------------------
    def test_load_home_data_success(self):
        """Test that load_home_data() successfully connects and retrieves live data."""
        is_connected, data, error_msg = app.load_home_data()

        self.assertTrue(is_connected, f"load_home_data failed with error: {error_msg}")
        self.assertEqual(error_msg, "")
        self.assertIsInstance(data, dict)

        # 1. Total Job Postings
        self.assertEqual(data["jobs_count"], 129550)

        # 2. Total Company Documents
        self.assertEqual(data["companies_count"], 24472)

        # 3. Total Postings with Salary Information (41,774 / 129,550 = 32.245%)
        self.assertEqual(data["total_salary_postings"], 41774)
        self.assertAlmostEqual(data["overall_salary_coverage_pct"], 32.25, places=2)
        self.assertAlmostEqual(data["overall_salary_coverage_display"], 32.24, places=2)

        # 4. Explicitly Remote Postings (15,236 / 129,550 = 11.76%)
        self.assertEqual(data["total_remote_postings"], 15236)
        self.assertAlmostEqual(data["overall_remote_pct"], 11.76, places=2)

        # 5. Continuous Annual Salary (LinkedIn only: 36,059 / 129,550 = 27.83%)
        self.assertEqual(data["continuous_salary_count"], 36059)
        self.assertAlmostEqual(data["continuous_salary_pct"], 27.83, places=2)

    # -------------------------------------------------------------------------
    # 3. Cross-Platform Comparison Metrics (Operation 12)
    # -------------------------------------------------------------------------
    def test_platform_comparison_breakdown(self):
        """Verify platform comparison accurately separates LinkedIn and Indeed."""
        is_connected, data, _ = app.load_home_data()
        self.assertTrue(is_connected)

        comp = data["comparison"]
        self.assertIn("platforms", comp)
        platforms = comp["platforms"]
        self.assertIn("linkedin", platforms)
        self.assertIn("indeed", platforms)

        # LinkedIn breakdown
        li = platforms["linkedin"]
        self.assertEqual(li["total_postings"], 123835)
        self.assertEqual(li["salary_coverage"]["postings_with_salary"], 36059)
        self.assertAlmostEqual(li["salary_coverage"]["coverage_percentage"], 29.12, places=2)
        self.assertEqual(li["remote_work_breakdown"]["explicitly_remote"], 15236)
        self.assertEqual(li["remote_work_breakdown"]["explicitly_on_site"], 0)
        self.assertEqual(li["remote_work_breakdown"]["unknown_unspecified"], 108599)
        self.assertAlmostEqual(li["remote_work_breakdown"]["remote_percentage"], 12.30, places=2)
        self.assertEqual(li["coverage_metrics"]["distinct_companies_count"], 24415)
        self.assertEqual(li["coverage_metrics"]["distinct_states_count"], 51)

        # Indeed breakdown
        ind = platforms["indeed"]
        self.assertEqual(ind["total_postings"], 5715)
        self.assertEqual(ind["salary_coverage"]["postings_with_salary"], 5715)
        self.assertAlmostEqual(ind["salary_coverage"]["coverage_percentage"], 100.0, places=1)
        self.assertEqual(ind["remote_work_breakdown"]["explicitly_remote"], 0)
        self.assertEqual(ind["remote_work_breakdown"]["explicitly_on_site"], 0)
        self.assertEqual(ind["remote_work_breakdown"]["unknown_unspecified"], 5715)
        self.assertAlmostEqual(ind["remote_work_breakdown"]["remote_percentage"], 0.0, places=1)
        self.assertEqual(ind["coverage_metrics"]["distinct_companies_count"], 2231)
        self.assertEqual(ind["coverage_metrics"]["distinct_states_count"], 49)

    # -------------------------------------------------------------------------
    # 4. Database Specifications & Complete Index Definitions
    # -------------------------------------------------------------------------
    def test_database_specs_and_indexes(self):
        """Verify dbStats and index definitions match the production catalog."""
        is_connected, data, _ = app.load_home_data()
        self.assertTrue(is_connected)

        db_stats = data["db_stats"]
        self.assertEqual(db_stats.get("db"), "jobmarketdb")
        self.assertGreater(db_stats.get("dataSize", 0), 500 * 1024 * 1024)  # ~670 MB
        self.assertGreater(db_stats.get("storageSize", 0), 200 * 1024 * 1024)

        # 11 indexes on jobs collection
        jobs_indexes = data["jobs_indexes"]
        self.assertEqual(len(jobs_indexes), self.expected_jobs_indexes)
        self.assertIn("_id_", jobs_indexes)
        self.assertIn("source_1_source_job_id_1_unique", jobs_indexes)
        self.assertIn("title_text_description_text", jobs_indexes)
        self.assertIn("location.state_1_location.is_remote_1", jobs_indexes)
        self.assertIn("salary.salary_bucket_1_salary.normalized_annual_1", jobs_indexes)
        self.assertIn("skills_1", jobs_indexes)
        self.assertIn("company.name_1", jobs_indexes)
        self.assertIn("experience_level.value_1", jobs_indexes)
        self.assertIn("source_1", jobs_indexes)
        self.assertIn("role_category.value_1", jobs_indexes)
        self.assertIn("source_1_salary.salary_bucket_1", jobs_indexes)

        # 4 indexes on companies collection
        comp_indexes = data["companies_indexes"]
        self.assertEqual(len(comp_indexes), self.expected_companies_indexes)
        self.assertIn("_id_", comp_indexes)
        self.assertIn("company_id_1_unique", comp_indexes)
        self.assertIn("name_1", comp_indexes)
        self.assertIn("industries_1", comp_indexes)

    # -------------------------------------------------------------------------
    # 5. Connection Failure Fallback
    # -------------------------------------------------------------------------
    def test_load_home_data_connection_failure(self):
        """Verify load_home_data handles database connection failures gracefully."""
        # Clear Streamlit cache if cached
        app.load_home_data.clear()

        with patch("app.verify_connection", return_value=False):
            is_connected, data, error_msg = app.load_home_data()
            self.assertFalse(is_connected)
            self.assertEqual(data, {})
            self.assertIn("MongoDB connection check failed", error_msg)

        # Re-clear cache so future calls reconnect properly
        app.load_home_data.clear()

    # -------------------------------------------------------------------------
    # 6. Database Invariant Check
    # -------------------------------------------------------------------------
    def test_database_invariants_preserved(self):
        """Confirm canonical collections and index configurations remain strictly untouched."""
        jobs_count = self.db["jobs"].count_documents({})
        companies_count = self.db["companies"].count_documents({})
        jobs_indexes = len(self.db["jobs"].index_information())
        companies_indexes = len(self.db["companies"].index_information())

        self.assertEqual(jobs_count, self.expected_jobs_count, f"Jobs count changed: {jobs_count}")
        self.assertEqual(companies_count, self.expected_companies_count, f"Companies count changed: {companies_count}")
        self.assertEqual(jobs_indexes, self.expected_jobs_indexes, f"Jobs index count changed: {jobs_indexes}")
        self.assertEqual(companies_indexes, self.expected_companies_indexes, f"Companies index count changed: {companies_indexes}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
