"""
JobMarketDB — Phase 7 Stage 9 Final Comprehensive Application Integration Test Suite
Validates:
1. Canonical database counts and index invariants.
2. Cross-page numerical consistency across all 7 pages.
3. Salary reconciliation benchmarks and source separation.
4. Remote-work tri-state semantics and geographic completeness.
5. Skills taxonomy isolation (35 LinkedIn domains vs 464 Indeed tools).
6. Shared employer metrics (570 employers).
7. All 7 page AST compilation and import integrity.
8. Safety policies (local MongoDB only, no Atlas, zero mock data).
"""

import ast
import os
import py_compile
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.connection import get_database, verify_connection, get_connection_config
from analytics.service import JobMarketAnalyticsService


class TestPhase7Stage9ComprehensiveVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert verify_connection(timeout_ms=3000), "Local MongoDB Community Server must be active"
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)
        cls.jobs_col = cls.db.jobs
        cls.companies_col = cls.db.companies
        cls.demo_col = cls.db.demo_postings
        cls.comparison = cls.service.compare_platforms()
        cls.completeness = cls.service.get_platform_field_completeness()
        cls.salary_buckets = cls.service.get_platform_salary_bucket_comparison()
        cls.shared_employers = cls.service.get_shared_employers_summary(limit=1000)
        cls.skills = cls.service.get_skills_by_platform(limit=10)

    # --- 1. Database Invariants ---
    def test_01_canonical_job_count_invariant(self):
        """jobs collection must contain exactly 129,550 documents."""
        count = self.jobs_col.count_documents({})
        self.assertEqual(count, 129550, f"Expected 129,550 jobs, got {count}")

    def test_02_canonical_company_count_invariant(self):
        """companies collection must contain exactly 24,472 documents."""
        count = self.companies_col.count_documents({})
        self.assertEqual(count, 24472, f"Expected 24,472 companies, got {count}")

    def test_03_jobs_index_count_invariant(self):
        """jobs collection must have exactly 11 indexes."""
        indexes = list(self.jobs_col.list_indexes())
        self.assertEqual(len(indexes), 11, f"Expected 11 jobs indexes, got {len(indexes)}")

    def test_04_companies_index_count_invariant(self):
        """companies collection must have exactly 4 indexes."""
        indexes = list(self.companies_col.list_indexes())
        self.assertEqual(len(indexes), 4, f"Expected 4 companies indexes, got {len(indexes)}")

    def test_05_total_production_indexes_invariant(self):
        """Total production indexes across jobs and companies must be exactly 15."""
        total = len(list(self.jobs_col.list_indexes())) + len(list(self.companies_col.list_indexes()))
        self.assertEqual(total, 15, f"Expected 15 total production indexes, got {total}")

    def test_06_sandbox_collection_clean_invariant(self):
        """demo_postings collection must be clean (0 documents)."""
        count = self.demo_col.count_documents({})
        self.assertEqual(count, 0, f"Expected 0 demo_postings documents, got {count}")

    # --- 2. Database Safety & Architecture ---
    def test_07_no_mongodb_atlas_configured(self):
        """Configured MongoDB URI must strictly be localhost, never Atlas or remote."""
        uri, db_name = get_connection_config()
        self.assertNotIn("mongodb+srv://", uri)
        self.assertTrue("localhost" in uri or "127.0.0.1" in uri)
        self.assertEqual(db_name, "jobmarketdb")

    def test_08_no_delete_many_or_drop_in_crud_page(self):
        """CRUD demo page must not use delete_many or drop collection."""
        crud_path = os.path.join(PROJECT_ROOT, "pages", "6_CRUD_Demo.py")
        with open(crud_path, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = ast.parse(content)
        for node in ast.walk(parsed):
            if isinstance(node, ast.Attribute):
                self.assertNotEqual(node.attr, "delete_many", "Forbidden delete_many found in CRUD Demo")
                self.assertNotEqual(node.attr, "drop", "Forbidden drop found in CRUD Demo")

    # --- 3. Platform Distribution Invariants ---
    def test_09_platform_volume_split(self):
        """Platform volume split must be 123,835 LinkedIn vs 5,715 Indeed."""
        li_vol = self.comparison["platforms"]["linkedin"]["total_postings"]
        ind_vol = self.comparison["platforms"]["indeed"]["total_postings"]
        total_vol = self.completeness["total_jobs"]

        self.assertEqual(li_vol, 123835)
        self.assertEqual(ind_vol, 5715)
        self.assertEqual(total_vol, 129550)
        self.assertEqual(li_vol + ind_vol, total_vol)

    # --- 4. Cross-Page Salary Reconciliation Consistency ---
    def test_10_salary_reconciliation_authoritative_benchmarks(self):
        """Salary benchmarks must strictly match authoritative reconciled figures."""
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
        ind_norm_count = self.jobs_col.count_documents({
            "source": "indeed",
            "salary.normalized_annual": {"$ne": None},
        })
        self.assertEqual(ind_norm_count, 0, "Indeed normalized annual salary must be strictly 0")

    # --- 5. Cross-Page Skills Taxonomy Separation ---
    def test_11_skills_taxonomy_counts(self):
        """LinkedIn has 35 functional domains; Indeed has 464 technical tools."""
        li_distinct_skills = len(self.jobs_col.distinct("skills", {"source": "linkedin"}))
        ind_distinct_skills = len(self.jobs_col.distinct("skills", {"source": "indeed"}))
        self.assertEqual(li_distinct_skills, 35, "LinkedIn must have exactly 35 distinct functional domains")
        self.assertEqual(ind_distinct_skills, 464, "Indeed must have exactly 464 distinct technical tools")

    # --- 6. Cross-Page Shared Employers Consistency ---
    def test_12_shared_employers_count(self):
        """Cross-platform shared employers must be exactly 570."""
        self.assertEqual(self.shared_employers["shared_employers_count"], 570)

    # --- 7. Cross-Page Remote-Work Tri-State Consistency ---
    def test_13_remote_work_tri_state_semantics(self):
        """LinkedIn remote: 15,236; LinkedIn null: 108,599; Indeed remote: 0; Indeed null: 5,715."""
        li_remote = self.jobs_col.count_documents({"source": "linkedin", "location.is_remote": True})
        li_null = self.jobs_col.count_documents({"source": "linkedin", "location.is_remote": None})
        li_false = self.jobs_col.count_documents({"source": "linkedin", "location.is_remote": False})
        
        ind_remote = self.jobs_col.count_documents({"source": "indeed", "location.is_remote": True})
        ind_null = self.jobs_col.count_documents({"source": "indeed", "location.is_remote": None})
        ind_false = self.jobs_col.count_documents({"source": "indeed", "location.is_remote": False})

        self.assertEqual(li_remote, 15236)
        self.assertEqual(li_null, 108599)
        self.assertEqual(li_false, 0, "LinkedIn must have 0 explicitly false remote records")

        self.assertEqual(ind_remote, 0)
        self.assertEqual(ind_null, 5715)
        self.assertEqual(ind_false, 0)

    # --- 8. Cross-Page Geographic Completeness ---
    def test_14_geographic_state_city_completeness(self):
        """State: 112,159 LI vs 5,381 Indeed. City: 108,855 LI vs 0 Indeed."""
        li_state = self.jobs_col.count_documents({"source": "linkedin", "location.state": {"$ne": None, "$nin": ["", "Unknown"]}})
        ind_state = self.jobs_col.count_documents({"source": "indeed", "location.state": {"$ne": None, "$nin": ["", "Unknown"]}})
        li_city = self.jobs_col.count_documents({"source": "linkedin", "location.city": {"$ne": None, "$nin": ["", "Unknown"]}})
        ind_city = self.jobs_col.count_documents({"source": "indeed", "location.city": {"$ne": None, "$nin": ["", "Unknown"]}})

        self.assertEqual(li_state, 112159)
        self.assertEqual(ind_state, 5381)
        self.assertEqual(li_city, 108855)
        self.assertEqual(ind_city, 0)

    def test_15_top_job_locations_completeness(self):
        """get_top_locations returns state aggregations."""
        res = self.service.get_top_locations(limit=60)
        locs = res.get("locations", [])
        self.assertTrue(len(locs) >= 50, f"Expected at least 50 state locations, got {len(locs)}")

    # --- 9. All 7 Redesigned Pages AST Compilation ---
    def test_16_all_seven_pages_compile(self):
        """All 7 page Python files must compile cleanly without syntax errors."""
        pages = [
            "app.py",
            "pages/1_Job_Search.py",
            "pages/2_Skills_Analytics.py",
            "pages/3_Salary_Analytics.py",
            "pages/4_Company_and_Geography.py",
            "pages/5_Platform_Comparison.py",
            "pages/6_CRUD_Demo.py",
        ]
        for rel_path in pages:
            full_path = os.path.join(PROJECT_ROOT, rel_path)
            self.assertTrue(os.path.exists(full_path), f"Missing page file: {full_path}")
            try:
                py_compile.compile(full_path, doraise=True)
            except Exception as e:
                self.fail(f"Compilation failed for {rel_path}: {e}")

    # --- 10. Shared Design Tokens and Utilities ---
    def test_17_shared_design_tokens_present(self):
        """style.css must define core Sage & Ivory color tokens."""
        css_path = os.path.join(PROJECT_ROOT, "utils", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        self.assertIn("#FAF8F5", css)  # Warm ivory canvas
        self.assertIn("#1C1F1D", css)  # Deep charcoal
        self.assertIn("#2E3A2D", css)  # Deep olive
        self.assertIn("#6E856C", css)  # Sage green
        self.assertIn("#E2DDD5", css)  # Subtle border

    # --- 11. Plotly Theming Consistency ---
    def test_18_plotly_theme_consistency(self):
        """plots.py must export apply_theme with the Sage & Ivory palette."""
        plots_path = os.path.join(PROJECT_ROOT, "utils", "plots.py")
        with open(plots_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("apply_theme", code)
        self.assertIn("#2E3A2D", code)
        self.assertIn("#6E856C", code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
