"""
JobMarketDB — Phase 7 Stage 1 Focused Test Suite
Tests:
1. utils/style.css existence, CSS design tokens, and spacing scale definitions.
2. utils/ui_components.py backward compatibility with Phase 6 signatures.
3. utils/ui_components.py new Phase 7 editorial components (EditorialHeader, EditorialStatCard, etc.).
4. utils/ui_components.py HTML/XSS sanitization on user-supplied content.
5. utils/plots.py THEME tokens (warm ivory, white card, charcoal, sage, olive).
6. utils/plots.py plot builders with normal, empty, and None inputs.
7. utils/plots.py input immutability.
8. MongoDB canonical invariants strictly preserved (129,550 jobs, 24,472 companies, 15 indexes).
"""

import copy
import os
import sys
import unittest
from typing import Any, Dict, List
import plotly.graph_objects as go

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_database
from utils.ui_components import (
    US_STATES,
    load_custom_css,
    render_header,
    render_metric_card,
    render_platform_badge,
    render_state_selector,
    render_pagination_controls,
    render_empty_state,
    render_loading_state,
    render_error_state,
    render_callout,
    render_editorial_header,
    EditorialHeader,
    render_editorial_stat_card,
    EditorialStatCard,
    render_editorial_callout,
    EditorialCallout,
    render_editorial_filter_bar,
    EditorialFilterBar,
    render_elevated_job_card,
    ElevatedJobCard,
)
from utils.plots import (
    THEME,
    apply_theme,
    create_empty_chart,
    create_horizontal_ranking_chart,
    create_salary_distribution_chart,
    create_skills_demand_chart,
    create_geographic_comparison_chart,
    create_us_choropleth_map,
    create_platform_comparison_chart,
    create_grouped_bar_chart,
    create_shared_employers_chart,
    create_platform_salary_bucket_chart,
)


class TestPhase7Stage1SharedFoundation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = get_database()
        cls.expected_jobs_count = 129550
        cls.expected_companies_count = 24472
        cls.expected_jobs_indexes = 11
        cls.expected_companies_indexes = 4

    # -------------------------------------------------------------------------
    # 1. CSS Design Tokens & Stylesheet Integrity
    # -------------------------------------------------------------------------
    def test_style_css_tokens(self):
        """Verify style.css contains all required Phase 7 editorial tokens and font stacks."""
        css_path = os.path.join(os.path.dirname(__file__), "..", "utils", "style.css")
        self.assertTrue(os.path.exists(css_path), "utils/style.css does not exist!")
        with open(css_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_tokens = [
            "--canvas-ivory: #FAF8F5;",
            "--surface-card: #FFFFFF;",
            "--surface-warm: #F5F2EB;",
            "--text-charcoal: #1C1F1D;",
            "--deep-olive: #2E3A2D;",
            "--sage-green: #6E856C;",
            "--muted-sage: #E8EDE7;",
            "--subtle-border: #E2DDD5;",
            "--space-2: 8px;",
            "--font-display:",
            "--font-sans:",
            "--font-mono:",
            "jmdb-editorial-header",
            "jmdb-job-card",
        ]
        for token in required_tokens:
            self.assertIn(token, content, f"Missing required token '{token}' in style.css")

    # -------------------------------------------------------------------------
    # 2. UI Components Backward Compatibility & Signatures
    # -------------------------------------------------------------------------
    def test_legacy_component_signatures(self):
        """Verify all Phase 6 public functions and signatures exist and are callable."""
        self.assertEqual(len(US_STATES), 51)
        self.assertIn("CA", US_STATES)
        self.assertIn("DC", US_STATES)

        # Badge generator
        li_badge = render_platform_badge("linkedin")
        self.assertIn("LinkedIn", li_badge)
        self.assertIn("jmdb-badge-linkedin", li_badge)

        ind_badge = render_platform_badge("indeed")
        self.assertIn("Indeed", ind_badge)
        self.assertIn("jmdb-badge-indeed", ind_badge)

        none_badge = render_platform_badge(None)
        self.assertIn("Unknown", none_badge)

    # -------------------------------------------------------------------------
    # 3. New Phase 7 Editorial Components
    # -------------------------------------------------------------------------
    def test_new_editorial_components(self):
        """Verify EditorialHeader, EditorialStatCard, EditorialCallout, EditorialFilterBar, ElevatedJobCard."""
        self.assertTrue(callable(EditorialHeader))
        self.assertTrue(callable(EditorialStatCard))
        self.assertTrue(callable(EditorialCallout))
        self.assertTrue(callable(EditorialFilterBar))
        self.assertTrue(callable(ElevatedJobCard))

        # Test ElevatedJobCard output
        sample_job = {
            "title": "Staff Data Engineer",
            "source": "linkedin",
            "company": {"name": "Stripe"},
            "location": {"city": "San Francisco", "state": "CA", "is_remote": True},
            "salary": {"normalized_annual": 215000.0, "salary_bucket": ">160000"},
            "skills": ["Python", "SQL", "MongoDB", "Spark"],
        }
        card_html = render_elevated_job_card(sample_job, selected_skills=["Python"])
        self.assertIn("Staff Data Engineer", card_html)
        self.assertIn("Stripe", card_html)
        self.assertIn("San Francisco, CA", card_html)
        self.assertIn("Remote", card_html)
        self.assertIn("$215,000 / yr", card_html)
        self.assertIn("jmdb-skill-chip-matched", card_html)
        self.assertIn("Python", card_html)

    # -------------------------------------------------------------------------
    # 4. HTML/XSS Sanitization
    # -------------------------------------------------------------------------
    def test_html_escaping(self):
        """Verify user-controlled inputs are escaped in badge and job card generators."""
        malicious = "<script>alert('xss')</script>"
        badge = render_platform_badge(malicious)
        self.assertNotIn("<script>", badge)
        self.assertIn("&lt;script&gt;", badge)

        bad_job = {
            "title": "<img src=x onerror=alert(1)>",
            "source": "linkedin",
            "company": {"name": "<b>Evil Corp</b>"},
            "location": {"raw": "<script>alert(2)</script>"},
        }
        card_html = render_elevated_job_card(bad_job)
        self.assertNotIn("<script>", card_html)
        self.assertNotIn("<img src=x", card_html)
        self.assertIn("&lt;img src=x", card_html)

    # -------------------------------------------------------------------------
    # 5. Plotly Theme Tokens & Palette
    # -------------------------------------------------------------------------
    def test_plotly_theme_tokens(self):
        """Verify Plotly THEME dictionary contains required editorial tokens and legacy compatibility keys."""
        required_keys = [
            "bg_paper", "bg_plot", "canvas_ivory", "card_white", "surface_warm",
            "text_primary", "text_secondary", "grid_color", "subtle_border",
            "deep_olive", "sage_green", "accent_blue", "accent_emerald",
            "linkedin_blue", "indeed_blue", "font_family"
        ]
        for k in required_keys:
            self.assertIn(k, THEME, f"Missing key '{k}' in THEME dictionary")

        self.assertEqual(THEME["bg_paper"], "#FFFFFF")
        self.assertEqual(THEME["bg_plot"], "#FAF8F5")
        self.assertEqual(THEME["text_primary"], "#1C1F1D")
        self.assertEqual(THEME["deep_olive"], "#2E3A2D")
        self.assertEqual(THEME["sage_green"], "#6E856C")

    # -------------------------------------------------------------------------
    # 6. Plotly Builder Functions with Normal, Empty, and None Inputs
    # -------------------------------------------------------------------------
    def test_plot_builders_normal_and_empty(self):
        """Verify all plot builders execute without exceptions for valid, empty, and None inputs."""
        # 1. Ranking
        fig1 = create_horizontal_ranking_chart([{"name": "Python", "count": 100}], "name", "count")
        self.assertIsInstance(fig1, go.Figure)
        self.assertIsInstance(create_horizontal_ranking_chart([], "name", "count"), go.Figure)
        self.assertIsInstance(create_horizontal_ranking_chart(None, "name", "count"), go.Figure)

        # 2. Salary Distribution
        fig2 = create_salary_distribution_chart([{"salary_bucket": "<60000", "count": 50, "avg_salary": 45000}])
        self.assertIsInstance(fig2, go.Figure)
        self.assertIsInstance(create_salary_distribution_chart([]), go.Figure)
        self.assertIsInstance(create_salary_distribution_chart(None), go.Figure)

        # 3. Skills Demand
        fig3 = create_skills_demand_chart([{"skill": "SQL", "count": 200, "percentage": 25.0}], platform="linkedin")
        self.assertIsInstance(fig3, go.Figure)
        self.assertIsInstance(create_skills_demand_chart([], platform="indeed"), go.Figure)
        self.assertIsInstance(create_skills_demand_chart(None), go.Figure)

        # 4. Geographic
        fig4 = create_geographic_comparison_chart([{"state": "CA", "count": 300, "percentage": 15.0}])
        self.assertIsInstance(fig4, go.Figure)
        self.assertIsInstance(create_geographic_comparison_chart([]), go.Figure)
        self.assertIsInstance(create_geographic_comparison_chart(None), go.Figure)

        # 5. Choropleth Map
        fig5 = create_us_choropleth_map([{"state": "CA", "count": 300}])
        self.assertIsInstance(fig5, go.Figure)
        self.assertIsInstance(create_us_choropleth_map([]), go.Figure)
        self.assertIsInstance(create_us_choropleth_map(None), go.Figure)

        # 6. Platform Comparison
        comp = {"platforms": {"linkedin": {"total_postings": 120000}, "indeed": {"total_postings": 5000}}}
        fig6 = create_platform_comparison_chart(comp, metric="volume")
        self.assertIsInstance(fig6, go.Figure)
        self.assertIsInstance(create_platform_comparison_chart(None), go.Figure)

        # 7. Grouped Bar
        fig7 = create_grouped_bar_chart(["Cat1"], [10.0], [20.0])
        self.assertIsInstance(fig7, go.Figure)
        self.assertIsInstance(create_grouped_bar_chart([], [], []), go.Figure)

        # 8. Shared Employers
        fig8 = create_shared_employers_chart([{"company_name": "Google", "linkedin_postings": 100, "indeed_postings": 10}])
        self.assertIsInstance(fig8, go.Figure)
        self.assertIsInstance(create_shared_employers_chart([]), go.Figure)

        # 9. Platform Salary Buckets
        fig9 = create_platform_salary_bucket_chart([
            {"bucket": "<60000", "linkedin_pct_salary_bearing": 5.0, "indeed_pct_salary_bearing": 8.0, "linkedin_pct_total": 1.0, "indeed_pct_total": 8.0, "linkedin_count": 50, "indeed_count": 80}
        ])
        self.assertIsInstance(fig9, go.Figure)
        self.assertIsInstance(create_platform_salary_bucket_chart([]), go.Figure)

    # -------------------------------------------------------------------------
    # 7. Input Immutability
    # -------------------------------------------------------------------------
    def test_plot_builder_immutability(self):
        """Confirm that Plotly builder functions do not mutate the input collections."""
        orig_ranking = [{"name": "A", "count": 10}, {"name": "B", "count": 20}]
        frozen_ranking = copy.deepcopy(orig_ranking)
        create_horizontal_ranking_chart(orig_ranking, "name", "count")
        self.assertEqual(orig_ranking, frozen_ranking)

        orig_buckets = [{"salary_bucket": "<60000", "count": 50}]
        frozen_buckets = copy.deepcopy(orig_buckets)
        create_salary_distribution_chart(orig_buckets)
        self.assertEqual(orig_buckets, frozen_buckets)

    # -------------------------------------------------------------------------
    # 8. MongoDB Canonical Database Invariants
    # -------------------------------------------------------------------------
    def test_database_invariants(self):
        """Verify 129,550 jobs, 24,472 companies, and 15 indexes remain strictly immutable."""
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

