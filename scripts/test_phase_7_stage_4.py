"""
JobMarketDB — Phase 7 Stage 4 Unit & Integration Test Suite
Validates Skills Intelligence (pages/2_Skills_Analytics.py) data pipelines,
taxonomy isolation, top skills ground-truth, role filtering, and database invariants.
"""

import py_compile
import unittest
from typing import Any, Dict

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService


class TestPhase7Stage4SkillsAnalytics(unittest.TestCase):
    """Stage 4 unit and integration test suite for Skills Intelligence."""

    @classmethod
    def setUpClass(cls):
        assert verify_connection(timeout_ms=3000), "MongoDB Community Server must be active"
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)

    def test_01_syntax_and_compilation(self):
        """Verifies pages/2_Skills_Analytics.py compiles cleanly without syntax errors."""
        try:
            py_compile.compile("pages/2_Skills_Analytics.py", doraise=True)
            compiled = True
        except Exception as exc:
            compiled = False
            self.fail(f"pages/2_Skills_Analytics.py failed compilation: {exc}")
        self.assertTrue(compiled)

    def test_02_platform_skills_isolation(self):
        """Verifies get_skills_by_platform partitions LinkedIn and Indeed strictly."""
        result = self.service.get_skills_by_platform(limit=1)
        self.assertIn("linkedin", result)
        self.assertIn("indeed", result)

        li = result["linkedin"]
        ind = result["indeed"]

        self.assertEqual(li["total_postings"], 123835)
        self.assertEqual(ind["total_postings"], 5715)

        # Check top entities
        self.assertEqual(li["skills"][0]["skill"], "Information Technology")
        self.assertEqual(li["skills"][0]["count"], 25252)
        self.assertAlmostEqual(li["skills"][0]["percentage_of_postings"], 20.39, places=2)

        self.assertEqual(ind["skills"][0]["skill"], "Python")
        self.assertEqual(ind["skills"][0]["count"], 3325)
        self.assertAlmostEqual(ind["skills"][0]["percentage_of_postings"], 58.18, places=2)

    def test_03_indeed_technical_tools_fidelity(self):
        """Verifies Indeed skills aggregation contains technical tools and excludes broad domains."""
        res = self.service.get_top_skills(limit=15, source="indeed")
        self.assertEqual(res["total_postings_evaluated"], 5715)

        tools = [s["skill"] for s in res["skills"]]
        self.assertIn("Python", tools)
        self.assertIn("SQL", tools)
        self.assertIn("Machine Learning", tools)
        self.assertIn("R", tools)

        # Exclude LinkedIn broad domains
        self.assertNotIn("Information Technology", tools)
        self.assertNotIn("Manufacturing", tools)

    def test_04_linkedin_functional_domains_fidelity(self):
        """Verifies LinkedIn skills aggregation contains functional disciplines and excludes tools."""
        res = self.service.get_top_skills(limit=15, source="linkedin")
        self.assertEqual(res["total_postings_evaluated"], 123835)

        domains = [s["skill"] for s in res["skills"]]
        self.assertIn("Information Technology", domains)
        self.assertIn("Sales", domains)
        self.assertIn("Management", domains)

        # Exclude Indeed programming tools
        self.assertNotIn("Python", domains)
        self.assertNotIn("SQL", domains)
        self.assertNotIn("Docker", domains)

    def test_05_role_category_filtering(self):
        """Verifies role category filter modifies skill distribution appropriately."""
        res_ds = self.service.get_top_skills(limit=10, source="indeed", role_category="Data Scientist")
        self.assertGreater(res_ds["total_postings_evaluated"], 0)
        tools_ds = [s["skill"] for s in res_ds["skills"]]
        self.assertIn("Python", tools_ds)

    def test_06_vocabulary_bridge_tokens(self):
        """Verifies that the overlap between LinkedIn and Indeed vocabularies is precisely 4 bridge tokens."""
        col = self.db["jobs"]
        li_distinct = set(col.distinct("skills", {"source": "linkedin"}))
        ind_distinct = set(col.distinct("skills", {"source": "indeed"}))

        self.assertEqual(len(li_distinct), 35)
        self.assertEqual(len(ind_distinct), 464)

        overlap = li_distinct.intersection(ind_distinct)
        expected_overlap = {"Customer Service", "Public Relations", "Project Management", "Marketing"}
        self.assertEqual(overlap, expected_overlap)

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

