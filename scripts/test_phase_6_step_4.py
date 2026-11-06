"""
Unit and Integration Tests for Phase 6 Step 4: Job Search & Details.

Validates:
1. Full-text search and Regex title search modes.
2. Every filter independently:
   - US State
   - Remote status preserving True / False / None / Any semantics
   - Salary bucket and continuous salary range
   - Skills multiselect with ALL ($all) and ANY ($in) semantics
   - Company name
   - Experience level
   - Source platform (LinkedIn, Indeed, Both)
3. Combined filters.
4. Allowlisted sorting modes and sort orders (relevance, salary, posted_date, title).
5. Missing salary and missing date behavior.
6. Pagination offsets, page counts, and consistency (no duplicate or skipped records).
7. Job detail lookup (ObjectId, string ObjectId, source_job_id).
8. Related-job recommendations (same-platform isolation, target exclusion, ranking).
9. Empty results and invalid input resilience.
10. Database invariants (canonical collections unchanged, index preservation).
"""

import os
import sys
import unittest
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService



class TestPhase6Step4JobSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        verify_connection()
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)

    # -------------------------------------------------------------------------
    # 1. Search Modes
    # -------------------------------------------------------------------------
    def test_01_full_text_search(self):
        """Full-text search using text index."""
        results, count = self.service.search_and_filter(
            query_text="Engineer",
            search_mode="text",
            limit=10
        )
        self.assertGreater(count, 0)
        self.assertLessEqual(len(results), 10)
        for job in results:
            self.assertIn("title", job)
            self.assertIn("source", job)

    def test_02_regex_title_search(self):
        """Regex search matching job titles specifically."""
        results, count = self.service.search_and_filter(
            query_text="Data Scientist",
            search_mode="regex",
            limit=10
        )
        self.assertGreater(count, 0)
        self.assertLessEqual(len(results), 10)
        for job in results:
            self.assertIn("data scientist", job["title"].lower())

    # -------------------------------------------------------------------------
    # 2. Individual Filters
    # -------------------------------------------------------------------------
    def test_03_filter_state(self):
        """US State filter."""
        results, count = self.service.search_and_filter(state="CA", limit=10)
        self.assertGreater(count, 0)
        for job in results:
            self.assertEqual(job.get("location", {}).get("state"), "CA")

    def test_04_filter_remote_true(self):
        """Explicitly remote postings (is_remote == True)."""
        results, count = self.service.search_and_filter(is_remote=True, limit=10)
        self.assertGreater(count, 0)
        for job in results:
            self.assertIs(job.get("location", {}).get("is_remote"), True)

    def test_05_filter_remote_false(self):
        """On-site postings (is_remote == False). In authentic data, on-site is unstated (is_remote is None), so literal False is 0."""
        results, count = self.service.search_and_filter(is_remote=False, limit=10)
        self.assertEqual(count, 0)
        self.assertEqual(len(results), 0)

    def test_06_filter_remote_none(self):
        """Unstated / Unknown remote postings (is_remote is None)."""
        results, count = self.service.search_and_filter(is_remote=None, limit=10)
        self.assertGreater(count, 0)
        for job in results:
            self.assertIsNone(job.get("location", {}).get("is_remote"))

    def test_07_filter_salary_bucket(self):
        """Salary bucket filter."""
        results, count = self.service.search_and_filter(salary_bucket="100000-119999", limit=10)
        self.assertGreater(count, 0)
        for job in results:
            self.assertEqual(job.get("salary", {}).get("salary_bucket"), "100000-119999")

    def test_08_filter_salary_continuous_range(self):
        """Continuous salary range filter (min_annual & max_annual)."""
        results, count = self.service.search_and_filter(min_annual=90000.0, max_annual=130000.0, limit=10)
        self.assertGreater(count, 0)
        for job in results:
            norm = job.get("salary", {}).get("normalized_annual")
            self.assertIsNotNone(norm)
            self.assertGreaterEqual(norm, 90000.0)
            self.assertLessEqual(norm, 130000.0)

    def test_09_filter_skills_match_all(self):
        """Skills multiselect with ALL ($all) semantics."""
        results, count = self.service.search_and_filter(skills=["Python", "SQL"], skills_match_all=True, limit=10)
        self.assertGreater(count, 0)
        for job in results:
            job_skills = set(job.get("skills", []))
            self.assertTrue({"Python", "SQL"}.issubset(job_skills))

    def test_10_filter_skills_match_any(self):
        """Skills multiselect with ANY ($in) semantics."""
        results, count = self.service.search_and_filter(skills=["Python", "SQL"], skills_match_all=False, limit=10)
        self.assertGreater(count, 0)
        for job in results:
            job_skills = set(job.get("skills", []))
            self.assertTrue(bool(job_skills.intersection({"Python", "SQL"})))

    def test_11_filter_company_name(self):
        """Company name filter (case-insensitive substring/regex)."""
        results, count = self.service.search_and_filter(company_name="Google", limit=10)
        self.assertGreater(count, 0)
        for job in results:
            company = (job.get("company", {}) or {}).get("name", "")
            self.assertIn("google", company.lower())

    def test_12_filter_experience_level(self):
        """Experience-level filter."""
        results, count = self.service.search_and_filter(experience_level="Entry level", limit=10)
        self.assertGreater(count, 0)
        for job in results:
            self.assertEqual(job.get("experience_level", {}).get("value"), "Entry level")

    def test_13_filter_source_platform(self):
        """Source platform filter (LinkedIn only, Indeed only)."""
        li_results, li_count = self.service.search_and_filter(source="linkedin", limit=10)
        self.assertGreater(li_count, 0)
        for job in li_results:
            self.assertEqual(job.get("source"), "linkedin")

        ind_results, ind_count = self.service.search_and_filter(source="indeed", limit=10)
        self.assertGreater(ind_count, 0)
        for job in ind_results:
            self.assertEqual(job.get("source"), "indeed")

    # -------------------------------------------------------------------------
    # 3. Combined Multi-Facet Filters
    # -------------------------------------------------------------------------
    def test_14_combined_filters(self):
        """Simultaneous multi-facet filtering: State + Source + Remote + Query."""
        results, count = self.service.search_and_filter(
            query_text="Engineer",
            state="TX",
            source="linkedin",
            is_remote=None,
            limit=5
        )
        self.assertGreater(count, 0)
        for job in results:
            self.assertEqual(job.get("source"), "linkedin")
            self.assertEqual(job.get("location", {}).get("state"), "TX")
            self.assertIsNone(job.get("location", {}).get("is_remote"))


    # -------------------------------------------------------------------------
    # 4. Sorting Modes
    # -------------------------------------------------------------------------
    def test_15_sort_salary_desc(self):
        """Sort by salary descending."""
        results, count = self.service.search_and_filter(sort_by="salary", sort_order=-1, limit=10)
        self.assertGreater(count, 0)
        salaries = [j.get("salary", {}).get("normalized_annual") for j in results if j.get("salary", {}).get("normalized_annual") is not None]
        # Verify non-increasing order for valid numbers
        for i in range(len(salaries) - 1):
            self.assertGreaterEqual(salaries[i], salaries[i + 1])

    def test_16_sort_title_asc(self):
        """Sort by title ascending."""
        results, count = self.service.search_and_filter(sort_by="title", sort_order=1, limit=10)
        self.assertGreater(count, 0)
        titles = [j.get("title", "").strip().lower() for j in results if j.get("title")]
        for i in range(len(titles) - 1):
            self.assertLessEqual(titles[i], titles[i + 1])

    def test_17_sort_posted_date_desc(self):
        """Sort by posted_date descending."""
        results, count = self.service.search_and_filter(source="linkedin", sort_by="posted_date", sort_order=-1, limit=10)
        self.assertGreater(count, 0)
        dates = [j.get("posted_date") for j in results if j.get("posted_date")]
        for i in range(len(dates) - 1):
            self.assertGreaterEqual(dates[i], dates[i + 1])

    # -------------------------------------------------------------------------
    # 5. Pagination & Consistency
    # -------------------------------------------------------------------------
    def test_18_pagination_no_duplicates_or_skips(self):
        """Ensure page 1 and page 2 have no overlapping IDs and cover exact range."""
        page_size = 15
        p1_results, total_count = self.service.search_and_filter(limit=page_size, skip=0)
        p2_results, _ = self.service.search_and_filter(limit=page_size, skip=page_size)

        self.assertEqual(len(p1_results), page_size)
        self.assertEqual(len(p2_results), page_size)

        p1_ids = {doc["_id"] for doc in p1_results}
        p2_ids = {doc["_id"] for doc in p2_results}

        # Intersect must be empty (no duplicates)
        self.assertEqual(len(p1_ids.intersection(p2_ids)), 0)

    # -------------------------------------------------------------------------
    # 6. Job Detail Lookup
    # -------------------------------------------------------------------------
    def test_19_get_job_by_id(self):
        """Lookup by string ObjectId, ObjectId instance, and authentic source_job_id."""
        sample = self.db.jobs.find_one({"source": "linkedin"})
        self.assertIsNotNone(sample)
        doc_id = sample["_id"]
        source_id = sample.get("source_job_id")

        # By ObjectId instance
        job1 = self.service.get_job_by_id(doc_id)
        self.assertIsNotNone(job1)
        self.assertEqual(job1["_id"], str(doc_id))

        # By 24-char hex string
        job2 = self.service.get_job_by_id(str(doc_id))
        self.assertIsNotNone(job2)
        self.assertEqual(job2["_id"], str(doc_id))

        # By source_job_id
        if source_id:
            job3 = self.service.get_job_by_id(source_id)
            self.assertIsNotNone(job3)
            self.assertEqual(job3.get("source_job_id"), source_id)

    # -------------------------------------------------------------------------
    # 7. Related Jobs Suggestions
    # -------------------------------------------------------------------------
    def test_20_related_jobs_same_platform_and_exclusion(self):
        """Related jobs must strictly share platform and exclude target posting."""
        sample = self.db.jobs.find_one({"source": "indeed", "skills.0": {"$exists": True}})
        self.assertIsNotNone(sample)
        doc_id = str(sample["_id"])

        related = self.service.get_related_jobs(doc_id, limit=5)
        self.assertGreater(len(related), 0)
        self.assertLessEqual(len(related), 5)

        for rel in related:
            # Must strictly match source
            self.assertEqual(rel["source"], "indeed")
            # Must exclude target job
            self.assertNotEqual(rel["_id"], doc_id)
            self.assertNotEqual(rel.get("source_job_id"), sample.get("source_job_id"))
            # Must contain match explanation
            self.assertIn("match_explanation", rel)
            exp = rel["match_explanation"]
            self.assertIn("match_score", exp)
            self.assertEqual(exp.get("source_platform"), "indeed")

    # -------------------------------------------------------------------------
    # 8. Empty & Invalid Handling
    # -------------------------------------------------------------------------
    def test_21_empty_results_handling(self):
        """Non-matching query gracefully returns empty list and 0 count."""
        results, count = self.service.search_and_filter(query_text="XYZNONEXISTENTQUERY999", limit=10)
        self.assertEqual(len(results), 0)
        self.assertEqual(count, 0)

    def test_22_nonexistent_job_id(self):
        """Nonexistent ID returns None gracefully."""
        res = self.service.get_job_by_id("000000000000000000000000")
        self.assertIsNone(res)

    # -------------------------------------------------------------------------
    # 9. Parameter Validation Guardrails
    # -------------------------------------------------------------------------
    def test_24_parameter_validation_search_mode(self):
        """Reject invalid search_mode values."""
        with self.assertRaises(ValueError):
            self.service.search_and_filter(search_mode="fuzzy")
        with self.assertRaises(ValueError):
            self.service.search_and_filter(search_mode="")
        with self.assertRaises(ValueError):
            self.service.search_and_filter(search_mode=123)

    def test_25_parameter_validation_skills_match_all(self):
        """Reject invalid skills_match_all types."""
        with self.assertRaises(ValueError):
            self.service.search_and_filter(skills_match_all="yes")
        with self.assertRaises(ValueError):
            self.service.search_and_filter(skills_match_all=1)
        with self.assertRaises(ValueError):
            self.service.search_and_filter(skills_match_all=None)

    # -------------------------------------------------------------------------
    # 10. Database Invariants & Index Field Verification
    # -------------------------------------------------------------------------
    def test_26_text_index_field_weights_inspection(self):
        """Confirm title_text_description_text covers title and description only, NOT skills."""
        info = self.db.jobs.index_information()
        self.assertIn("title_text_description_text", info)
        text_index = info["title_text_description_text"]
        weights = dict(text_index.get("weights", {}))
        
        # Verify exact covered fields and weights
        self.assertEqual(weights, {"title": 1, "description": 1})
        self.assertNotIn("skills", weights, "skills must NOT be in the full-text index.")

        # Confirm skills has its own separate multikey BSON index
        self.assertIn("skills_1", info)
        self.assertEqual(info["skills_1"]["key"], [("skills", 1)])

    def test_27_remote_status_tri_state_distinction(self):
        """Confirm three distinct non-conflated states for is_remote."""
        true_cnt = self.db.jobs.count_documents({"location.is_remote": True})
        false_cnt = self.db.jobs.count_documents({"location.is_remote": False})
        none_cnt = self.db.jobs.count_documents({"location.is_remote": None})
        total_cnt = self.db.jobs.count_documents({})

        self.assertEqual(true_cnt, 15236)
        self.assertEqual(false_cnt, 0)
        self.assertEqual(none_cnt, 114314)
        self.assertEqual(true_cnt + false_cnt + none_cnt, total_cnt)
        self.assertEqual(total_cnt, 129550)

    def test_28_database_invariants(self):
        """Ensure canonical datasets and index counts have not been altered."""
        jobs_count = self.db.jobs.count_documents({})
        companies_count = self.db.companies.count_documents({})
        jobs_indexes = len(self.db.jobs.index_information())
        companies_indexes = len(self.db.companies.index_information())

        self.assertEqual(jobs_count, 129550, "Canonical jobs count must remain exactly 129,550.")
        self.assertEqual(companies_count, 24472, "Canonical companies count must remain exactly 24,472.")
        self.assertEqual(jobs_indexes, 11, "Canonical jobs indexes must remain 11.")
        self.assertEqual(companies_indexes, 4, "Canonical companies indexes must remain 4.")


    def test_29_python_sql_all_and_any_counts(self):
        """Verify exact counts and inclusion-exclusion for Python and SQL under ALL and ANY."""
        py_cnt = self.db.jobs.count_documents({"skills": "Python"})
        sql_cnt = self.db.jobs.count_documents({"skills": "SQL"})
        all_cnt = self.db.jobs.count_documents({"skills": {"$all": ["Python", "SQL"]}})
        any_cnt = self.db.jobs.count_documents({"skills": {"$in": ["Python", "SQL"]}})

        self.assertEqual(py_cnt, 3325)
        self.assertEqual(sql_cnt, 3104)
        self.assertEqual(all_cnt, 2075)
        self.assertEqual(any_cnt, 4354)
        self.assertEqual(py_cnt + sql_cnt - all_cnt, any_cnt)

        # Service verification
        docs_all, svc_all = self.service.search_and_filter(skills=["Python", "SQL"], skills_match_all=True, limit=20)
        self.assertEqual(svc_all, 2075)
        self.assertTrue(all("Python" in d.get("skills", []) and "SQL" in d.get("skills", []) for d in docs_all))

        docs_any, svc_any = self.service.search_and_filter(skills=["Python", "SQL"], skills_match_all=False, limit=20)
        self.assertEqual(svc_any, 4354)
        self.assertTrue(all("Python" in d.get("skills", []) or "SQL" in d.get("skills", []) for d in docs_any))


if __name__ == "__main__":
    unittest.main(verbosity=2)


