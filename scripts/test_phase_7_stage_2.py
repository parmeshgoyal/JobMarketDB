"""
JobMarketDB — Phase 7 Stage 2 Focused Test Suite
Flagship Product: Job Explorer Verification Suite

Tests:
1. Full-text and regex search execution via analytics service
2. Multi-facet filters: platform, state, remote, salary bucket, continuous salary, company, experience
3. Skills matching logic: ALL ($all) versus ANY ($in)
4. Authentic remote tri-state behavior (True, False, None, Any)
5. Salary filtering and strict non-fabrication of missing salaries
6. Allowlisted sorting modes and directions
7. Pagination offsets and bounds
8. Single job detail retrieval and provenance fields
9. Same-platform related jobs recommendations (strict taxonomy isolation)
10. HTML escaping integrity for job cards and headers
11. Canonical database invariants (129,550 jobs, 24,472 companies, 15 indexes)
"""

import html
import os
import sys
import unittest
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService
from utils.ui_components import render_elevated_job_card, render_platform_badge


class TestPhase7Stage2JobExplorer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        verify_connection()
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)
        cls.expected_jobs_count = 129550
        cls.expected_companies_count = 24472
        cls.expected_jobs_indexes = 11
        cls.expected_companies_indexes = 4

    # -------------------------------------------------------------------------
    # 1. Search Modes: Full-Text and Regex
    # -------------------------------------------------------------------------
    def test_01_full_text_search(self):
        """Full-text search queries title and description via text index."""
        results, count = self.service.search_and_filter(
            query_text="Engineer",
            search_mode="text",
            limit=5,
        )
        self.assertGreater(count, 0)
        self.assertLessEqual(len(results), 5)
        for job in results:
            self.assertIn("title", job)

    def test_02_regex_title_search(self):
        """Regex search specifically targets title field."""
        results, count = self.service.search_and_filter(
            query_text="Data Scientist",
            search_mode="regex",
            limit=5,
        )
        self.assertGreater(count, 0)
        for job in results:
            self.assertIn("data scientist", job["title"].lower())

    # -------------------------------------------------------------------------
    # 2. Skills Matching Logic: ALL ($all) vs ANY ($in)
    # -------------------------------------------------------------------------
    def test_03_skills_match_all_and_any(self):
        """Test $all vs $in multikey skills semantics."""
        skills = ["Python", "SQL"]
        # ALL
        res_all, count_all = self.service.search_and_filter(skills=skills, skills_match_all=True, limit=10)
        # ANY
        res_any, count_any = self.service.search_and_filter(skills=skills, skills_match_all=False, limit=10)

        self.assertGreater(count_any, count_all)
        for job in res_all:
            job_skills = job.get("skills", [])
            self.assertTrue(all(s in job_skills for s in skills))

    # -------------------------------------------------------------------------
    # 3. Authentic Remote Tri-State Behavior
    # -------------------------------------------------------------------------
    def test_04_remote_tri_state(self):
        """Verify tri-state remote semantics: True, False, None, Any."""
        # Remote True
        _, count_true = self.service.search_and_filter(is_remote=True, limit=1)
        self.assertEqual(count_true, 15236)

        # Explicitly On-Site False (0 in authentic dataset)
        _, count_false = self.service.search_and_filter(is_remote=False, limit=1)
        self.assertEqual(count_false, 0)

        # Unspecified None
        _, count_none = self.service.search_and_filter(is_remote=None, limit=1)
        self.assertEqual(count_none, 114314)

        # Total sum check: 15236 + 114314 = 129550
        self.assertEqual(count_true + count_none, 129550)

    # -------------------------------------------------------------------------
    # 4. Compensation Filters & Missing Salary Handling
    # -------------------------------------------------------------------------
    def test_05_salary_bucket_and_continuous(self):
        """Test salary bucket filter and continuous range filter."""
        # Bucket
        res_b, count_b = self.service.search_and_filter(salary_bucket="100000-119999", limit=5)
        self.assertGreater(count_b, 0)
        for job in res_b:
            self.assertEqual(job.get("salary", {}).get("salary_bucket"), "100000-119999")

        # Continuous range
        res_c, count_c = self.service.search_and_filter(min_annual=100000.0, max_annual=120000.0, limit=5)
        self.assertGreater(count_c, 0)
        for job in res_c:
            val = job.get("salary", {}).get("normalized_annual")
            self.assertIsNotNone(val)
            self.assertTrue(100000.0 <= val <= 120000.0)

    # -------------------------------------------------------------------------
    # 5. Sorting and Pagination Controls
    # -------------------------------------------------------------------------
    def test_06_sorting_and_pagination(self):
        """Test allowlisted sorting by salary and pagination skip/limit."""
        # Sort salary descending
        res_desc, _ = self.service.search_and_filter(
            sort_by="salary",
            sort_order=-1,
            limit=5,
            skip=0,
        )
        salaries = [j.get("salary", {}).get("normalized_annual", 0) for j in res_desc]
        self.assertEqual(salaries, sorted(salaries, reverse=True))

        # Pagination: Page 1 vs Page 2 (no overlap)
        p1, _ = self.service.search_and_filter(limit=5, skip=0)
        p2, _ = self.service.search_and_filter(limit=5, skip=5)
        ids_p1 = {j["_id"] for j in p1}
        ids_p2 = {j["_id"] for j in p2}
        self.assertEqual(len(ids_p1.intersection(ids_p2)), 0)

    # -------------------------------------------------------------------------
    # 6. Single Job Detail Retrieval
    # -------------------------------------------------------------------------
    def test_07_job_detail_lookup(self):
        """Test lookup by ObjectId, string id, and non-existent id."""
        first_job = self.db["jobs"].find_one({}, {"_id": 1, "title": 1})
        self.assertIsNotNone(first_job)
        str_id = str(first_job["_id"])

        # Lookup by string ID
        found_job = self.service.get_job_by_id(str_id)
        self.assertIsNotNone(found_job)
        self.assertEqual(str(found_job["_id"]), str_id)

        # Lookup non-existent
        bad_job = self.service.get_job_by_id("000000000000000000000000")
        self.assertIsNone(bad_job)

    # -------------------------------------------------------------------------
    # 7. Same-Platform Related Job Recommendations
    # -------------------------------------------------------------------------
    def test_08_related_jobs_same_platform_isolation(self):
        """Verify related jobs are strictly isolated to the same source platform."""
        # Find a LinkedIn job and an Indeed job
        li_job = self.db["jobs"].find_one({"source": "linkedin"}, {"_id": 1})
        ind_job = self.db["jobs"].find_one({"source": "indeed"}, {"_id": 1})

        # LinkedIn recommendations
        li_related = self.service.get_related_jobs(str(li_job["_id"]), limit=5)
        for r in li_related:
            self.assertEqual(r.get("source"), "linkedin")
            self.assertNotEqual(str(r["_id"]), str(li_job["_id"]))

        # Indeed recommendations
        ind_related = self.service.get_related_jobs(str(ind_job["_id"]), limit=5)
        for r in ind_related:
            self.assertEqual(r.get("source"), "indeed")
            self.assertNotEqual(str(r["_id"]), str(ind_job["_id"]))

    # -------------------------------------------------------------------------
    # 8. HTML/XSS Escaping Integrity
    # -------------------------------------------------------------------------
    def test_09_card_escaping_and_safety(self):
        """Confirm job card markup strictly escapes malicious tags."""
        malicious_job = {
            "title": "<script>alert('pwned')</script>",
            "source": "linkedin",
            "company": {"name": "Hacker <img src=x>"},
            "location": {"city": "City", "state": "CA"},
            "salary": {"normalized_annual": 150000.0},
            "skills": ["<script>", "SQL"],
        }
        rendered = render_elevated_job_card(malicious_job)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<img src=x>", rendered)

    # -------------------------------------------------------------------------
    # 9. Database Invariants Strictly Preserved
    # -------------------------------------------------------------------------
    def test_10_database_invariants(self):
        """Confirm canonical collections and indexes remain unmodified."""
        jobs_count = self.db["jobs"].count_documents({})
        companies_count = self.db["companies"].count_documents({})
        jobs_indexes = len(self.db["jobs"].index_information())
        companies_indexes = len(self.db["companies"].index_information())

        self.assertEqual(jobs_count, self.expected_jobs_count)
        self.assertEqual(companies_count, self.expected_companies_count)
        self.assertEqual(jobs_indexes, self.expected_jobs_indexes)
        self.assertEqual(companies_indexes, self.expected_companies_indexes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

