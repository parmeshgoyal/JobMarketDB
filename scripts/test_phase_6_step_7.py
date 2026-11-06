"""
Phase 6 Step 7 Unit & Integration Test Suite — Salary Analytics
=================================================================
Tests for the Salary Analytics dashboard backend covering:
  - Salary coverage and missing-value counts
  - Median and mean calculations (unadjusted vs threshold-adjusted)
  - Salary bucket distributions
  - Source/platform separation
  - Salary interval (pay_period) handling
  - Salary range and filter correctness
  - Experience-level and job-title comparisons
  - Missing salary handling (never treated as zero)
  - Outlier audit transparency
  - Indeed estimated_midpoint handling
  - Invalid inputs and empty results
  - Database immutability

Database: mongodb://localhost:27017/jobmarketdb
Collections (read-only): jobs (129,550), companies (24,472)
"""

import sys
import os
import unittest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.connection import get_database, verify_connection
from analytics.service import JobMarketAnalyticsService


class Phase6Step7SalaryAnalyticsTests(unittest.TestCase):
    """
    Unit and integration tests for Phase 6 Step 7 salary analytics.
    All tests are read-only against canonical collections.
    """

    @classmethod
    def setUpClass(cls):
        verify_connection()
        cls.db = get_database()
        cls.svc = JobMarketAnalyticsService(db=cls.db)
        cls.overview = cls.svc.get_salary_overview()

    # ─── Test 01: Salary Coverage Counts ─────────────────────────────────────
    def test_01_salary_coverage_counts(self):
        """Verify platform-level salary coverage counts match direct DB counts."""
        li = self.overview["linkedin"]
        ind = self.overview["indeed"]

        # LinkedIn normalized_annual coverage
        direct_li = self.db.jobs.count_documents({
            "source": "linkedin",
            "salary.normalized_annual": {"$exists": True, "$ne": None}
        })
        self.assertEqual(li["postings_with_normalized_annual"], direct_li,
                         "LinkedIn salary count mismatch between service and direct DB query")

        # Indeed estimated_midpoint coverage
        direct_ind = self.db.jobs.count_documents({
            "source": "indeed",
            "salary.estimated_midpoint": {"$exists": True, "$ne": None}
        })
        self.assertEqual(ind["postings_with_estimated_midpoint"], direct_ind,
                         "Indeed midpoint count mismatch")

    # ─── Test 02: Missing Salary Counts Are Consistent ───────────────────────
    def test_02_missing_salary_accounts_for_all_linkedin(self):
        """LinkedIn: with_salary + missing_salary = total_linkedin_postings."""
        li = self.overview["linkedin"]
        self.assertEqual(
            li["postings_with_normalized_annual"] + li["postings_missing_salary"],
            li["total_postings"],
            "LinkedIn salary coverage + missing salary must equal total LinkedIn postings",
        )

    # ─── Test 03: Indeed Has Zero Normalized Annual ───────────────────────────
    def test_03_indeed_normalized_annual_strictly_zero(self):
        """Indeed salary.normalized_annual must be null for ALL Indeed records."""
        ind = self.overview["indeed"]
        self.assertEqual(ind["postings_with_normalized_annual"], 0,
                         "Indeed must have 0 records with non-null salary.normalized_annual")

        # Verify directly
        direct = self.db.jobs.count_documents({
            "source": "indeed",
            "salary.normalized_annual": {"$ne": None}
        })
        self.assertEqual(direct, 0, "Direct DB query: Indeed must have 0 normalized_annual records")

    # ─── Test 04: LinkedIn Outlier Count ──────────────────────────────────────
    def test_04_linkedin_outlier_count_is_38(self):
        """38 LinkedIn records have normalized_annual > $1,000,000 (audit finding)."""
        outlier_audit = self.overview["outlier_audit"]
        self.assertEqual(outlier_audit["total_outliers"], 38,
                         "Expected exactly 38 outliers > $1M as per prior audit")
        self.assertTrue(outlier_audit["all_from_linkedin"],
                        "All outliers must be LinkedIn records")

        direct = self.db.jobs.count_documents({"salary.normalized_annual": {"$gt": 1_000_000}})
        self.assertEqual(direct, 38, "Direct DB count of outliers > $1M must be 38")

    # ─── Test 05: Outlier Audit Classification Sums to 38 ────────────────────
    def test_05_outlier_classification_sums_to_38(self):
        """Sum of all outlier classification counts must equal 38."""
        classification = self.overview["outlier_audit"]["classification"]
        total_classified = sum(classification.values())
        self.assertEqual(total_classified, 38,
                         f"Outlier classification sum {total_classified} != 38")
        self.assertEqual(classification["hourly_conversion_artifacts"], 19)
        self.assertEqual(classification["recruiter_entry_errors"], 10)
        self.assertEqual(classification["task_fee_or_other"], 1)
        self.assertEqual(classification["unresolved_internship_stipends"], 8)

    # ─── Test 06: Unadjusted Mean Is Distorted by Outliers ───────────────────
    def test_06_unadjusted_mean_materially_greater_than_adjusted(self):
        """Unadjusted mean must be materially higher than threshold-adjusted mean."""
        li = self.overview["linkedin"]
        unadj_mean = li["unadjusted"]["mean"]
        adj_mean = li["threshold_adjusted"]["mean"]
        self.assertIsNotNone(unadj_mean, "Unadjusted mean must not be None")
        self.assertIsNotNone(adj_mean, "Threshold-adjusted mean must not be None")
        self.assertGreater(unadj_mean, adj_mean,
                           "Unadjusted mean must exceed threshold-adjusted mean due to outliers")
        # The distortion should be material (> $50k difference)
        self.assertGreater(unadj_mean - adj_mean, 50_000,
                           "Outlier distortion must be > $50k on the mean")

    # ─── Test 07: Threshold-Adjusted Count = Total - 38 Outliers ─────────────
    def test_07_threshold_adjusted_count_excludes_38(self):
        """Threshold-adjusted count must equal total salary records minus 38 outliers."""
        li = self.overview["linkedin"]
        self.assertEqual(
            li["threshold_adjusted"]["count"],
            li["unadjusted"]["count"] - li["threshold_adjusted"]["excluded_outlier_count"],
            "adjusted_count must equal unadjusted_count minus excluded_outlier_count",
        )
        self.assertEqual(li["threshold_adjusted"]["excluded_outlier_count"], 38)

    # ─── Test 08: Median Is Robust (Threshold-Adjusted Median < Adjusted Mean) ─
    def test_08_median_reasonable_relative_to_adjusted_mean(self):
        """Threshold-adjusted median must be < adjusted mean and > 0."""
        li = self.overview["linkedin"]
        adj_median = li["threshold_adjusted"]["approx_median"]
        adj_mean = li["threshold_adjusted"]["mean"]
        self.assertIsNotNone(adj_median)
        self.assertGreater(adj_median, 0)
        # Median and mean should be within 3x of each other for a salary distribution
        self.assertLess(adj_median, adj_mean * 3)
        self.assertGreater(adj_median, adj_mean / 3)

    # ─── Test 09: Indeed Midpoint Statistics Are Plausible ───────────────────
    def test_09_indeed_midpoint_statistics_plausible(self):
        """Indeed estimated_midpoint stats must be within plausible salary bounds."""
        em = self.overview["indeed"]["estimated_midpoint"]
        self.assertIsNotNone(em["mean"])
        self.assertIsNotNone(em["approx_median"])
        self.assertGreater(em["mean"], 0)
        self.assertGreater(em["approx_median"], 0)
        # Indeed midpoints are derived from QUERY_BUCKET bands (verified range: $70k–$175k)
        self.assertGreaterEqual(em["min_val"], 60_000,
                                "Indeed midpoints must be at least $60,000 (bucket bands)")
        self.assertLessEqual(em["max_val"], 200_000,
                             "Indeed midpoints must be <= $200k (bucket bands)")

    # ─── Test 10: Salary Coverage Percentage Calculations ────────────────────
    def test_10_salary_coverage_percentage_correct(self):
        """LinkedIn salary_coverage_pct matches manual calculation."""
        li = self.overview["linkedin"]
        expected_pct = round(li["postings_with_normalized_annual"] / li["total_postings"] * 100, 2)
        self.assertAlmostEqual(li["salary_coverage_pct"], expected_pct, places=1,
                               msg="Salary coverage percentage mismatch")
        # Should be approximately 29.12%
        self.assertAlmostEqual(li["salary_coverage_pct"], 29.12, delta=0.5,
                               msg="LinkedIn salary coverage should be ~29.12%")

    # ─── Test 11: Pay Period Breakdown Covers All LinkedIn Salary Records ─────
    def test_11_pay_period_breakdown_complete(self):
        """Sum of pay_period counts must equal total LinkedIn salary records."""
        li = self.overview["linkedin"]
        pp_total = sum(p["count"] for p in li["pay_period_breakdown"])
        self.assertEqual(pp_total, li["postings_with_normalized_annual"],
                         "Pay period counts must sum to total LinkedIn salary records")

        # Verify YEARLY and HOURLY are present (known data)
        periods = {p["pay_period"] for p in li["pay_period_breakdown"]}
        self.assertIn("YEARLY", periods, "YEARLY pay_period must be present")
        self.assertIn("HOURLY", periods, "HOURLY pay_period must be present")

    # ─── Test 12: Salary Bucket Distribution Counts ───────────────────────────
    def test_12_salary_bucket_distribution(self):
        """Salary bucket distribution returns correct canonical buckets."""
        dist = self.svc.get_salary_distribution()
        buckets = dist.get("buckets", [])
        self.assertGreater(len(buckets), 0, "Salary bucket distribution must return at least one bucket")

        # Verify expected canonical buckets are present
        bucket_names = {b["salary_bucket"] for b in buckets}
        expected_buckets = {"<80000", "80000-99999", "100000-119999"}
        for eb in expected_buckets:
            self.assertIn(eb, bucket_names, f"Expected bucket '{eb}' not in distribution")

        # Total bucket count must match individual platform counts
        for b in buckets:
            self.assertEqual(b["total_count"], b["linkedin_count"] + b["indeed_count"],
                             f"Bucket {b['salary_bucket']}: total != linkedin + indeed")

    # ─── Test 13: Salary By Experience Level — LinkedIn Only ─────────────────
    def test_13_salary_by_experience_level_linkedin_only(self):
        """Experience level salary data is LinkedIn-only and contains expected levels."""
        exp = self.svc.get_salary_by_experience()
        self.assertEqual(exp["source"], "linkedin")
        levels = exp.get("experience_levels", [])
        self.assertGreater(len(levels), 0, "Must return at least one experience level")

        level_names = {r["experience_level"] for r in levels}
        # Verify known LinkedIn experience levels and Unclassified are present
        for expected in ["Entry level", "Mid-Senior level", "Director", "Executive", "Associate", "Internship", "Unclassified"]:
            self.assertIn(expected, level_names, f"'{expected}' must be in experience levels")

        # Verify complete population sums across all 7 cohorts
        total_postings_sum = sum(r["total_postings"] for r in levels)
        salary_bearing_sum = sum(r["unadjusted_count"] for r in levels)
        adjusted_sum = sum(r["adjusted_count"] for r in levels)
        outlier_sum = sum(r["outlier_count"] for r in levels)

        self.assertEqual(total_postings_sum, 123835, "Sum of total_postings across experience levels must equal 123,835")
        self.assertEqual(salary_bearing_sum, 36059, "Sum of salary-bearing postings must equal 36,059")
        self.assertEqual(adjusted_sum, 36021, "Sum of threshold-adjusted postings must equal 36,021")
        self.assertEqual(outlier_sum, 38, "Sum of outliers must equal 38")

    # ─── Test 14: Experience Level Sorted by Adjusted Mean Descending ─────────
    def test_14_experience_level_sorted_descending(self):
        """Experience levels must be sorted by threshold-adjusted mean, descending."""
        exp = self.svc.get_salary_by_experience()
        levels = exp.get("experience_levels", [])
        adj_means = [r["adjusted_mean"] for r in levels if r["adjusted_mean"] is not None]
        self.assertEqual(adj_means, sorted(adj_means, reverse=True),
                         "Experience levels must be sorted by adjusted_mean descending")

    # ─── Test 15: Executive Mean > Entry Level Mean (Adjusted) ───────────────
    def test_15_executive_salary_exceeds_entry_level(self):
        """Executive threshold-adjusted mean must exceed Entry level mean."""
        exp = self.svc.get_salary_by_experience()
        levels = {r["experience_level"]: r for r in exp.get("experience_levels", [])}
        if "Executive" in levels and "Entry level" in levels:
            exec_mean = levels["Executive"]["adjusted_mean"] or 0
            entry_mean = levels["Entry level"]["adjusted_mean"] or 0
            self.assertGreater(exec_mean, entry_mean,
                               "Executive adj_mean must exceed Entry level adj_mean")

    # ─── Test 16: Salary By State Returns Validated State Codes ─────────────
    def test_16_salary_by_state_valid_codes(self):
        """State salary data returns valid 2-letter US state codes."""
        states = self.svc.get_salary_by_state(limit=10, min_postings=50)
        state_rows = states.get("states", [])
        self.assertGreater(len(state_rows), 0, "Must return at least one state")
        for row in state_rows:
            self.assertEqual(len(row["state"]), 2, f"State code '{row['state']}' is not 2 letters")
            self.assertTrue(row["state"].isupper(), f"State code '{row['state']}' must be uppercase")

    # ─── Test 17: Min Postings Filter Respected ──────────────────────────────
    def test_17_state_min_postings_filter_respected(self):
        """States with fewer than min_postings salary records must be excluded."""
        states = self.svc.get_salary_by_state(limit=51, min_postings=500)
        for row in states.get("states", []):
            self.assertGreaterEqual(row["unadjusted_count"], 500,
                                    f"State {row['state']} violates min_postings=500 filter")

    # ─── Test 18: Salary By Title — Min Postings Filter ─────────────────────
    def test_18_salary_by_title_min_postings_filter(self):
        """Title salary data respects min_postings threshold."""
        titles = self.svc.get_salary_by_title(limit=20, min_postings=20)
        for row in titles.get("titles", []):
            self.assertGreaterEqual(row["count"], 20,
                                    f"Title '{row['title']}' violates min_postings=20 filter")

    # ─── Test 19: Salary Histogram LinkedIn ──────────────────────────────────
    def test_19_salary_histogram_linkedin(self):
        """LinkedIn histogram returns 36,021 values (36,059 total minus 38 outliers > $1M)."""
        hist = self.svc.get_salary_histogram(source="linkedin")
        self.assertEqual(hist["source"], "linkedin")
        self.assertIsInstance(hist["values"], list)
        # Threshold-adjusted: should be 36,021 (36,059 - 38 outliers)
        self.assertEqual(hist["count"], 36021,
                         "LinkedIn threshold-adjusted histogram must have 36,021 values")
        # All values should be <= $1M
        for v in hist["values"]:
            self.assertLessEqual(v, 1_000_000,
                                 "LinkedIn histogram (threshold-adjusted) must contain no value > $1M")

    # ─── Test 20: Salary Histogram Indeed ────────────────────────────────────
    def test_20_salary_histogram_indeed(self):
        """Indeed histogram returns estimated_midpoint values for all 5,715 records."""
        hist = self.svc.get_salary_histogram(source="indeed", outlier_threshold=None)
        self.assertEqual(hist["source"], "indeed")
        self.assertEqual(hist["count"], 5715,
                         "Indeed histogram must have 5,715 estimated_midpoint values")
        # All Indeed midpoints in known range $70k–$175k
        for v in hist["values"]:
            self.assertGreaterEqual(v, 60_000, "Indeed midpoint below expected minimum")
            self.assertLessEqual(v, 200_000, "Indeed midpoint above expected maximum")

    # ─── Test 21: Histogram Statistics Computed Correctly ───────────────────
    def test_21_histogram_stats_match_values(self):
        """Histogram stats (mean, median, min, max) must match the returned values array."""
        hist = self.svc.get_salary_histogram(source="linkedin")
        values = hist["values"]
        if not values:
            self.skipTest("No histogram values available")

        stats = hist["stats"]
        self.assertAlmostEqual(stats["min_val"], min(values), delta=1.0, msg="min_val mismatch")
        self.assertAlmostEqual(stats["max_val"], max(values), delta=1.0, msg="max_val mismatch")
        computed_mean = sum(values) / len(values)
        self.assertAlmostEqual(stats["mean"], computed_mean, delta=1.0, msg="mean mismatch")

    # ─── Test 22: Invalid Source Raises ValueError ───────────────────────────
    def test_22_invalid_histogram_source_raises(self):
        """get_salary_histogram with invalid source must raise ValueError."""
        with self.assertRaises(ValueError):
            self.svc.get_salary_histogram(source="twitter")

    # ─── Test 23: Invalid Outlier Threshold Raises ValueError ────────────────
    def test_23_invalid_outlier_threshold_raises(self):
        """get_salary_by_experience with outlier_threshold <= 0 must raise ValueError."""
        with self.assertRaises(ValueError):
            self.svc.get_salary_by_experience(outlier_threshold=0)
        with self.assertRaises(ValueError):
            self.svc.get_salary_by_experience(outlier_threshold=-1)

    # ─── Test 24: Invalid Limit Raises ValueError ────────────────────────────
    def test_24_invalid_limit_raises(self):
        """get_salary_by_state and get_salary_by_title with limit <= 0 must raise ValueError."""
        with self.assertRaises(ValueError):
            self.svc.get_salary_by_state(limit=0)
        with self.assertRaises(ValueError):
            self.svc.get_salary_by_state(limit=-1)
        with self.assertRaises(ValueError):
            self.svc.get_salary_by_title(limit=0)
        with self.assertRaises(ValueError):
            self.svc.get_salary_by_title(limit=-5)

    # ─── Test 25: Min Postings <= 0 Raises ValueError ────────────────────────
    def test_25_invalid_min_postings_raises(self):
        """min_postings=0 must raise ValueError."""
        with self.assertRaises(ValueError):
            self.svc.get_salary_by_state(min_postings=0)
        with self.assertRaises(ValueError):
            self.svc.get_salary_by_title(min_postings=0)

    # ─── Test 26: High Min Postings Returns Empty ────────────────────────────
    def test_26_very_high_min_postings_returns_empty(self):
        """A very high min_postings filter returns empty lists gracefully."""
        states = self.svc.get_salary_by_state(limit=10, min_postings=999_999)
        self.assertEqual(states.get("states", []), [],
                         "Very high min_postings must return empty list, not raise error")

        titles = self.svc.get_salary_by_title(limit=10, min_postings=999_999)
        self.assertEqual(titles.get("titles", []), [],
                         "Very high min_postings must return empty list, not raise error")

    # ─── Test 27: Ground Truth — Verified LinkedIn Statistics ────────────────
    def test_27_ground_truth_linkedin_statistics(self):
        """Verify against independently audited LinkedIn salary figures."""
        li = self.overview["linkedin"]
        # Audited: 36,059 total salary records, 38 outliers > $1M
        self.assertEqual(li["postings_with_normalized_annual"], 36059)
        self.assertEqual(li["threshold_adjusted"]["count"], 36021)
        self.assertEqual(li["threshold_adjusted"]["excluded_outlier_count"], 38)

        # Unadjusted mean should be ~$205k (per data inspection)
        unadj_mean = li["unadjusted"]["mean"]
        self.assertAlmostEqual(unadj_mean, 205407, delta=1000,
                               msg="Unadjusted mean out of expected range ~$205,407")

        # Adjusted mean should be ~$95,515 (per data inspection)
        adj_mean = li["threshold_adjusted"]["mean"]
        self.assertAlmostEqual(adj_mean, 95515, delta=500,
                               msg="Threshold-adjusted mean out of expected range ~$95,515")

    # ─── Test 28: Ground Truth — Verified Indeed Midpoint Statistics ──────────
    def test_28_ground_truth_indeed_midpoint_statistics(self):
        """Verify against independently audited Indeed estimated_midpoint figures."""
        ind = self.overview["indeed"]
        em = ind["estimated_midpoint"]
        # Audited: 5,715 records, mean ~$116,501, median ~$110,000
        self.assertEqual(em["count"], 5715)
        self.assertAlmostEqual(em["mean"], 116501, delta=500,
                               msg="Indeed midpoint mean out of expected range ~$116,501")
        self.assertAlmostEqual(em["approx_median"], 110000, delta=5000,
                               msg="Indeed midpoint median out of expected range ~$110,000")

    # ─── Test 29: Provenance Warning Present in Overview ─────────────────────
    def test_29_provenance_warning_present(self):
        """Overview result must contain provenance_warning field."""
        self.assertIn("provenance_warning", self.overview,
                      "Salary overview must include provenance_warning field")
        self.assertIn("NEVER", self.overview["provenance_warning"],
                      "Provenance warning must explicitly state figures are never combined")

    # ─── Test 30: Database Immutability (Invariants) ─────────────────────────
    def test_30_database_invariants_preserved(self):
        """Confirm canonical collections and indexes are strictly untouched."""
        jobs_count = self.db.jobs.count_documents({})
        companies_count = self.db.companies.count_documents({})
        jobs_indexes = len(self.db.jobs.index_information())
        companies_indexes = len(self.db.companies.index_information())

        self.assertEqual(jobs_count, 129_550,
                         f"jobs collection count changed: expected 129,550, got {jobs_count}")
        self.assertEqual(companies_count, 24_472,
                         f"companies collection count changed: expected 24,472, got {companies_count}")
        self.assertEqual(jobs_indexes, 11,
                         f"jobs index count changed: expected 11, got {jobs_indexes}")
        self.assertEqual(companies_indexes, 4,
                         f"companies index count changed: expected 4, got {companies_indexes}")
        self.assertEqual(jobs_indexes + companies_indexes, 15,
                         "Total index count must remain 15")

        collections = set(self.db.list_collection_names())
        self.assertTrue({"jobs", "companies"}.issubset(collections) and collections.issubset({"jobs", "companies", "demo_postings"}),
                        "No unauthorized collections must have been created")


if __name__ == "__main__":
    unittest.main(verbosity=2)
