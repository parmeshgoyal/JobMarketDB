"""
JobMarketDB - Phase 6 Step 1 Focused Verification Suite

Tests:
1. Valid sorting parameters across all allowlisted fields and orders.
2. Invalid sorting parameters rejection (ValueError).
3. Full-text relevance preservation (textScore preservation when sorting by relevance or default).
4. Explicit missing salary handling in both sort directions (no silent filtering, count invariance).
5. LinkedIn vs Indeed date sorting limitations.
6. Job retrieval via get_job_by_id (ObjectId string, ObjectId instance, source_job_id).
7. Related jobs via get_related_jobs (same-platform isolation, target exclusion, deduplication, ranking, fallbacks).
8. Database invariant check (129,550 jobs, 24,472 companies, 11 jobs indexes, 4 companies indexes).
"""

import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bson import ObjectId
from typing import Any, Dict, List

from database.connection import get_database
from analytics.service import JobMarketAnalyticsService
from analytics.queries import (
    ALLOWED_SORT_FIELDS,
    _validate_sort_parameters,
    get_job_by_id,
    get_related_jobs,
    search_and_filter_jobs,
)


class Phase6Step1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)

        # Baseline database invariants
        cls.expected_jobs_count = 129550
        cls.expected_companies_count = 24472
        cls.expected_jobs_indexes = 11
        cls.expected_companies_indexes = 4

    # -------------------------------------------------------------------------
    # 1. Parameter Validation Tests
    # -------------------------------------------------------------------------
    def test_sort_parameter_validation_valid(self):
        """Test valid sort_by and sort_order combinations."""
        # Allowed fields: None, "relevance", "salary", "posted_date", "title"
        for field in [None, "relevance", "salary", "posted_date", "title"]:
            for order in [1, -1, "asc", "desc", "ASC", "DESC", "ascending", "descending"]:
                clean_field, clean_order = _validate_sort_parameters(field, order)
                expected_field = field if field is None else field.lower()
                self.assertEqual(clean_field, expected_field)
                self.assertIn(clean_order, (1, -1))

    def test_sort_parameter_validation_invalid_field(self):
        """Test rejection of non-allowlisted sort fields."""
        invalid_fields = ["company", "location", "experience", "random_field", 123, True]
        for field in invalid_fields:
            with self.assertRaises(ValueError, msg=f"Should raise ValueError for {field}"):
                _validate_sort_parameters(sort_by=field, sort_order=1)

    def test_sort_parameter_validation_invalid_order(self):
        """Test rejection of invalid sort orders."""
        invalid_orders = [0, 2, -2, "up", "down", "random", True, False, None]
        for order in invalid_orders:
            with self.assertRaises(ValueError, msg=f"Should raise ValueError for {order}"):
                _validate_sort_parameters(sort_by="salary", sort_order=order)

    # -------------------------------------------------------------------------
    # 2. Search & Filter Sorting Tests
    # -------------------------------------------------------------------------
    def test_fulltext_relevance_sorting(self):
        """Test full-text relevance preservation when search query is provided."""
        results_default, count_default = self.service.search_and_filter(
            query_text="python developer",
            sort_by=None,
            limit=5,
        )
        self.assertGreater(count_default, 0)
        self.assertEqual(len(results_default), 5)
        # Check textScore projection exists
        self.assertIn("score", results_default[0])
        self.assertIsInstance(results_default[0]["score"], float)

        results_relevance, count_relevance = self.service.search_and_filter(
            query_text="python developer",
            sort_by="relevance",
            limit=5,
        )
        self.assertEqual(count_relevance, count_default)
        self.assertEqual(
            [r["_id"] for r in results_default],
            [r["_id"] for r in results_relevance],
            "Default text search sort and explicit relevance sort should yield identical ranking."
        )

    def test_missing_salary_handling_both_directions(self):
        """
        Test explicit missing salary handling in both sort directions:
        - Results must NOT silently exclude documents with null salary.
        - Total matching count must remain invariant regardless of sort direction.
        - Descending: Highest salaries first; null salaries sort last.
        - Ascending: Null salaries sort first (BSON Null < Number); lowest salaries follow.
        """
        # Query a representative role
        query = "analyst"
        
        # 1. Unsorted count
        _, count_unsorted = self.service.search_and_filter(query_text=query, limit=1)
        
        # 2. Descending salary sort
        results_desc, count_desc = self.service.search_and_filter(
            query_text=query,
            sort_by="salary",
            sort_order=-1,
            limit=10,
        )
        # 3. Ascending salary sort
        results_asc, count_asc = self.service.search_and_filter(
            query_text=query,
            sort_by="salary",
            sort_order=1,
            limit=10,
        )

        # Invariant check: counts must be identical (no silent exclusion of null salaries)
        self.assertEqual(count_unsorted, count_desc, "Descending salary sort must not exclude null salaries.")
        self.assertEqual(count_unsorted, count_asc, "Ascending salary sort must not exclude null salaries.")

        # Check descending values: top results should have non-null high salaries
        first_desc_sal = (results_desc[0].get("salary") or {}).get("normalized_annual")
        self.assertIsNotNone(first_desc_sal, "Top descending salary should have a normalized_annual value.")
        self.assertGreater(first_desc_sal, 50000.0)

        # Verify descending order among non-null salaries
        desc_salaries = [
            (r.get("salary") or {}).get("normalized_annual")
            for r in results_desc
            if (r.get("salary") or {}).get("normalized_annual") is not None
        ]
        self.assertEqual(
            desc_salaries,
            sorted(desc_salaries, reverse=True),
            "Non-null salaries in descending sort must be non-increasing."
        )

        # Check ascending values: in MongoDB, null values naturally sort first
        first_asc_sal = (results_asc[0].get("salary") or {}).get("normalized_annual")
        self.assertIsNone(
            first_asc_sal,
            "Ascending salary sort must place null salaries first without dropping them."
        )

    def test_date_sorting_and_platform_limitations(self):
        """
        Test date sorting and document platform differences:
        - LinkedIn postings have authentic ISO datetime in posted_date.
        - Indeed postings have posted_date: null (relative days in date_since_posted_days).
        """
        # 1. LinkedIn date sorting
        linkedin_results, li_count = self.service.search_and_filter(
            source="linkedin",
            sort_by="posted_date",
            sort_order=-1,
            limit=5,
        )
        self.assertGreater(li_count, 0)
        self.assertTrue(all(r["posted_date"] is not None for r in linkedin_results))
        li_dates = [r["posted_date"] for r in linkedin_results]
        self.assertEqual(li_dates, sorted(li_dates, reverse=True), "LinkedIn dates must sort descending.")

        # 2. Indeed date limitation verification
        indeed_results, in_count = self.service.search_and_filter(
            source="indeed",
            sort_by="posted_date",
            sort_order=-1,
            limit=5,
        )
        self.assertGreater(in_count, 0)
        self.assertTrue(
            all(r["posted_date"] is None for r in indeed_results),
            "Indeed postings must have posted_date: null (as documented in Phase 2/3 schema)."
        )

        # 3. Cross-platform date sort: LinkedIn dated jobs should appear before Indeed null-date jobs in desc
        mixed_results, _ = self.service.search_and_filter(
            sort_by="posted_date",
            sort_order=-1,
            limit=10,
        )
        # All non-null dates should come before null dates
        found_null = False
        for r in mixed_results:
            if r["posted_date"] is None:
                found_null = True
            elif found_null:
                self.fail("Found non-null posted_date after a null posted_date in descending sort!")

    def test_title_sorting(self):
        """Test sorting by job title alphabetically."""
        results_asc, _ = self.service.search_and_filter(
            source="linkedin",
            sort_by="title",
            sort_order=1,
            limit=5,
        )
        titles_asc = [r["title"].lower() for r in results_asc]
        self.assertEqual(titles_asc, sorted(titles_asc), "Titles in asc sort must be alphabetically ordered.")

    # -------------------------------------------------------------------------
    # 3. get_job_by_id Tests
    # -------------------------------------------------------------------------
    def test_get_job_by_id_linkedin(self):
        """Test retrieving a LinkedIn job by ObjectId string, ObjectId instance, and source_job_id."""
        sample = self.db["jobs"].find_one({"source": "linkedin", "source_job_id": {"$exists": True}})
        self.assertIsNotNone(sample)

        oid_str = str(sample["_id"])
        source_id = sample["source_job_id"]

        # 1. By string ObjectId
        job1 = self.service.get_job_by_id(oid_str)
        self.assertIsNotNone(job1)
        self.assertEqual(job1["_id"], oid_str)

        # 2. By ObjectId object
        job2 = self.service.get_job_by_id(sample["_id"])
        self.assertIsNotNone(job2)
        self.assertEqual(job2["_id"], oid_str)

        # 3. By authentic source_job_id
        job3 = self.service.get_job_by_id(source_id)
        self.assertIsNotNone(job3)
        self.assertEqual(job3["_id"], oid_str)
        self.assertEqual(job3["source"], "linkedin")

    def test_get_job_by_id_indeed(self):
        """Test retrieving an Indeed job by ObjectId string and source_job_id."""
        sample = self.db["jobs"].find_one({"source": "indeed", "source_job_id": {"$exists": True}})
        self.assertIsNotNone(sample)

        oid_str = str(sample["_id"])
        source_id = sample["source_job_id"]

        # By string ObjectId
        job1 = self.service.get_job_by_id(oid_str)
        self.assertIsNotNone(job1)
        self.assertEqual(job1["_id"], oid_str)

        # By authentic source_job_id (e.g. hex hash string)
        job2 = self.service.get_job_by_id(source_id)
        self.assertIsNotNone(job2)
        self.assertEqual(job2["_id"], oid_str)
        self.assertEqual(job2["source"], "indeed")

    def test_get_job_by_id_invalid_and_missing(self):
        """Test invalid IDs and non-existent queries return None."""
        self.assertIsNone(self.service.get_job_by_id("000000000000000000000000"))
        self.assertIsNone(self.service.get_job_by_id("non_existent_source_id_xyz"))
        self.assertIsNone(self.service.get_job_by_id(""))

    # -------------------------------------------------------------------------
    # 4. get_related_jobs Tests
    # -------------------------------------------------------------------------
    def test_related_jobs_same_platform_restriction(self):
        """
        Verify Priority 2 requirement:
        - Target job from LinkedIn MUST ONLY recommend LinkedIn jobs.
        - Target job from Indeed MUST ONLY recommend Indeed jobs.
        """
        # 1. LinkedIn target
        li_target = self.db["jobs"].find_one({"source": "linkedin", "skills.0": {"$exists": True}})
        self.assertIsNotNone(li_target)
        li_related = self.service.get_related_jobs(str(li_target["_id"]), limit=5)
        self.assertGreater(len(li_related), 0)
        for r in li_related:
            self.assertEqual(r["source"], "linkedin", "LinkedIn target must only yield LinkedIn related jobs.")
            self.assertEqual(r["match_explanation"]["source_platform"], "linkedin")

        # 2. Indeed target
        in_target = self.db["jobs"].find_one({"source": "indeed", "skills.0": {"$exists": True}})
        self.assertIsNotNone(in_target)
        in_related = self.service.get_related_jobs(str(in_target["_id"]), limit=5)
        self.assertGreater(len(in_related), 0)
        for r in in_related:
            self.assertEqual(r["source"], "indeed", "Indeed target must only yield Indeed related jobs.")
            self.assertEqual(r["match_explanation"]["source_platform"], "indeed")

    def test_related_jobs_target_exclusion_and_deduplication(self):
        """
        Verify:
        - Target job itself is excluded from recommendations.
        - No duplicate postings in recommendations.
        """
        sample = self.db["jobs"].find_one({"source": "linkedin", "skills.2": {"$exists": True}})
        self.assertIsNotNone(sample)
        target_id_str = str(sample["_id"])
        target_source_id = str(sample.get("source_job_id", ""))

        related = self.service.get_related_jobs(target_id_str, limit=10)
        self.assertGreater(len(related), 0)

        related_ids = [r["_id"] for r in related]
        # Target exclusion
        self.assertNotIn(target_id_str, related_ids, "Target posting _id must be excluded.")
        if target_source_id:
            related_source_ids = [str(r.get("source_job_id", "")) for r in related]
            self.assertNotIn(target_source_id, related_source_ids, "Target source_job_id must be excluded.")

        # Deduplication
        self.assertEqual(len(related_ids), len(set(related_ids)), "Related jobs must be strictly unique.")

    def test_related_jobs_ranking_and_explanation(self):
        """
        Verify:
        - Recommendations are ordered by match score descending.
        - Match explanation metadata is populated and mathematically consistent.
        """
        sample = self.db["jobs"].find_one({
            "source": "indeed",
            "role_category.value": {"$ne": None},
            "skills.2": {"$exists": True}
        })
        self.assertIsNotNone(sample)

        related = self.service.get_related_jobs(str(sample["_id"]), limit=5)
        self.assertGreater(len(related), 0)

        scores = [r["match_explanation"]["match_score"] for r in related]
        self.assertEqual(scores, sorted(scores, reverse=True), "Related jobs must be ranked by match_score descending.")

        # Check metadata consistency
        for r in related:
            exp = r["match_explanation"]
            self.assertIn("shared_skills", exp)
            self.assertIn("shared_skills_count", exp)
            self.assertIn("same_role_category", exp)
            self.assertIn("same_state", exp)
            calculated_score = (exp["shared_skills_count"] * 3) + (5 if exp["same_role_category"] else 0) + (1 if exp["same_state"] else 0)
            self.assertEqual(exp["match_score"], calculated_score, "Match score must equal defined formula.")

    def test_related_jobs_missing_fields_fallback(self):
        """Test fallback behavior when target job has empty skills or missing role category."""
        # Find a job with empty skills array
        sparse_job = self.db["jobs"].find_one({"source": "linkedin", "skills": []})
        if sparse_job is None:
            # Or find one with skills null
            sparse_job = self.db["jobs"].find_one({"source": "linkedin", "skills": None})

        if sparse_job:
            related = self.service.get_related_jobs(str(sparse_job["_id"]), limit=5)
            self.assertGreater(len(related), 0, "Fallback must return related jobs even with empty skills.")
            self.assertTrue(all(r["source"] == "linkedin" for r in related))

    # -------------------------------------------------------------------------
    # 5. Database Invariant Check
    # -------------------------------------------------------------------------
    def test_database_invariants(self):
        """Verify canonical document counts and index counts remain completely unchanged."""
        jobs_count = self.db["jobs"].count_documents({})
        companies_count = self.db["companies"].count_documents({})
        jobs_indexes = len(self.db["jobs"].index_information())
        companies_indexes = len(self.db["companies"].index_information())

        self.assertEqual(jobs_count, self.expected_jobs_count, f"Jobs count mutated: {jobs_count}")
        self.assertEqual(companies_count, self.expected_companies_count, f"Companies count mutated: {companies_count}")
        self.assertEqual(jobs_indexes, self.expected_jobs_indexes, f"Jobs index count mutated: {jobs_indexes}")
        self.assertEqual(companies_indexes, self.expected_companies_indexes, f"Companies index count mutated: {companies_indexes}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
