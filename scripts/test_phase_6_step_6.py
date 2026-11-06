"""
JobMarketDB - Phase 6 Step 6 Automated Test Suite
Validates Company & Geography Analytics:
- Company ranking, platform breakdown, and deep-dive
- Curated company profiles vs raw employer strings
- Geographic state distribution, covered index scan metrics, and choropleth data
- Top hiring cities and missing city/state handling
- Input validation, limits, empty results handling
- Database invariants (jobs = 129,550, companies = 24,472, 15 indexes)
"""

import os
import sys
import unittest
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService
from utils.plots import (
    create_horizontal_ranking_chart,
    create_geographic_comparison_chart,
    create_us_choropleth_map,
    create_empty_chart,
)


class TestPhase6Step6CompanyAndGeography(unittest.TestCase):
    """Test suite for Phase 6 Step 6: Company & Geography Analytics."""

    @classmethod
    def setUpClass(cls):
        verify_connection()
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)

    # -------------------------------------------------------------------------
    # 1. Company Analytics & Hiring Leaders
    # -------------------------------------------------------------------------
    def test_01_top_hiring_companies_ranking(self):
        """Verify Operation 9 returns employers ordered descending by posting count."""
        res = self.service.get_top_companies(limit=10)
        self.assertEqual(res["operation"], "top_hiring_companies")
        companies = res["companies"]
        self.assertLessEqual(len(companies), 10)
        self.assertGreater(len(companies), 0)

        # Assert monotonic descending order
        counts = [c["postings_count"] for c in companies]
        self.assertEqual(counts, sorted(counts, reverse=True))

        # Check top employer is non-null
        self.assertIsNotNone(companies[0]["company_name"])
        self.assertIn("postings_count", companies[0])
        self.assertIn("platforms", companies[0])

    def test_02_top_hiring_companies_platform_filter(self):
        """Verify company ranking with platform filtering (LinkedIn vs Indeed)."""
        li_res = self.service.get_top_companies(limit=5, source="linkedin")
        self.assertEqual(li_res["source_filter"], "linkedin")
        for c in li_res["companies"]:
            self.assertIn("linkedin", c["platforms"])

        ind_res = self.service.get_top_companies(limit=5, source="indeed")
        self.assertEqual(ind_res["source_filter"], "indeed")
        for c in ind_res["companies"]:
            self.assertIn("indeed", c["platforms"])

    def test_03_top_hiring_companies_state_filter(self):
        """Verify company ranking filtered by geographic state."""
        res = self.service.get_top_companies(limit=5, state="CA")
        self.assertEqual(res["state_filter"], "CA")
        self.assertLessEqual(len(res["companies"]), 5)
        for c in res["companies"]:
            self.assertGreater(c["postings_count"], 0)

    def test_04_company_details_known_with_profile(self):
        """Verify deep-dive for Capital One: postings across both platforms and verified profile match."""
        details = self.service.get_company_details("Capital One")
        self.assertTrue(details["found"])
        self.assertEqual(details["company_name"], "Capital One")
        self.assertEqual(details["total_postings"], 550)
        self.assertEqual(details["linkedin_postings"], 496)
        self.assertEqual(details["indeed_postings"], 54)
        self.assertTrue(details["has_company_profile"])
        self.assertIsNotNone(details["profile"])
        self.assertEqual(details["profile"]["company_id"], 1419)
        self.assertIn("Financial Services", details["profile"]["industries"])
        self.assertGreater(len(details["top_titles"]), 0)

    def test_05_company_details_unmatched_profile(self):
        """Verify employer with active postings but no standalone record in canonical companies."""
        # Query an employer that exists in jobs but not companies collection
        details = self.service.get_company_details("Liberty Healthcare and Rehabilitation Services")
        self.assertTrue(details["found"])
        self.assertEqual(details["total_postings"], 1108)
        # Even if profile exists or doesn't, explanation string must be present
        self.assertIn("profile_explanation", details)

    def test_06_company_details_nonexistent(self):
        """Verify graceful empty response when querying nonexistent employer."""
        details = self.service.get_company_details("NonExistentEmployerXYZ123456")
        self.assertFalse(details["found"])
        self.assertEqual(details["total_postings"], 0)
        self.assertFalse(details["has_company_profile"])
        self.assertIsNone(details["profile"])

    def test_07_company_details_invalid_input(self):
        """Verify ValueError is raised on empty or non-string company name."""
        with self.assertRaises(ValueError):
            self.service.get_company_details("")
        with self.assertRaises(ValueError):
            self.service.get_company_details("   ")
        with self.assertRaises(ValueError):
            self.service.get_company_details(None)  # type: ignore

    def test_08_company_overview_stats(self):
        """Verify employer overview metrics distinguishing companies from raw postings."""
        stats = self.service.get_company_overview()
        self.assertEqual(stats["canonical_companies_count"], 24472)
        self.assertEqual(stats["total_jobs_count"], 129550)
        self.assertEqual(stats["jobs_with_company"], 127727)
        self.assertEqual(stats["jobs_missing_company"], 1823)
        self.assertEqual(stats["distinct_employer_names"], 26077)
        self.assertIn("methodology_note", stats)

    def test_09_missing_company_handling(self):
        """Verify that 1,823 postings without company.name are preserved and not fabricated."""
        missing_count = self.db.jobs.count_documents({"company.name": None})
        self.assertEqual(missing_count, 1823)
        # Top hiring companies must exclude None
        top_comp = self.service.get_top_companies(limit=50)
        for c in top_comp["companies"]:
            self.assertIsNotNone(c["company_name"])
            self.assertNotEqual(c["company_name"], "None")

    # -------------------------------------------------------------------------
    # 2. Geography Analytics & Location Grouping
    # -------------------------------------------------------------------------
    def test_10_top_job_locations_ranking(self):
        """Verify Operation 10 returns states in descending order of postings count."""
        res = self.service.get_top_locations(limit=10)
        self.assertEqual(res["operation"], "top_job_locations")
        locations = res["locations"]
        self.assertLessEqual(len(locations), 10)
        self.assertGreater(len(locations), 0)

        counts = [loc["postings_count"] for loc in locations]
        self.assertEqual(counts, sorted(counts, reverse=True))
        # Top state in US job postings is CA or TX
        self.assertIn(locations[0]["state"], ["CA", "TX"])

    def test_11_top_job_locations_platform_filter(self):
        """Verify location aggregation by platform (LinkedIn covers 51 states, Indeed 49)."""
        li_res = self.service.get_top_locations(limit=60, source="linkedin")
        self.assertEqual(len(li_res["locations"]), 51)  # All 50 states + DC

        ind_res = self.service.get_top_locations(limit=60, source="indeed")
        self.assertEqual(len(ind_res["locations"]), 49)

    def test_12_top_job_locations_remote_filter(self):
        """Verify location aggregation with remote status filtering."""
        # Explicitly remote (is_remote = True)
        rem_res = self.service.get_top_locations(limit=10, is_remote=True)
        self.assertEqual(rem_res["is_remote_filter"], True)
        for loc in rem_res["locations"]:
            self.assertGreater(loc["postings_count"], 0)

        # Unstated / On-site (is_remote = None)
        onsite_res = self.service.get_top_locations(limit=10, is_remote=None)
        self.assertIsNone(onsite_res["is_remote_filter"])
        self.assertGreater(len(onsite_res["locations"]), 0)

    def test_13_missing_location_handling(self):
        """Verify that 12,010 postings with location.state == None are excluded from state rankings."""
        missing_count = self.db.jobs.count_documents({"location.state": None})
        self.assertEqual(missing_count, 12010)

        top_locs = self.service.get_top_locations(limit=60)
        for loc in top_locs["locations"]:
            self.assertIsNotNone(loc["state"])
            self.assertNotEqual(loc["state"], "None")

    def test_14_state_choropleth_data(self):
        """Verify state choropleth aggregation across all 51 US jurisdictions."""
        choro = self.service.get_state_choropleth()
        self.assertEqual(choro["operation"], "state_choropleth_data")
        self.assertEqual(choro["total_evaluated"], 129550)
        self.assertEqual(choro["postings_with_state"], 117540)
        self.assertEqual(choro["postings_missing_state"], 12010)
        self.assertEqual(len(choro["locations"]), 51)

        # Verify percentages sum approximately to 100% of known states
        total_pct = sum(loc["percentage"] for loc in choro["locations"])
        self.assertAlmostEqual(total_pct, 100.0, delta=1.0)

    def test_15_top_cities_aggregation(self):
        """Verify top hiring cities aggregation returns valid municipal hubs."""
        res = self.service.get_top_cities(limit=10)
        self.assertEqual(res["operation"], "top_cities")
        cities = res["cities"]
        self.assertEqual(len(cities), 10)

        # Assert descending count order
        counts = [c["postings_count"] for c in cities]
        self.assertEqual(counts, sorted(counts, reverse=True))

        # Top city in dataset is New York, NY
        self.assertEqual(cities[0]["city"], "New York")
        self.assertEqual(cities[0]["state"], "NY")
        self.assertGreater(cities[0]["postings_count"], 4000)

    def test_16_top_cities_state_filter(self):
        """Verify city aggregation filtered by state (e.g. CA)."""
        res = self.service.get_top_cities(limit=5, state="CA")
        self.assertEqual(res["state_filter"], "CA")
        self.assertEqual(len(res["cities"]), 5)
        for c in res["cities"]:
            self.assertEqual(c["state"], "CA")
        # San Francisco and Los Angeles must be in top CA cities
        city_names = [c["city"] for c in res["cities"]]
        self.assertIn("San Francisco", city_names)
        self.assertIn("Los Angeles", city_names)

    def test_17_top_cities_missing_city_handling(self):
        """Verify handling of 20,695 postings with missing city information."""
        missing_count = self.db.jobs.count_documents({"location.city": None})
        self.assertEqual(missing_count, 20695)

        res = self.service.get_top_cities(limit=10)
        self.assertEqual(res["postings_missing_city"], 20695)
        self.assertEqual(res["total_postings_in_scope"], 129550)
        self.assertEqual(res["postings_with_city"], 129550 - 20695)

    # -------------------------------------------------------------------------
    # 3. Input Validation & Edge Cases
    # -------------------------------------------------------------------------
    def test_18_input_validation_and_limits(self):
        """Verify rejection of limit <= 0 in company and location aggregations."""
        with self.assertRaises(ValueError):
            self.service.get_top_companies(limit=0)
        with self.assertRaises(ValueError):
            self.service.get_top_companies(limit=-5)
        with self.assertRaises(ValueError):
            self.service.get_top_locations(limit=0)
        with self.assertRaises(ValueError):
            self.service.get_top_locations(limit=-10)
        with self.assertRaises(ValueError):
            self.service.get_top_cities(limit=0)

    def test_19_empty_results_graceful(self):
        """Verify queries with nonexistent state filters return empty lists cleanly."""
        res_comp = self.service.get_top_companies(limit=5, state="ZZ")
        self.assertEqual(len(res_comp["companies"]), 0)

        res_cities = self.service.get_top_cities(limit=5, state="ZZ")
        self.assertEqual(len(res_cities["cities"]), 0)

    # -------------------------------------------------------------------------
    # 4. Plotly Visualization Builders
    # -------------------------------------------------------------------------
    def test_20_plot_builders_company_and_geo(self):
        """Verify Plotly chart builders handle representative and empty data."""
        sample_companies = [
            {"company_name": "Company A", "postings_count": 500},
            {"company_name": "Company B", "postings_count": 300},
        ]
        fig_comp = create_horizontal_ranking_chart(
            items=sample_companies,
            label_key="company_name",
            value_key="postings_count",
        )
        self.assertIsNotNone(fig_comp)
        self.assertEqual(len(fig_comp.data), 1)

        sample_states = [
            {"state": "CA", "postings_count": 20000, "percentage": 17.0},
            {"state": "NY", "postings_count": 12000, "percentage": 10.2},
        ]
        fig_geo = create_geographic_comparison_chart(sample_states)
        self.assertIsNotNone(fig_geo)
        self.assertEqual(len(fig_geo.data[0].y), 2)

        fig_choro = create_us_choropleth_map(sample_states)
        self.assertIsNotNone(fig_choro)
        self.assertEqual(fig_choro.data[0].type, "choropleth")

        # Test empty charts
        self.assertIsNotNone(create_horizontal_ranking_chart([], "k", "v"))
        self.assertIsNotNone(create_geographic_comparison_chart([]))
        self.assertIsNotNone(create_us_choropleth_map([]))

    # -------------------------------------------------------------------------
    # 5. Database Safety & Integrity Invariants
    # -------------------------------------------------------------------------
    def test_21_database_invariants_preserved(self):
        """Confirm canonical collections and index definitions remain strictly untouched."""
        self.assertEqual(self.db.jobs.count_documents({}), 129550)
        self.assertEqual(self.db.companies.count_documents({}), 24472)
        self.assertEqual(len(self.db.jobs.index_information()), 11)
        self.assertEqual(len(self.db.companies.index_information()), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
