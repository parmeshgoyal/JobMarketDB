"""
JobMarketDB - Phase 6 Step 5 Test Suite
Tests for Module 2: Skills Analytics & Taxonomy Separation

Verifies:
1. Strict platform separation (LinkedIn functional domains vs Indeed technical tools)
2. Accurate skill counts and descending ranking order against direct MongoDB queries
3. Distinct skill counting semantics and $setUnion deduplication
4. Empty, missing, and zero-skill posting handling
5. Multi-facet role category filtering on skill demand
6. Visualizations and chart data builders
7. Database safety invariants (read-only integrity, collection counts, index counts)
"""

import os
import sys
import unittest
from typing import Any, Dict, List

# Ensure project root is available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analytics.service import JobMarketAnalyticsService
from analytics.aggregations import get_top_demanded_skills, get_skills_by_platform
from utils.plots import create_skills_demand_chart, create_empty_chart, THEME
import plotly.graph_objects as go


class TestSkillsAnalyticsPlatformSeparation(unittest.TestCase):
    """Verifies that LinkedIn and Indeed taxonomies are strictly partitioned."""

    @classmethod
    def setUpClass(cls):
        cls.service = JobMarketAnalyticsService()
        cls.db = cls.service.db

    def test_platform_skills_isolation(self):
        """Test that get_skills_by_platform returns separate namespaces for LinkedIn and Indeed."""
        result = self.service.get_skills_by_platform(limit=10)
        self.assertIn("linkedin", result)
        self.assertIn("indeed", result)
        self.assertEqual(result["linkedin"]["source"], "linkedin")
        self.assertEqual(result["indeed"]["source"], "indeed")

        # LinkedIn should have 123,835 postings evaluated
        self.assertEqual(result["linkedin"]["total_postings"], 123835)
        # Indeed should have 5,715 postings evaluated
        self.assertEqual(result["indeed"]["total_postings"], 5715)

    def test_linkedin_domains_fidelity(self):
        """Test that LinkedIn top skills reflect broad functional disciplines, not tools."""
        li_res = self.service.get_top_skills(limit=10, source="linkedin")
        self.assertEqual(li_res["source_filter"], "linkedin")
        self.assertEqual(li_res["total_postings_evaluated"], 123835)

        li_skill_names = [s["skill"] for s in li_res["skills"]]
        # Must contain known functional disciplines
        self.assertIn("Information Technology", li_skill_names)
        self.assertIn("Sales", li_skill_names)
        self.assertIn("Management", li_skill_names)
        self.assertIn("Manufacturing", li_skill_names)

        # Must NOT contain granular programming tools
        self.assertNotIn("Python", li_skill_names)
        self.assertNotIn("SQL", li_skill_names)
        self.assertNotIn("Docker", li_skill_names)
        self.assertNotIn("Hadoop", li_skill_names)

    def test_indeed_tools_fidelity(self):
        """Test that Indeed top skills reflect granular technical tools, not broad domains."""
        ind_res = self.service.get_top_skills(limit=10, source="indeed")
        self.assertEqual(ind_res["source_filter"], "indeed")
        self.assertEqual(ind_res["total_postings_evaluated"], 5715)

        ind_skill_names = [s["skill"] for s in ind_res["skills"]]
        # Must contain known granular programming tools
        self.assertIn("Python", ind_skill_names)
        self.assertIn("SQL", ind_skill_names)
        self.assertIn("Machine Learning", ind_skill_names)
        self.assertIn("R", ind_skill_names)

        # Must NOT contain broad LinkedIn-exclusive domain names
        self.assertNotIn("Information Technology", ind_skill_names)
        self.assertNotIn("Manufacturing", ind_skill_names)
        self.assertNotIn("Health Care Provider", ind_skill_names)

    def test_vocabulary_intersection_boundary(self):
        """Verify that the overlap between LinkedIn and Indeed vocabularies is precisely 4 bridge tokens."""
        col = self.db["jobs"]
        li_distinct = set(col.distinct("skills", {"source": "linkedin"}))
        ind_distinct = set(col.distinct("skills", {"source": "indeed"}))

        self.assertEqual(len(li_distinct), 35, "LinkedIn must have exactly 35 distinct functional domains")
        self.assertEqual(len(ind_distinct), 464, "Indeed must have exactly 464 distinct technical tools")

        overlap = li_distinct.intersection(ind_distinct)
        expected_overlap = {"Customer Service", "Public Relations", "Project Management", "Marketing"}
        self.assertEqual(overlap, expected_overlap, f"Overlap should only be 4 shared tokens, got: {overlap}")


class TestSkillCountsAndRankingOrder(unittest.TestCase):
    """Verifies that skill frequencies and ranking orders match direct MongoDB ground-truth."""

    @classmethod
    def setUpClass(cls):
        cls.service = JobMarketAnalyticsService()
        cls.db = cls.service.db

    def test_linkedin_top_skill_ground_truth(self):
        """Verify LinkedIn #1 domain is Information Technology with 25,252 postings."""
        res = self.service.get_top_skills(limit=5, source="linkedin")
        top_skill = res["skills"][0]
        self.assertEqual(top_skill["skill"], "Information Technology")
        self.assertEqual(top_skill["count"], 25252)
        # Expected %: 25252 / 123835 * 100 = 20.39%
        self.assertAlmostEqual(top_skill["percentage_of_postings"], 20.39, places=2)

    def test_indeed_top_skills_ground_truth(self):
        """Verify Indeed #1 tool is Python (3,325), #2 SQL (3,104), #3 Machine Learning (2,297)."""
        res = self.service.get_top_skills(limit=5, source="indeed")
        skills = res["skills"]

        self.assertEqual(skills[0]["skill"], "Python")
        self.assertEqual(skills[0]["count"], 3325)
        # Expected %: 3325 / 5715 * 100 = 58.18%
        self.assertAlmostEqual(skills[0]["percentage_of_postings"], 58.18, places=2)

        self.assertEqual(skills[1]["skill"], "SQL")
        self.assertEqual(skills[1]["count"], 3104)
        # Expected %: 3104 / 5715 * 100 = 54.31%
        self.assertAlmostEqual(skills[1]["percentage_of_postings"], 54.31, places=2)

        self.assertEqual(skills[2]["skill"], "Machine Learning")
        self.assertEqual(skills[2]["count"], 2297)
        # Expected %: 2297 / 5715 * 100 = 40.19%
        self.assertAlmostEqual(skills[2]["percentage_of_postings"], 40.19, places=2)

    def test_descending_rank_order(self):
        """Verify that returned skills are monotonically non-increasing in count."""
        for src in ["linkedin", "indeed"]:
            res = self.service.get_top_skills(limit=25, source=src)
            counts = [s["count"] for s in res["skills"]]
            self.assertEqual(counts, sorted(counts, reverse=True), f"Ranking must be strictly descending for {src}")

    def test_direct_mongodb_reference_equivalence(self):
        """Verify service results match independent, direct reference aggregation."""
        col = self.db["jobs"]
        ref_pipeline = [
            {"$match": {"source": "indeed"}},
            {"$project": {"skills": {"$setUnion": [{"$ifNull": ["$skills", []]}, []]}}},
            {"$unwind": "$skills"},
            {"$group": {"_id": "$skills", "total": {"$sum": 1}}},
            {"$sort": {"total": -1}},
            {"$limit": 5},
        ]
        ref_docs = list(col.aggregate(ref_pipeline))
        service_res = self.service.get_top_skills(limit=5, source="indeed")["skills"]

        for ref, srv in zip(ref_docs, service_res):
            self.assertEqual(ref["_id"], srv["skill"])
            self.assertEqual(ref["total"], srv["count"])


class TestDistinctSkillCountingAndDeduplication(unittest.TestCase):
    """Verifies $setUnion deduplication logic preventing multi-token inflation."""

    @classmethod
    def setUpClass(cls):
        cls.service = JobMarketAnalyticsService()
        cls.db = cls.service.db

    def test_set_union_deduplication_semantics(self):
        """Verify that $setUnion collapses duplicate elements in array projections."""
        col = self.db["jobs"]
        pipeline = [
            {"$match": {"source": "indeed"}},
            {"$limit": 10},
            {"$project": {
                "test_array": {"$literal": ["Python", "Python", "Python", "SQL"]},
            }},
            {"$project": {
                "deduped": {"$setUnion": ["$test_array", []]},
            }},
        ]
        sample = list(col.aggregate(pipeline))
        self.assertTrue(len(sample) > 0)
        # Length of deduped array must be 2, containing Python and SQL exactly once
        self.assertEqual(len(sample[0]["deduped"]), 2)
        self.assertEqual(set(sample[0]["deduped"]), {"Python", "SQL"})

    def test_zero_skills_postings_included_in_denominator(self):
        """Verify that postings with empty/null skills remain in total postings denominator."""
        col = self.db["jobs"]
        zero_li = col.count_documents({"source": "linkedin", "$or": [{"skills": {"$exists": False}}, {"skills": {"$size": 0}}]})
        zero_ind = col.count_documents({"source": "indeed", "$or": [{"skills": {"$exists": False}}, {"skills": {"$size": 0}}]})

        # From baseline: LinkedIn has 1,752 postings with no skills; Indeed has 232
        self.assertEqual(zero_li, 1752)
        self.assertEqual(zero_ind, 232)

        # Evaluated totals must be full population, not just postings with skills
        res_li = self.service.get_top_skills(limit=1, source="linkedin")
        self.assertEqual(res_li["total_postings_evaluated"], 123835)

        res_ind = self.service.get_top_skills(limit=1, source="indeed")
        self.assertEqual(res_ind["total_postings_evaluated"], 5715)


class TestRoleCategoryFilter(unittest.TestCase):
    """Verifies that role_category filtering functions correctly across both platforms."""

    @classmethod
    def setUpClass(cls):
        cls.service = JobMarketAnalyticsService()

    def test_indeed_data_scientist_filtering(self):
        """Test filtering Indeed skills by role_category='Data Scientist'."""
        res = self.service.get_top_skills(limit=5, source="indeed", role_category="Data Scientist")
        self.assertEqual(res["role_category_filter"], "Data Scientist")
        self.assertGreater(res["total_postings_evaluated"], 0)
        self.assertLess(res["total_postings_evaluated"], 5715)

        skills = [s["skill"] for s in res["skills"]]
        self.assertIn("Python", skills)
        self.assertIn("Machine Learning", skills)

    def test_linkedin_software_engineer_filtering(self):
        """Test filtering LinkedIn domains by role_category='Software Engineer'."""
        res = self.service.get_top_skills(limit=5, source="linkedin", role_category="Software Engineer")
        self.assertEqual(res["role_category_filter"], "Software Engineer")
        self.assertGreater(res["total_postings_evaluated"], 0)
        self.assertLess(res["total_postings_evaluated"], 123835)

        skills = [s["skill"] for s in res["skills"]]
        self.assertIn("Information Technology", skills)
        self.assertIn("Engineering", skills)

    def test_nonexistent_role_category_graceful(self):
        """Test non-existent role category yields empty skills list without crashing."""
        res = self.service.get_top_skills(limit=5, source="indeed", role_category="NonExistentRoleXYZ")
        self.assertEqual(res["total_postings_evaluated"], 0)
        self.assertEqual(len(res["skills"]), 0)

    def test_indeed_role_category_denominators_and_percentages(self):
        """Verify that scoped denominators and percentages precisely reflect platform AND role category."""
        # 1. Unfiltered Indeed
        res_all = self.service.get_top_skills(limit=5, source="indeed")
        self.assertEqual(res_all["total_postings_evaluated"], 5715)
        py_all = next(s for s in res_all["skills"] if s["skill"] == "Python")
        self.assertEqual(py_all["count"], 3325)
        self.assertEqual(py_all["percentage_of_postings"], 58.18)

        # 2. Indeed Data Scientist
        res_ds = self.service.get_top_skills(limit=5, source="indeed", role_category="Data Scientist")
        self.assertEqual(res_ds["total_postings_evaluated"], 2543)
        py_ds = next(s for s in res_ds["skills"] if s["skill"] == "Python")
        self.assertEqual(py_ds["count"], 1912)
        # Expected %: 1912 / 2543 * 100 = 75.1867... -> 75.19%
        self.assertEqual(py_ds["percentage_of_postings"], 75.19)

        # 3. Indeed Data Analyst
        res_da = self.service.get_top_skills(limit=5, source="indeed", role_category="Data Analyst")
        self.assertEqual(res_da["total_postings_evaluated"], 1793)
        sql_da = next(s for s in res_da["skills"] if s["skill"] == "SQL")
        self.assertEqual(sql_da["count"], 1044)
        # Expected %: 1044 / 1793 * 100 = 58.226... -> 58.23%
        self.assertEqual(sql_da["percentage_of_postings"], 58.23)

        # 4. Indeed Data Engineer
        res_de = self.service.get_top_skills(limit=5, source="indeed", role_category="Data Engineer")
        self.assertEqual(res_de["total_postings_evaluated"], 1379)
        py_de = next(s for s in res_de["skills"] if s["skill"] == "Python")
        self.assertEqual(py_de["count"], 901)
        # Expected %: 901 / 1379 * 100 = 65.337... -> 65.34%
        self.assertEqual(py_de["percentage_of_postings"], 65.34)

        # 5. Role category partition sum matches total Indeed postings
        self.assertEqual(2543 + 1793 + 1379, 5715)

    def test_scoped_denominator_includes_zero_skill_postings(self):
        """Verify that postings lacking skill annotations remain included in scoped role-category denominators."""
        col = self.service.db["jobs"]
        # Ground truth counts in MongoDB
        da_total = col.count_documents({"source": "indeed", "role_category.value": "Data Analyst"})
        da_zero = col.count_documents({"source": "indeed", "role_category.value": "Data Analyst", "$or": [{"skills": {"$exists": False}}, {"skills": {"$size": 0}}]})
        self.assertEqual(da_total, 1793)
        self.assertEqual(da_zero, 163)

        ds_total = col.count_documents({"source": "indeed", "role_category.value": "Data Scientist"})
        ds_zero = col.count_documents({"source": "indeed", "role_category.value": "Data Scientist", "$or": [{"skills": {"$exists": False}}, {"skills": {"$size": 0}}]})
        self.assertEqual(ds_total, 2543)
        self.assertEqual(ds_zero, 47)

        de_total = col.count_documents({"source": "indeed", "role_category.value": "Data Engineer"})
        de_zero = col.count_documents({"source": "indeed", "role_category.value": "Data Engineer", "$or": [{"skills": {"$exists": False}}, {"skills": {"$size": 0}}]})
        self.assertEqual(de_total, 1379)
        self.assertEqual(de_zero, 22)

        # Service evaluated denominators must equal full totals (including zero-skill postings)
        self.assertEqual(self.service.get_top_skills(limit=1, source="indeed", role_category="Data Analyst")["total_postings_evaluated"], 1793)
        self.assertEqual(self.service.get_top_skills(limit=1, source="indeed", role_category="Data Scientist")["total_postings_evaluated"], 2543)
        self.assertEqual(self.service.get_top_skills(limit=1, source="indeed", role_category="Data Engineer")["total_postings_evaluated"], 1379)


class TestChartBuildersAndVisualizations(unittest.TestCase):
    """Verifies Plotly chart builders handle skills data and edge cases cleanly."""

    def test_indeed_chart_builder(self):
        """Test create_skills_demand_chart with Indeed data."""
        skills = [
            {"skill": "Python", "count": 3325, "percentage_of_postings": 58.18},
            {"skill": "SQL", "count": 3104, "percentage_of_postings": 54.31},
        ]
        fig = create_skills_demand_chart(skills, platform="indeed", title="Indeed Top Skills")
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.data), 1)
        self.assertEqual(fig.data[0].orientation, "h")
        self.assertEqual(fig.data[0].marker.color, THEME["indeed_blue"])

    def test_linkedin_chart_builder(self):
        """Test create_skills_demand_chart with LinkedIn data."""
        skills = [
            {"skill": "Information Technology", "count": 25252, "percentage_of_postings": 20.39},
            {"skill": "Sales", "count": 21188, "percentage_of_postings": 17.11},
        ]
        fig = create_skills_demand_chart(skills, platform="linkedin", title="LinkedIn Top Domains")
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.data), 1)
        self.assertEqual(fig.data[0].orientation, "h")
        self.assertEqual(fig.data[0].marker.color, THEME["linkedin_blue"])

    def test_chart_builder_empty_inputs(self):
        """Test create_skills_demand_chart handles empty list and None without raising."""
        fig_empty = create_skills_demand_chart([], title="Empty Skills")
        self.assertIsInstance(fig_empty, go.Figure)
        self.assertTrue(any("No data available" in str(ann.text) for ann in fig_empty.layout.annotations))

        fig_none = create_skills_demand_chart(None, title="None Skills")
        self.assertIsInstance(fig_none, go.Figure)
        self.assertTrue(any("No data available" in str(ann.text) for ann in fig_none.layout.annotations) or len(fig_none.data) == 0)


class TestDatabaseSafetyInvariants(unittest.TestCase):
    """Verifies that database integrity, document counts, and index counts are strictly preserved."""

    @classmethod
    def setUpClass(cls):
        cls.service = JobMarketAnalyticsService()
        cls.db = cls.service.db

    def test_canonical_job_count_preserved(self):
        """Verify jobs collection has exactly 129,550 canonical documents."""
        count = self.db["jobs"].count_documents({})
        self.assertEqual(count, 129550, f"Jobs count modified! Expected 129,550, got {count}")

    def test_canonical_companies_count_preserved(self):
        """Verify companies collection has exactly 24,472 documents."""
        count = self.db["companies"].count_documents({})
        self.assertEqual(count, 24472, f"Companies count modified! Expected 24,472, got {count}")

    def test_canonical_index_inventory_preserved(self):
        """Verify 11 indexes on jobs and 4 indexes on companies (total 15)."""
        jobs_indexes = len(self.db["jobs"].index_information())
        companies_indexes = len(self.db["companies"].index_information())
        self.assertEqual(jobs_indexes, 11, f"Expected 11 indexes on jobs, found {jobs_indexes}")
        self.assertEqual(companies_indexes, 4, f"Expected 4 indexes on companies, found {companies_indexes}")
        self.assertEqual(jobs_indexes + companies_indexes, 15, "Expected exactly 15 total database indexes")


if __name__ == "__main__":
    unittest.main()
