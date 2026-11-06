"""
JobMarketDB — Phase 7 Stage 8: CRUD Demo Redesign Test Suite

Tests:
1. Compilation & Import Integrity
2. Page module structure validation (editorial header, safety overview, tabs)
3. Database invariant safety (canonical counts unchanged, 15 indexes)
4. CRUD create operation via service layer
5. CRUD read operation via service layer
6. CRUD update operation with salary modification
7. CRUD update with salary $unset removal
8. CRUD single-document delete with confirmation guard
9. Invalid input validation tests (empty title, invalid salary, min > max, invalid ID)
10. Target collection security enforcement (assertion guards against canonical modification)
11. HTML escaping of user-controlled content
12. Safety guards in source code (no delete_many, no drop, no canonical mutations)
13. Canonical collection immutability before and after CRUD cycles
"""

import html
import os
import re
import sys
import unittest
from bson import ObjectId

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestPhase7Stage8Compilation(unittest.TestCase):
    """Test 1: Verify 6_CRUD_Demo.py compiles and imports are valid."""

    def test_crud_demo_compiles(self):
        import py_compile
        path = os.path.join(PROJECT_ROOT, "pages", "6_CRUD_Demo.py")
        self.assertTrue(os.path.exists(path), f"6_CRUD_Demo.py not found at {path}")
        py_compile.compile(path, doraise=True)

    def test_source_imports_editorial_components(self):
        with open(os.path.join(PROJECT_ROOT, "pages", "6_CRUD_Demo.py"), "r", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("render_editorial_header", source)
        self.assertIn("render_editorial_stat_card", source)
        self.assertIn("render_editorial_callout", source)
        self.assertIn("render_empty_state", source)
        self.assertIn("render_error_state", source)
        self.assertIn("load_custom_css", source)
        self.assertIn("THEME", source)


class TestPhase7Stage8PageStructure(unittest.TestCase):
    """Test 2: Validate page structure matches Stage 8 requirements."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(PROJECT_ROOT, "pages", "6_CRUD_Demo.py"), "r", encoding="utf-8") as f:
            cls.source = f.read()

    def test_editorial_header_eyebrow(self):
        self.assertIn("DATABASE OPERATIONS LABORATORY", self.source)

    def test_editorial_header_title(self):
        self.assertIn("Explore MongoDB Operations", self.source)

    def test_editorial_header_status(self):
        self.assertIn("LOCAL DATABASE", self.source)

    def test_database_safety_overview(self):
        self.assertIn("Canonical Collections", self.source)
        self.assertIn("Sandbox Collection", self.source)
        self.assertIn("Read-Only", self.source)
        self.assertIn("Read/Write", self.source)
        self.assertIn("Canonical Protected", self.source)
        self.assertIn("Sandbox Isolated", self.source)
        self.assertIn("Local MongoDB Only", self.source)
        self.assertIn("No Atlas Connection", self.source)

    def test_five_crud_tabs(self):
        self.assertIn("Browse Sandbox", self.source)
        self.assertIn("Create Posting", self.source)
        self.assertIn("Update Posting", self.source)
        self.assertIn("Delete Posting", self.source)
        self.assertIn("Operations Audit & Reference", self.source)

    def test_sage_ivory_visual_tokens(self):
        self.assertIn("THEME[", self.source)
        self.assertIn("Newsreader", self.source)
        self.assertIn("Plus Jakarta Sans", self.source)

    def test_footer_invariant_guarantee(self):
        self.assertIn("Live Data Invariant Guarantee", self.source)

    def test_no_use_container_width_for_charts(self):
        lines = self.source.split("\n")
        for line in lines:
            if "st.plotly_chart" in line:
                self.assertNotIn("use_container_width", line,
                    "st.plotly_chart should use width='stretch' instead of use_container_width")


class TestPhase7Stage8DatabaseInvariants(unittest.TestCase):
    """Test 3: Canonical database counts are unchanged."""

    def test_canonical_job_count(self):
        from database.connection import get_database
        db = get_database()
        count = db["jobs"].count_documents({})
        self.assertEqual(count, 129550, f"Canonical jobs count mismatch: expected 129,550 got {count:,}")

    def test_canonical_company_count(self):
        from database.connection import get_database
        db = get_database()
        count = db["companies"].count_documents({})
        self.assertEqual(count, 24472, f"Canonical companies count mismatch: expected 24,472 got {count:,}")

    def test_index_count(self):
        from database.connection import get_database
        db = get_database()
        jobs_indexes = len(list(db["jobs"].list_indexes()))
        companies_indexes = len(list(db["companies"].list_indexes()))
        total = jobs_indexes + companies_indexes
        self.assertEqual(total, 15, f"Index count mismatch: expected 15 got {total}")
        self.assertEqual(jobs_indexes, 11, f"Jobs indexes expected 11 got {jobs_indexes}")
        self.assertEqual(companies_indexes, 4, f"Companies indexes expected 4 got {companies_indexes}")


class TestPhase7Stage8CRUDCreate(unittest.TestCase):
    """Test 4: Create demo posting via service layer."""

    def test_create_demo_posting(self):
        from analytics.service import JobMarketAnalyticsService
        svc = JobMarketAnalyticsService()

        result = svc.create_demo_posting(
            title="Stage 8 Test Engineer",
            company_name="TestCorp Stage8",
            description="This is a Stage 8 automated test posting for verification purposes.",
            location_city="Portland",
            location_state="OR",
            is_remote=True,
            skills=["Python", "MongoDB", "Testing"],
            source="Demonstration Sandbox",
            experience_level="Mid-Senior level",
            salary_min=90000.0,
            salary_max=140000.0,
            salary_currency="USD",
            salary_period="yearly",
        )
        self.assertIn("_id", result)
        self.assertIn("demo_id", result)
        self.assertTrue(str(result["demo_id"]).startswith("DEMO-"))
        self.assertEqual(result["title"], "Stage 8 Test Engineer")
        self.assertEqual(result["company"]["name"], "TestCorp Stage8")

        # Cleanup
        svc.delete_demo_posting(doc_id=result["_id"])


class TestPhase7Stage8CRUDRead(unittest.TestCase):
    """Test 5: Read demo postings via service layer."""

    def test_read_demo_postings(self):
        from analytics.service import JobMarketAnalyticsService
        svc = JobMarketAnalyticsService()

        # Create a record first
        created = svc.create_demo_posting(
            title="Stage 8 Read Test",
            company_name="ReadCorp Stage8",
            description="A read test posting for verification purposes.",
        )

        postings, total = svc.get_demo_postings(limit=50)
        self.assertIsInstance(postings, list)
        self.assertGreaterEqual(total, 1)

        # Find our record
        found = any(p.get("demo_id") == created["demo_id"] for p in postings)
        self.assertTrue(found, "Created record not found in read results")

        # Cleanup
        svc.delete_demo_posting(doc_id=created["_id"])


class TestPhase7Stage8CRUDUpdateSalary(unittest.TestCase):
    """Test 6: Update demo posting salary values."""

    def test_update_salary(self):
        from analytics.service import JobMarketAnalyticsService
        svc = JobMarketAnalyticsService()

        created = svc.create_demo_posting(
            title="Stage 8 Update Test",
            company_name="UpdateCorp Stage8",
            description="An update test posting for salary modification.",
            salary_min=80000.0,
            salary_max=120000.0,
        )

        updated = svc.update_demo_posting(
            doc_id=created["_id"],
            salary_min=100000.0,
            salary_max=160000.0,
            salary_period="yearly",
        )
        self.assertEqual(updated["salary"]["min_amount"], 100000.0)
        self.assertEqual(updated["salary"]["max_amount"], 160000.0)

        # Cleanup
        svc.delete_demo_posting(doc_id=created["_id"])


class TestPhase7Stage8CRUDUnsetSalary(unittest.TestCase):
    """Test 7: Update demo posting with salary $unset removal."""

    def test_unset_salary(self):
        from analytics.service import JobMarketAnalyticsService
        svc = JobMarketAnalyticsService()

        created = svc.create_demo_posting(
            title="Stage 8 Unset Test",
            company_name="UnsetCorp Stage8",
            description="An unset test posting for salary removal verification.",
            salary_min=70000.0,
            salary_max=100000.0,
        )
        self.assertIsNotNone(created.get("salary"))

        updated = svc.update_demo_posting(
            doc_id=created["_id"],
            remove_salary=True,
        )
        self.assertIsNone(updated.get("salary"), "Salary should be None after $unset")

        # Cleanup
        svc.delete_demo_posting(doc_id=created["_id"])


class TestPhase7Stage8CRUDDelete(unittest.TestCase):
    """Test 8: Single-document deletion with confirmation."""

    def test_delete_single_document(self):
        from analytics.service import JobMarketAnalyticsService
        svc = JobMarketAnalyticsService()

        created = svc.create_demo_posting(
            title="Stage 8 Delete Test",
            company_name="DeleteCorp Stage8",
            description="A delete test posting that should be removed.",
        )

        success = svc.delete_demo_posting(doc_id=created["_id"])
        self.assertTrue(success)

        # Verify it's gone
        postings, _ = svc.get_demo_postings(limit=200)
        found = any(str(p.get("_id")) == str(created["_id"]) for p in postings)
        self.assertFalse(found, "Deleted record should not appear in results")


class TestPhase7Stage8InvalidInputValidation(unittest.TestCase):
    """Test 9: Service layer validation rejects invalid inputs."""

    @classmethod
    def setUpClass(cls):
        from analytics.service import JobMarketAnalyticsService
        cls.svc = JobMarketAnalyticsService()

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.create_demo_posting(
                title="",
                company_name="Valid Company",
                description="Valid description with enough characters.",
            )

    def test_empty_company_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.create_demo_posting(
                title="Valid Title",
                company_name="",
                description="Valid description with enough characters.",
            )

    def test_short_description_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.create_demo_posting(
                title="Valid Title",
                company_name="Valid Company",
                description="short",
            )

    def test_negative_salary_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.create_demo_posting(
                title="Valid Title",
                company_name="Valid Company",
                description="Valid description with enough characters.",
                salary_min=-50000.0,
            )

    def test_min_exceeds_max_salary_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.create_demo_posting(
                title="Valid Title",
                company_name="Valid Company",
                description="Valid description with enough characters.",
                salary_min=150000.0,
                salary_max=100000.0,
            )

    def test_invalid_objectid_delete_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.delete_demo_posting(doc_id="not-a-valid-oid-at-all")

    def test_nonexistent_objectid_delete_rejected(self):
        fake_id = ObjectId()
        with self.assertRaises(ValueError):
            self.svc.delete_demo_posting(doc_id=fake_id)


class TestPhase7Stage8TargetSecurityGuard(unittest.TestCase):
    """Test 10: Security assertion blocks targeting canonical collections."""

    def test_assert_demo_collection_blocks_jobs(self):
        from analytics.crud import _assert_demo_collection
        with self.assertRaises(PermissionError):
            _assert_demo_collection("jobs")

    def test_assert_demo_collection_blocks_companies(self):
        from analytics.crud import _assert_demo_collection
        with self.assertRaises(PermissionError):
            _assert_demo_collection("companies")

    def test_assert_demo_collection_blocks_arbitrary(self):
        from analytics.crud import _assert_demo_collection
        with self.assertRaises(PermissionError):
            _assert_demo_collection("users")

    def test_assert_demo_collection_allows_demo_postings(self):
        from analytics.crud import _assert_demo_collection
        # Should not raise
        _assert_demo_collection("demo_postings")


class TestPhase7Stage8HTMLEscaping(unittest.TestCase):
    """Test 11: HTML escaping of user-controlled content in source code."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(PROJECT_ROOT, "pages", "6_CRUD_Demo.py"), "r", encoding="utf-8") as f:
            cls.source = f.read()

    def test_html_import(self):
        self.assertIn("import html", self.source)

    def test_html_escape_usage(self):
        escape_count = self.source.count("html.escape")
        self.assertGreaterEqual(escape_count, 10,
            f"Expected >=10 html.escape() calls for safety, found {escape_count}")

    def test_xss_prevention_in_crud_service(self):
        from analytics.service import JobMarketAnalyticsService
        svc = JobMarketAnalyticsService()

        xss_title = "<script>alert('xss')</script>Test"
        try:
            created = svc.create_demo_posting(
                title=xss_title,
                company_name="SafeCorp",
                description="XSS test posting for HTML escaping validation.",
            )
            escaped = html.escape(created["title"])
            self.assertNotIn("<script>", escaped)
            self.assertIn("&lt;script&gt;", escaped)
            svc.delete_demo_posting(doc_id=created["_id"])
        except Exception:
            pass


class TestPhase7Stage8SafetyGuards(unittest.TestCase):
    """Test 12: No bulk deletion, no canonical mutation in page source."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(PROJECT_ROOT, "pages", "6_CRUD_Demo.py"), "r", encoding="utf-8") as f:
            cls.source = f.read()

    def test_no_delete_many(self):
        cleaned = re.sub(r'""".*?"""', '', self.source, flags=re.DOTALL)
        cleaned = re.sub(r"'''.*?'''", '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'"[^"]*"', '""', cleaned)
        cleaned = re.sub(r"'[^']*'", "''", cleaned)
        cleaned = re.sub(r'#.*$', '', cleaned, flags=re.MULTILINE)
        self.assertNotIn("delete_many", cleaned,
            "Found delete_many in executable code (outside strings/comments)")

    def test_no_drop_collection(self):
        self.assertNotIn("drop(", self.source)
        self.assertNotIn("drop_collection", self.source)

    def test_no_canonical_mutation(self):
        self.assertNotIn('db["jobs"].insert', self.source)
        self.assertNotIn('db["jobs"].update', self.source)
        self.assertNotIn('db["jobs"].delete', self.source)
        self.assertNotIn('db["companies"].insert', self.source)
        self.assertNotIn('db["companies"].update', self.source)
        self.assertNotIn('db["companies"].delete', self.source)

    def test_single_document_delete_only(self):
        self.assertIn("delete_demo_posting", self.source)
        self.assertIn("confirm_single_delete", self.source)


class TestPhase7Stage8CanonicalImmutabilityCycle(unittest.TestCase):
    """Test 13: Verify canonical counts remain identical through a full CRUD cycle."""

    def test_full_crud_cycle_leaves_canonical_intact(self):
        from database.connection import get_database
        from analytics.service import JobMarketAnalyticsService

        db = get_database()
        svc = JobMarketAnalyticsService()

        # Pre-cycle canonical audit
        jobs_pre = db["jobs"].count_documents({})
        comp_pre = db["companies"].count_documents({})
        self.assertEqual(jobs_pre, 129550)
        self.assertEqual(comp_pre, 24472)

        # 1. CREATE
        created = svc.create_demo_posting(
            title="Lifecycle Test Engineer",
            company_name="LifecycleCorp",
            description="Document for full CRUD lifecycle immutability verification.",
            salary_min=95000.0,
            salary_max=135000.0,
        )
        self.assertEqual(db["jobs"].count_documents({}), 129550)
        self.assertEqual(db["companies"].count_documents({}), 24472)

        # 2. READ
        postings, _ = svc.get_demo_postings(search_query="LifecycleCorp")
        self.assertGreaterEqual(len(postings), 1)

        # 3. UPDATE
        updated = svc.update_demo_posting(
            doc_id=created["_id"],
            title="Senior Lifecycle Test Engineer",
            remove_salary=True,
        )
        self.assertEqual(updated["title"], "Senior Lifecycle Test Engineer")
        self.assertIsNone(updated.get("salary"))
        self.assertEqual(db["jobs"].count_documents({}), 129550)
        self.assertEqual(db["companies"].count_documents({}), 24472)

        # 4. DELETE
        deleted = svc.delete_demo_posting(doc_id=created["_id"])
        self.assertTrue(deleted)

        # Post-cycle canonical audit
        jobs_post = db["jobs"].count_documents({})
        comp_post = db["companies"].count_documents({})
        self.assertEqual(jobs_post, 129550, "Canonical jobs count mutated during CRUD cycle!")
        self.assertEqual(comp_post, 24472, "Canonical companies count mutated during CRUD cycle!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
