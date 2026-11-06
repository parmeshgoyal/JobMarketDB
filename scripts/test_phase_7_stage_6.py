"""
JobMarketDB - Phase 7 Stage 6 Unit & Integration Test Suite
Validates Company & Geography Intelligence (pages/4_Company_and_Geography.py) data loaders,
coverage KPIs, company profile deep-dives, state choropleth distributions, city completeness,
and database invariants.
"""

import py_compile
import unittest
from typing import Any, Dict

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService


class TestPhase7Stage6CompanyGeography(unittest.TestCase):
    """Stage 6 unit and integration test suite for Company & Geography Analytics."""

    @classmethod
    def setUpClass(cls):
        assert verify_connection(timeout_ms=3000), "MongoDB Community Server must be active"
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)
        cls.overview = cls.service.get_company_overview()

    def test_01_syntax_and_compilation(self):
        """Verifies pages/4_Company_and_Geography.py compiles cleanly without syntax errors."""
        try:
            py_compile.compile("pages/4_Company_and_Geography.py", doraise=True)
            compiled = True
        except Exception as exc:
            compiled = False
            self.fail(f"pages/4_Company_and_Geography.py failed compilation: {exc}")
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

    def test_03_company_overview_metrics(self):
        """Verifies company overview metrics match verified ground truth."""
        self.assertEqual(self.overview["canonical_companies_count"], 24472)
        self.assertEqual(self.overview["total_jobs_count"], 129550)
        self.assertEqual(self.overview["jobs_with_company"], 127727)
        self.assertEqual(self.overview["jobs_missing_company"], 1823)

        # Distinct employer names (non-null = 26,076; raw includes None = 26,077)
        non_null_distinct = len([n for n in self.db.jobs.distinct("company.name") if n is not None])
        self.assertEqual(non_null_distinct, 26076)

    def test_04_linkedin_company_id_coverage(self):
        """Verifies LinkedIn company_id linking to canonical catalog."""
        li_company_id_count = self.db.jobs.count_documents({
            "source": "linkedin",
            "company.company_id": {"$ne": None},
        })
        self.assertEqual(li_company_id_count, 122118, "LinkedIn company_id count must be exactly 122,118")

        ind_company_id_count = self.db.jobs.count_documents({
            "source": "indeed",
            "company.company_id": {"$ne": None},
        })
        self.assertEqual(ind_company_id_count, 0, "Indeed company_id count must be 0")

    def test_05_geographic_state_completeness(self):
        """Verifies state choropleth geographic metrics across 51 jurisdictions."""
        choro = self.service.get_state_choropleth()
        self.assertEqual(choro["total_evaluated"], 129550)
        self.assertEqual(choro["postings_with_state"], 117540)
        self.assertEqual(choro["postings_missing_state"], 12010)
        self.assertEqual(len(choro["locations"]), 51, "Must span exactly 51 jurisdictions (50 states + DC)")

        # Verify top state is CA
        top_state = choro["locations"][0]
        self.assertEqual(top_state["state"], "CA")
        self.assertEqual(top_state["postings_count"], 13892)
        self.assertAlmostEqual(top_state["percentage"], 11.82, places=1)

    def test_06_city_field_completeness_and_rankings(self):
        """Verifies city completeness and verified top municipal hubs."""
        cities_res = self.service.get_top_cities(limit=5)
        self.assertEqual(cities_res["total_postings_in_scope"], 129550)
        self.assertEqual(cities_res["postings_with_city"], 108855)
        self.assertEqual(cities_res["postings_missing_city"], 20695)

        expected_cities = [
            ("New York", 4240),
            ("Chicago", 2033),
            ("Houston", 1986),
            ("Dallas", 1702),
            ("Atlanta", 1362),
        ]
        actual_cities = [(c["city"], c["postings_count"]) for c in cities_res["cities"]]
        self.assertEqual(actual_cities, expected_cities)

    def test_07_top_hiring_companies(self):
        """Verifies top employer rankings across the complete dataset."""
        top_comp = self.service.get_top_companies(limit=5)
        companies = top_comp["companies"]
        self.assertEqual(len(companies), 5)
        self.assertEqual(companies[0]["company_name"], "Liberty Healthcare and Rehabilitation Services")
        self.assertEqual(companies[0]["postings_count"], 1108)
        self.assertEqual(companies[1]["company_name"], "The Job Network")
        self.assertEqual(companies[1]["postings_count"], 1003)
        self.assertEqual(companies[3]["company_name"], "Capital One")
        self.assertEqual(companies[3]["postings_count"], 550)

    def test_08_company_details_deep_dive(self):
        """Verifies deep-dive company lookup and catalog linking."""
        cap_one = self.service.get_company_details("Capital One")
        self.assertTrue(cap_one["found"])
        self.assertTrue(cap_one["has_company_profile"])
        self.assertEqual(cap_one["total_postings"], 550)
        self.assertEqual(cap_one["linkedin_postings"], 496)
        self.assertEqual(cap_one["indeed_postings"], 54)
        self.assertIsNotNone(cap_one.get("profile"))
        self.assertIn("industries", cap_one["profile"])

    def test_09_shared_employers_summary(self):
        """Verifies cross-platform employer overlap summary."""
        shared = self.service.get_shared_employers_summary(limit=5)
        self.assertEqual(shared["shared_employers_count"], 570)
        self.assertEqual(shared["top_shared_employers"][0]["company_name"], "Capital One")
        self.assertEqual(shared["top_shared_employers"][0]["total_postings"], 550)

    def test_10_covered_index_scan(self):
        """Verifies MongoDB covered index scan over location.state_1_location.is_remote_1."""
        pipeline = [
            {"$match": {"location.state": {"$ne": None}}},
            {"$group": {"_id": "$location.state", "count": {"$sum": 1}}},
        ]
        explain_res = self.db.command(
            "explain",
            {"aggregate": "jobs", "pipeline": pipeline, "cursor": {}},
            verbosity="executionStats",
        )
        stages = explain_res.get("stages", [])
        # In MongoDB 9.0 covered index scan, totalDocsExamined is 0
        execution_stats = explain_res.get("executionStats") or {}
        docs_examined = execution_stats.get("totalDocsExamined")
        if docs_examined is None and stages:
            for s in stages:
                if "$cursor" in s:
                    docs_examined = s["$cursor"].get("executionStats", {}).get("totalDocsExamined")
                    break

        if docs_examined is not None:
            self.assertEqual(docs_examined, 0, "State distribution query must be a covered index scan with totalDocsExamined == 0")


if __name__ == "__main__":
    unittest.main()

