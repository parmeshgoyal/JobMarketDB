"""
JobMarketDB - Phase 6 Step 2 Focused Verification Suite

Tests:
1. Streamlit app and multi-page structure integrity (syntax and compilation checks).
2. Shared UI components with normal, empty, and missing-data inputs.
3. Plotly visualization builders with representative aggregation data and empty/None data.
4. Input immutability verification across all Plotly builders.
5. Database invariant check (129,550 jobs, 24,472 companies, 11 jobs indexes, 4 companies indexes).
"""

import copy
import os
import py_compile
import sys
import unittest
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_database
from utils.ui_components import (
    US_STATES,
    render_platform_badge,
)
from utils.plots import (
    apply_theme,
    create_empty_chart,
    create_horizontal_ranking_chart,
    create_salary_distribution_chart,
    create_skills_demand_chart,
    create_geographic_comparison_chart,
    create_us_choropleth_map,
    create_platform_comparison_chart,
)
import plotly.graph_objects as go


class Phase6Step2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = get_database()
        cls.expected_jobs_count = 129550
        cls.expected_companies_count = 24472
        cls.expected_jobs_indexes = 11
        cls.expected_companies_indexes = 4

    # -------------------------------------------------------------------------
    # 1. Multi-Page Structure & Compilation Integrity
    # -------------------------------------------------------------------------
    def test_app_and_page_files_exist_and_compile(self):
        """Verify app.py and all 6 page placeholders exist and compile without syntax errors."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        page_files = [
            os.path.join(base_dir, "app.py"),
            os.path.join(base_dir, "pages", "1_Job_Search.py"),
            os.path.join(base_dir, "pages", "2_Skills_Analytics.py"),
            os.path.join(base_dir, "pages", "3_Salary_Analytics.py"),
            os.path.join(base_dir, "pages", "4_Company_and_Geography.py"),
            os.path.join(base_dir, "pages", "5_Platform_Comparison.py"),
            os.path.join(base_dir, "pages", "6_CRUD_Demo.py"),
        ]

        for filepath in page_files:
            self.assertTrue(os.path.exists(filepath), f"Missing page file: {filepath}")
            # Ensure file compiles cleanly
            py_compile.compile(filepath, doraise=True)

    # -------------------------------------------------------------------------
    # 2. Shared UI Component Helpers
    # -------------------------------------------------------------------------
    def test_us_states_tuple(self):
        """Verify US_STATES contains all 50 states + DC (51 jurisdictions)."""
        self.assertEqual(len(US_STATES), 51)
        self.assertIn("CA", US_STATES)
        self.assertIn("NY", US_STATES)
        self.assertIn("DC", US_STATES)

    def test_render_platform_badge_inputs(self):
        """Test platform badge generator across valid, edge-case, empty, and None inputs."""
        # Normal inputs
        li_badge = render_platform_badge("linkedin")
        self.assertIn("jmdb-badge-linkedin", li_badge)
        self.assertIn("LinkedIn", li_badge)

        in_badge = render_platform_badge("indeed")
        self.assertIn("jmdb-badge-indeed", in_badge)
        self.assertIn("Indeed", in_badge)

        comb_badge = render_platform_badge("combined")
        self.assertIn("jmdb-badge-neutral", comb_badge)

        # Empty / None / Missing inputs
        none_badge = render_platform_badge(None)
        self.assertIn("jmdb-badge-neutral", none_badge)
        self.assertIn("Unknown", none_badge)

        empty_badge = render_platform_badge("")
        self.assertIn("jmdb-badge-neutral", empty_badge)

    # -------------------------------------------------------------------------
    # 3. Plotly Visualization Builders - Representative & Empty Data
    # -------------------------------------------------------------------------
    def test_create_empty_chart(self):
        """Verify empty chart builder returns a valid Plotly Figure with annotation."""
        fig = create_empty_chart(title="Test Empty", message="Custom empty message")
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(fig.layout.title.text, "<b>Test Empty</b>")
        self.assertTrue(any("Custom empty message" in str(ann.text) for ann in fig.layout.annotations))

    def test_create_horizontal_ranking_chart(self):
        """Test horizontal ranking chart with representative data and empty data."""
        data = [
            {"skill": "Python", "count": 3104},
            {"skill": "SQL", "count": 2850},
            {"skill": "AWS", "count": 1940},
        ]
        fig = create_horizontal_ranking_chart(
            items=data,
            label_key="skill",
            value_key="count",
            title="Top Skills",
            x_axis_title="Postings",
        )
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.data), 1)
        self.assertEqual(fig.data[0].type, "bar")

        # Test empty data
        empty_fig = create_horizontal_ranking_chart([], label_key="skill", value_key="count")
        self.assertIsInstance(empty_fig, go.Figure)
        none_fig = create_horizontal_ranking_chart(None, label_key="skill", value_key="count")
        self.assertIsInstance(none_fig, go.Figure)

    def test_create_salary_distribution_chart(self):
        """Test salary distribution chart with Operation 11 bucket format and empty data."""
        buckets = [
            {"salary_bucket": "<60000", "count": 420, "avg_salary": 48500.0},
            {"salary_bucket": "60000-79999", "count": 1850, "avg_salary": 72000.0},
            {"salary_bucket": "80000-99999", "count": 3400, "avg_salary": 89500.0},
            {"salary_bucket": "100000-119999", "count": 5486, "avg_salary": 110200.0},
            {"salary_bucket": "120000-159999", "count": 7820, "avg_salary": 138000.0},
            {"salary_bucket": ">=160000", "count": 22798, "avg_salary": 245000.0},
        ]
        # Test direct list
        fig1 = create_salary_distribution_chart(buckets, title="Salary Tiers")
        self.assertIsInstance(fig1, go.Figure)
        self.assertEqual(len(fig1.data[0].x), 6)

        # Test dictionary containing buckets key
        fig2 = create_salary_distribution_chart({"buckets": buckets}, title="Salary Tiers")
        self.assertIsInstance(fig2, go.Figure)

        # Test empty / None
        empty_fig = create_salary_distribution_chart([])
        self.assertIsInstance(empty_fig, go.Figure)
        none_fig = create_salary_distribution_chart(None)
        self.assertIsInstance(none_fig, go.Figure)

    def test_create_skills_demand_chart(self):
        """Test skills demand chart with platform branding and empty data."""
        skills_indeed = [
            {"skill": "Python", "count": 1948, "percentage": 34.09},
            {"skill": "SQL", "count": 1720, "percentage": 30.10},
        ]
        fig_indeed = create_skills_demand_chart(skills_indeed, platform="indeed")
        self.assertIsInstance(fig_indeed, go.Figure)
        self.assertEqual(len(fig_indeed.data), 1)

        skills_linkedin = [
            {"skill": "Information Technology", "count": 45200, "percentage": 36.5},
            {"skill": "Management", "count": 31000, "percentage": 25.0},
        ]
        fig_li = create_skills_demand_chart(skills_linkedin, platform="linkedin")
        self.assertIsInstance(fig_li, go.Figure)

        # Test empty / None
        self.assertIsInstance(create_skills_demand_chart([]), go.Figure)
        self.assertIsInstance(create_skills_demand_chart(None), go.Figure)

    def test_create_geographic_comparison_chart(self):
        """Test geographic location chart with Operation 10 format."""
        locations = [
            {"state": "CA", "count": 19850, "percentage": 15.3},
            {"state": "TX", "count": 14200, "percentage": 11.0},
            {"state": "NY", "count": 11500, "percentage": 8.9},
        ]
        fig = create_geographic_comparison_chart(locations)
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.data[0].y), 3)

        # Test empty / None
        self.assertIsInstance(create_geographic_comparison_chart([]), go.Figure)
        self.assertIsInstance(create_geographic_comparison_chart(None), go.Figure)

    def test_create_us_choropleth_map(self):
        """Test US choropleth map builder."""
        locations = [
            {"state": "CA", "count": 19850},
            {"state": "TX", "count": 14200},
            {"state": "NY", "count": 11500},
        ]
        fig = create_us_choropleth_map(locations)
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(fig.data[0].type, "choropleth")

        # Test empty / None
        self.assertIsInstance(create_us_choropleth_map([]), go.Figure)
        self.assertIsInstance(create_us_choropleth_map(None), go.Figure)

    def test_create_platform_comparison_chart(self):
        """Test platform comparison chart across volume, salary coverage, and remote rate metrics."""
        comp_data = {
            "linkedin": {
                "total_postings": 123835,
                "salary_coverage_pct": 29.12,
                "remote_pct": 12.3,
            },
            "indeed": {
                "total_postings": 5715,
                "salary_coverage_pct": 100.0,
                "remote_pct": 0.0,
            },
        }

        fig_vol = create_platform_comparison_chart(comp_data, metric="volume")
        self.assertIsInstance(fig_vol, go.Figure)
        self.assertEqual(len(fig_vol.data[0].x), 2)

        fig_sal = create_platform_comparison_chart(comp_data, metric="salary_coverage")
        self.assertIsInstance(fig_sal, go.Figure)

        fig_rem = create_platform_comparison_chart(comp_data, metric="remote_rate")
        self.assertIsInstance(fig_rem, go.Figure)

        # Test empty / None
        self.assertIsInstance(create_platform_comparison_chart(None), go.Figure)

    # -------------------------------------------------------------------------
    # 4. Input Immutability Tests
    # -------------------------------------------------------------------------
    def test_chart_builders_do_not_mutate_inputs(self):
        """Confirm that chart builders never mutate the data collections passed to them."""
        # Test 1: Ranking data
        original_ranking = [
            {"name": "Company A", "count": 100},
            {"name": "Company B", "count": 50},
            {"name": "Company C", "count": 25},
        ]
        frozen_ranking = copy.deepcopy(original_ranking)
        create_horizontal_ranking_chart(original_ranking, "name", "count")
        self.assertEqual(original_ranking, frozen_ranking, "create_horizontal_ranking_chart mutated input list!")

        # Test 2: Salary buckets
        original_buckets = [
            {"salary_bucket": "<60000", "count": 100, "avg_salary": 50000},
            {"salary_bucket": ">=160000", "count": 200, "avg_salary": 180000},
        ]
        frozen_buckets = copy.deepcopy(original_buckets)
        create_salary_distribution_chart(original_buckets)
        self.assertEqual(original_buckets, frozen_buckets, "create_salary_distribution_chart mutated input list!")

        # Test 3: Skills data
        original_skills = [
            {"skill": "Python", "count": 500, "percentage": 25.0},
            {"skill": "Java", "count": 300, "percentage": 15.0},
        ]
        frozen_skills = copy.deepcopy(original_skills)
        create_skills_demand_chart(original_skills, platform="indeed")
        self.assertEqual(original_skills, frozen_skills, "create_skills_demand_chart mutated input list!")

        # Test 4: Locations data
        original_locations = [
            {"state": "CA", "count": 1000, "percentage": 20.0},
            {"state": "NY", "count": 800, "percentage": 16.0},
        ]
        frozen_locations = copy.deepcopy(original_locations)
        create_geographic_comparison_chart(original_locations)
        create_us_choropleth_map(original_locations)
        self.assertEqual(original_locations, frozen_locations, "Geographic chart builders mutated input list!")

        # Test 5: Platform comparison
        original_comp = {
            "linkedin": {"total_postings": 123835, "salary_coverage_pct": 29.12, "remote_pct": 12.3},
            "indeed": {"total_postings": 5715, "salary_coverage_pct": 100.0, "remote_pct": 0.0},
        }
        frozen_comp = copy.deepcopy(original_comp)
        create_platform_comparison_chart(original_comp, metric="volume")
        self.assertEqual(original_comp, frozen_comp, "create_platform_comparison_chart mutated input dict!")

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
