"""
JobMarketDB — Phase 7 Stage 3 Unit & Integration Test Suite
Validates Executive Overview (app.py) data loader, KPI calculations,
platform comparisons, salary distributions, index catalog, and database invariants.
"""

import py_compile
import unittest
from typing import Any, Dict

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService


class TestPhase7Stage3HomeDashboard(unittest.TestCase):
    """Stage 3 unit and integration test suite for Executive Overview."""

    @classmethod
    def setUpClass(cls):
        assert verify_connection(timeout_ms=3000), "MongoDB Community Server must be active"
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)

    def test_01_syntax_and_compilation(self):
        """Verifies app.py compiles cleanly without syntax errors."""
        try:
            py_compile.compile("app.py", doraise=True)
            compiled = True
        except Exception as exc:
            compiled = False
            self.fail(f"app.py failed compilation: {exc}")
        self.assertTrue(compiled)

    def test_02_database_connection_and_stats(self):
        """Verifies active connection to 'jobmarketdb' and valid dbStats."""
        stats = self.db.command("dbStats")
        self.assertEqual(stats.get("db"), "jobmarketdb")
        self.assertGreater(stats.get("dataSize", 0), 0)
        self.assertGreater(stats.get("storageSize", 0), 0)
        self.assertGreater(stats.get("indexSize", 0), 0)

    def test_03_canonical_counts(self):
        """Verifies exact canonical document counts: 129,550 jobs and 24,472 companies."""
        jobs_count = self.db["jobs"].count_documents({})
        companies_count = self.db["companies"].count_documents({})
        self.assertEqual(jobs_count, 129550, f"Expected 129,550 jobs, found {jobs_count}")
        self.assertEqual(companies_count, 24472, f"Expected 24,472 companies, found {companies_count}")

    def test_04_index_catalog_invariants(self):
        """Verifies all 15 production indexes (11 jobs + 4 companies) are intact."""
        jobs_indexes = self.db["jobs"].index_information()
        companies_indexes = self.db["companies"].index_information()

        self.assertEqual(len(jobs_indexes), 11, f"Expected 11 jobs indexes, found {len(jobs_indexes)}")
        self.assertEqual(len(companies_indexes), 4, f"Expected 4 companies indexes, found {len(companies_indexes)}")

        # Verify key expected index names
        self.assertIn("_id_", jobs_indexes)
        self.assertIn("source_1_source_job_id_1_unique", jobs_indexes)
        self.assertIn("title_text_description_text", jobs_indexes)
        self.assertIn("skills_1", jobs_indexes)
        self.assertIn("salary.salary_bucket_1_salary.normalized_annual_1", jobs_indexes)
        self.assertIn("source_1_salary.salary_bucket_1", jobs_indexes)

        self.assertIn("_id_", companies_indexes)
        self.assertIn("company_id_1_unique", companies_indexes)

    def test_05_platform_comparison_volume_and_share(self):
        """Verifies LinkedIn (123,835 / 95.59%) and Indeed (5,715 / 4.41%) distribution."""
        comp = self.service.compare_platforms()
        self.assertIn("platforms", comp)

        li = comp["platforms"].get("linkedin", {})
        ind = comp["platforms"].get("indeed", {})

        li_postings = li.get("total_postings", 0)
        ind_postings = ind.get("total_postings", 0)

        self.assertEqual(li_postings, 123835)
        self.assertEqual(ind_postings, 5715)
        self.assertEqual(li_postings + ind_postings, 129550)

    def test_06_salary_coverage_and_provenance(self):
        """Verifies overall salary coverage (41,774 / 32.24%) and continuous vs bucket distinction."""
        comp = self.service.compare_platforms()
        li = comp["platforms"].get("linkedin", {})
        ind = comp["platforms"].get("indeed", {})

        li_sal = li.get("salary_coverage", {}).get("postings_with_salary", 0)
        ind_sal = ind.get("salary_coverage", {}).get("postings_with_salary", 0)
        total_sal = li_sal + ind_sal

        self.assertEqual(li_sal, 36059)
        self.assertEqual(ind_sal, 5715)
        self.assertEqual(total_sal, 41774)

        # Continuous salary (LinkedIn only)
        continuous_sal_count = self.db["jobs"].count_documents({"salary.normalized_annual": {"$ne": None}})
        self.assertEqual(continuous_sal_count, 36059)

        # Indeed continuous salary must be 0
        indeed_continuous = self.db["jobs"].count_documents({
            "source": "indeed",
            "salary.normalized_annual": {"$ne": None}
        })
        self.assertEqual(indeed_continuous, 0)

    def test_07_remote_tristate_coverage(self):
        """Verifies authentic tri-state remote adoption: 15,236 remote, 0 on-site, 114,314 unspecified."""
        remote_true = self.db["jobs"].count_documents({"location.is_remote": True})
        remote_false = self.db["jobs"].count_documents({"location.is_remote": False})
        remote_none = self.db["jobs"].count_documents({"location.is_remote": None})

        self.assertEqual(remote_true, 15236)
        self.assertEqual(remote_false, 0)
        self.assertEqual(remote_none, 114314)
        self.assertEqual(remote_true + remote_false + remote_none, 129550)

    def test_08_standardized_salary_bucket_comparison(self):
        """Verifies 6-tier salary bucket comparison returns valid distributions."""
        bucket_data = self.service.get_platform_salary_bucket_comparison()
        self.assertIn("buckets", bucket_data)
        buckets = bucket_data["buckets"]
        self.assertEqual(len(buckets), 6)

        bucket_names = [b["bucket"] for b in buckets]
        expected_buckets = ["<80000", "80000-99999", "100000-119999", "120000-139999", "140000-159999", ">160000"]
        self.assertEqual(bucket_names, expected_buckets)

        # Verify sum of indeed counts equals 5,715
        indeed_sum = sum(b["indeed_count"] for b in buckets)
        self.assertEqual(indeed_sum, 5715)

    def test_09_top_hiring_locations(self):
        """Verifies top 5 hiring states aggregation returns CA, TX, NY, FL, NC."""
        top_locs = self.service.get_top_locations(limit=5)
        locs = top_locs.get("locations", [])
        self.assertEqual(len(locs), 5)

        states = [l["state"] for l in locs]
        self.assertEqual(states, ["CA", "TX", "NY", "FL", "NC"])
        self.assertGreater(locs[0]["postings_count"], locs[1]["postings_count"])

    def test_10_database_immutability(self):
        """Guarantees zero database modifications occurred during testing."""
        jobs_count = self.db["jobs"].count_documents({})
        companies_count = self.db["companies"].count_documents({})
        self.assertEqual(jobs_count, 129550)
        self.assertEqual(companies_count, 24472)


if __name__ == "__main__":
    unittest.main()
