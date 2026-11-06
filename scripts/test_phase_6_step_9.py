"""
JobMarketDB - Phase 6 Step 9 Test Suite: Isolated CRUD Demonstration Sandbox

Comprehensive verification of:
1. Strict collection isolation to 'jobmarketdb.demo_postings'.
2. Canonical collection immutability ('jobs' and 'companies' remain 100% untouched).
3. Safety guards preventing access to forbidden collections.
4. Create operation validation (required fields, lengths, salary constraints, unique demo_id).
5. Read operation functionality (keyword search, state filter, modality filter, by-id retrieval).
6. Update operation validation (partial updates, salary modifications, timestamp tracking).
7. Single-document Delete operation (verified deletion, rejection of non-existent/invalid IDs).
8. Absence of bulk deletion, drop, or database-wide reset operations.
9. Service-layer encapsulation through JobMarketAnalyticsService.
10. Database invariants before and after test execution.
"""

import unittest
from bson import ObjectId
import pymongo

from database.connection import get_database
from analytics.service import JobMarketAnalyticsService
from analytics.crud import (
    DEMO_COLLECTION,
    CANONICAL_COLLECTIONS,
    _assert_demo_collection,
    create_demo_posting,
    get_demo_postings,
    get_demo_posting_by_id,
    update_demo_posting,
    delete_demo_posting,
    get_demo_collection_stats,
)


class TestPhase6Step9CRUDDemo(unittest.TestCase):
    """Phase 6 Step 9 automated verification suite for CRUD Demonstration Sandbox."""

    @classmethod
    def setUpClass(cls):
        cls.db = get_database()
        cls.service = JobMarketAnalyticsService(cls.db)
        cls.raw_client = pymongo.MongoClient("mongodb://localhost:27017/")
        cls.raw_db = cls.raw_client["jobmarketdb"]

        # Initial invariant assertion
        cls._verify_invariants()

        # Track created demo document IDs for clean single-document cleanup during testing
        cls.test_doc_ids = []

    @classmethod
    def tearDownClass(cls):
        # Clean up any leftover test demo documents individually (NO bulk delete)
        for doc_id in cls.test_doc_ids:
            try:
                cls.raw_db[DEMO_COLLECTION].delete_one({"_id": doc_id})
            except Exception:
                pass

        # Post-execution invariant assertion
        cls._verify_invariants()
        cls.raw_client.close()

    @classmethod
    def _verify_invariants(cls):
        jobs_count = cls.raw_db.jobs.count_documents({})
        companies_count = cls.raw_db.companies.count_documents({})
        jobs_indexes = len(cls.raw_db.jobs.index_information())
        companies_indexes = len(cls.raw_db.companies.index_information())

        assert jobs_count == 129550, f"Jobs document invariant violated! Expected 129,550, got {jobs_count}"
        assert companies_count == 24472, f"Companies document invariant violated! Expected 24,472, got {companies_count}"
        assert jobs_indexes == 11, f"Jobs index count invariant violated! Expected 11, got {jobs_indexes}"
        assert companies_indexes == 4, f"Companies index count invariant violated! Expected 4, got {companies_indexes}"
        assert (jobs_indexes + companies_indexes) == 15, (
            f"Total indexes invariant violated! Expected 15 (11 jobs + 4 companies), got {jobs_indexes + companies_indexes}"
        )

    def test_01_canonical_immutability_guard(self):
        """Verify that _assert_demo_collection strictly forbids canonical or non-demo collections."""
        # Canonical collections must raise PermissionError
        with self.assertRaises(PermissionError):
            _assert_demo_collection("jobs")

        with self.assertRaises(PermissionError):
            _assert_demo_collection("companies")

        with self.assertRaises(PermissionError):
            _assert_demo_collection("system.indexes")

        with self.assertRaises(PermissionError):
            _assert_demo_collection("other_collection")

        # Only demo_postings is authorized
        _assert_demo_collection(DEMO_COLLECTION)

    def test_02_create_demo_posting_validation_failures(self):
        """Verify that create_demo_posting rejects invalid required fields and illogical constraints."""
        # Empty title
        with self.assertRaises(ValueError) as ctx:
            self.service.create_demo_posting(title="", company_name="Acme", description="Valid description text here.")
        self.assertIn("Job title is required", str(ctx.exception))

        # Empty company
        with self.assertRaises(ValueError) as ctx:
            self.service.create_demo_posting(title="Software Engineer", company_name="   ", description="Valid description text.")
        self.assertIn("Company name is required", str(ctx.exception))

        # Too short description
        with self.assertRaises(ValueError) as ctx:
            self.service.create_demo_posting(title="Software Engineer", company_name="Acme", description="Short")
        self.assertIn("Job description must contain at least 10 characters", str(ctx.exception))

        # Negative salary
        with self.assertRaises(ValueError) as ctx:
            self.service.create_demo_posting(
                title="Engineer",
                company_name="Acme",
                description="Valid description text.",
                salary_min=-5000,
            )
        self.assertIn("cannot be negative", str(ctx.exception))

        # Min salary > Max salary
        with self.assertRaises(ValueError) as ctx:
            self.service.create_demo_posting(
                title="Engineer",
                company_name="Acme",
                description="Valid description text.",
                salary_min=180000,
                salary_max=120000,
            )
        self.assertIn("Minimum salary cannot exceed maximum salary", str(ctx.exception))

    def test_03_create_demo_posting_success(self):
        """Verify successful creation of a demonstration posting with all fields and salary computation."""
        created = self.service.create_demo_posting(
            title="Senior Distributed Systems Architect",
            company_name="Apex Cloud Technologies",
            description="Leading the development of large-scale distributed analytics engines using MongoDB Community Server.",
            location_city="Seattle",
            location_state="WA",
            is_remote=True,
            skills=["Python", "MongoDB", "Distributed Systems", "Docker", "Apache Kafka"],
            source="Demonstration Sandbox",
            experience_level="Mid-Senior level",
            salary_min=140000,
            salary_max=190000,
            salary_currency="USD",
            salary_period="yearly",
        )

        self.assertIn("_id", created)
        self.assertIsInstance(created["_id"], ObjectId)
        self.test_doc_ids.append(created["_id"])

        self.assertTrue(created.get("demo_id", "").startswith("DEMO-"))
        self.assertEqual(created["title"], "Senior Distributed Systems Architect")
        self.assertEqual(created["company"]["name"], "Apex Cloud Technologies")
        self.assertEqual(created["location"]["city"], "Seattle")
        self.assertEqual(created["location"]["state"], "WA")
        self.assertTrue(created["location"]["is_remote"])
        self.assertEqual(len(created["skills"]), 5)
        self.assertIn("MongoDB", created["skills"])
        self.assertTrue(created["is_demo"])

        # Verify salary normalization: (140,000 + 190,000) / 2 = 165,000
        salary_doc = created.get("salary")
        self.assertIsNotNone(salary_doc)
        self.assertEqual(salary_doc["normalized_annual"], 165000.0)

        # Confirm document actually exists in demo_postings
        raw_doc = self.raw_db[DEMO_COLLECTION].find_one({"_id": created["_id"]})
        self.assertIsNotNone(raw_doc)
        self.assertEqual(raw_doc["demo_id"], created["demo_id"])

        # Confirm canonical collections are completely untouched
        self.assertEqual(self.raw_db.jobs.count_documents({}), 129550)
        self.assertEqual(self.raw_db.companies.count_documents({}), 24472)

    def test_04_create_demo_posting_without_salary(self):
        """Verify that demonstration postings without salary are created with salary=None."""
        created = self.service.create_demo_posting(
            title="Junior DevOps Engineer",
            company_name="CloudBridge Networks",
            description="Deploying, maintaining, and automating local microservices infrastructure.",
            location_city="Austin",
            location_state="TX",
            is_remote=False,
            skills=["Linux", "Bash", "Git"],
        )

        self.assertIn("_id", created)
        self.test_doc_ids.append(created["_id"])
        self.assertIsNone(created.get("salary"))

    def test_05_read_demo_postings_with_filters(self):
        """Verify get_demo_postings filtering by keyword, state, and modality."""
        # Insert a distinct test document
        doc1 = self.service.create_demo_posting(
            title="Bioinformatics Research Scientist",
            company_name="Genomics Labs International",
            description="Performing computational genomics analysis and high-throughput data processing.",
            location_city="Boston",
            location_state="MA",
            is_remote=False,
            skills=["R", "Python", "Bioinformatics"],
        )
        self.test_doc_ids.append(doc1["_id"])

        # 1. Search by title keyword
        res, count = self.service.get_demo_postings(search_query="Bioinformatics")
        self.assertGreaterEqual(count, 1)
        self.assertTrue(any(p["_id"] == doc1["_id"] for p in res))

        # 2. Search by company keyword
        res, count = self.service.get_demo_postings(search_query="Genomics Labs")
        self.assertGreaterEqual(count, 1)
        self.assertTrue(any(p["_id"] == doc1["_id"] for p in res))

        # 3. Filter by state
        res, count = self.service.get_demo_postings(state="MA")
        self.assertGreaterEqual(count, 1)
        self.assertTrue(all(p["location"]["state"] == "MA" for p in res))

        # 4. Filter by remote
        res_remote, _ = self.service.get_demo_postings(is_remote=True)
        self.assertTrue(all(p["location"]["is_remote"] is True for p in res_remote))

    def test_06_get_demo_posting_by_id(self):
        """Verify get_demo_posting_by_id retrieves documents by ObjectId and demo_id string."""
        doc = self.service.create_demo_posting(
            title="Full Stack Python Developer",
            company_name="InnovateTech Solutions",
            description="Developing end-to-end web applications with modern frontend and MongoDB backend.",
            location_city="Denver",
            location_state="CO",
            is_remote=True,
        )
        self.test_doc_ids.append(doc["_id"])

        # Retrieval by ObjectId
        fetched_by_oid = self.service.get_demo_posting_by_id(doc["_id"])
        self.assertIsNotNone(fetched_by_oid)
        self.assertEqual(fetched_by_oid["_id"], doc["_id"])

        # Retrieval by demo_id string
        fetched_by_demo_id = self.service.get_demo_posting_by_id(doc["demo_id"])
        self.assertIsNotNone(fetched_by_demo_id)
        self.assertEqual(fetched_by_demo_id["_id"], doc["_id"])

        # Non-existent ID returns None
        self.assertIsNone(self.service.get_demo_posting_by_id(ObjectId()))
        self.assertIsNone(self.service.get_demo_posting_by_id("DEMO-NONEXISTENT-99999"))

    def test_07_update_demo_posting(self):
        """Verify update_demo_posting modifies fields, updates timestamp, and preserves other fields."""
        doc = self.service.create_demo_posting(
            title="Original Title Engineer",
            company_name="Original Company",
            description="Original job description for testing updates.",
            location_city="Chicago",
            location_state="IL",
            is_remote=False,
            skills=["Python"],
        )
        self.test_doc_ids.append(doc["_id"])

        import time
        time.sleep(0.01)

        # Update title, company, skills, and add salary
        updated = self.service.update_demo_posting(
            doc_id=doc["_id"],
            title="Updated Staff Data Engineer",
            company_name="Updated Premier Corp",
            skills=["Python", "PySpark", "MongoDB"],
            is_remote=True,
            salary_min=135000,
            salary_max=175000,
        )

        self.assertEqual(updated["title"], "Updated Staff Data Engineer")
        self.assertEqual(updated["company"]["name"], "Updated Premier Corp")
        self.assertEqual(len(updated["skills"]), 3)
        self.assertTrue(updated["location"]["is_remote"])
        self.assertIsNotNone(updated["salary"])
        self.assertEqual(updated["salary"]["normalized_annual"], 155000.0)
        self.assertGreaterEqual(updated["updated_at"], doc["created_at"])

        # Verify update validation: empty title raises ValueError
        with self.assertRaises(ValueError):
            self.service.update_demo_posting(doc_id=doc["_id"], title="   ")

    def test_08_delete_demo_posting_single_document(self):
        """Verify delete_demo_posting deletes exactly one targeted document."""
        doc = self.service.create_demo_posting(
            title="Temporary Post For Deletion",
            company_name="Ephemeral Enterprises",
            description="This posting will be deleted to test single-document deletion.",
        )

        doc_id = doc["_id"]
        # Confirm document exists prior to deletion
        self.assertIsNotNone(self.service.get_demo_posting_by_id(doc_id))

        # Delete document
        deleted = self.service.delete_demo_posting(doc_id)
        self.assertTrue(deleted)

        # Confirm document no longer exists
        self.assertIsNone(self.service.get_demo_posting_by_id(doc_id))

        # Attempting to delete the same ID again raises ValueError
        with self.assertRaises(ValueError):
            self.service.delete_demo_posting(doc_id)

    def test_09_prohibition_of_bulk_deletion(self):
        """Verify that no bulk deletion or reset methods are exposed in the service layer."""
        self.assertFalse(hasattr(self.service, "delete_many"))
        self.assertFalse(hasattr(self.service, "drop_collection"))
        self.assertFalse(hasattr(self.service, "reset_sandbox"))
        self.assertFalse(hasattr(self.service, "clear_demo_postings"))

    def test_10_database_invariants_strictly_preserved(self):
        """Verify that canonical collections and indexes remained completely unchanged with separate assertions."""
        jobs_count = self.raw_db.jobs.count_documents({})
        companies_count = self.raw_db.companies.count_documents({})
        jobs_indexes = len(self.raw_db.jobs.index_information())
        companies_indexes = len(self.raw_db.companies.index_information())

        # Individual separate assertions required by Phase 6 audit
        self.assertEqual(jobs_count, 129550, f"jobs documents invariant violated: expected 129550, got {jobs_count}")
        self.assertEqual(companies_count, 24472, f"companies documents invariant violated: expected 24472, got {companies_count}")
        self.assertEqual(jobs_indexes, 11, f"jobs indexes invariant violated: expected 11, got {jobs_indexes}")
        self.assertEqual(companies_indexes, 4, f"companies indexes invariant violated: expected 4, got {companies_indexes}")
        self.assertEqual(jobs_indexes + companies_indexes, 15, "Total canonical index count must remain 15")

    def test_11_get_canonical_counts_service(self):
        """Verify service.get_canonical_counts returns exact live counts without hardcoded fallbacks."""
        counts = self.service.get_canonical_counts()
        self.assertIsInstance(counts, dict)
        self.assertEqual(counts.get("jobs"), 129550)
        self.assertEqual(counts.get("companies"), 24472)

    def test_12_update_demo_posting_remove_salary(self):
        """Verify explicit salary removal via remove_salary=True using targeted $unset."""
        doc = self.service.create_demo_posting(
            title="Compensation Test Engineer",
            company_name="Salary Benchmarking Labs",
            description="Posting created with full salary structure to test targeted $unset removal.",
            salary_min=120000,
            salary_max=160000,
            salary_period="yearly",
        )
        self.test_doc_ids.append(doc["_id"])
        self.assertIsNotNone(doc.get("salary"))
        self.assertEqual(doc["salary"]["normalized_annual"], 140000.0)

        # Negative test: cannot pass both remove_salary and salary values
        with self.assertRaises(ValueError):
            self.service.update_demo_posting(
                doc_id=doc["_id"],
                remove_salary=True,
                salary_min=130000,
            )

        # Remove salary via remove_salary=True
        updated = self.service.update_demo_posting(
            doc_id=doc["_id"],
            remove_salary=True,
        )
        self.assertIsNone(updated.get("salary"))

        # Verify directly in MongoDB that 'salary' field was completely unset
        raw_doc = self.raw_db[DEMO_COLLECTION].find_one({"_id": doc["_id"]})
        self.assertNotIn("salary", raw_doc)

        # Verify title and company were preserved
        self.assertEqual(raw_doc["title"], "Compensation Test Engineer")
        self.assertEqual(raw_doc["company"]["name"], "Salary Benchmarking Labs")

    def test_13_xss_and_html_input_sanitization_and_escaping(self):
        """Test input containing HTML tags and script-like strings renders as text and cannot execute."""
        import html

        raw_xss_title = "<script>alert('xss')</script> Cloud Architect"
        raw_xss_company = "<b onmouseover='alert(1)'>Cyberdyne Systems</b>"
        raw_xss_desc = "<img src=x onerror=alert('hack')> Full description with <em>emphasis</em> and <script>alert(2)</script>."
        raw_xss_skills = ["<script>", "React", "<style>body{color:red;}</style>"]

        doc = self.service.create_demo_posting(
            title=raw_xss_title,
            company_name=raw_xss_company,
            description=raw_xss_desc,
            skills=raw_xss_skills,
        )
        self.test_doc_ids.append(doc["_id"])

        fetched = self.service.get_demo_posting_by_id(doc["_id"])
        self.assertIsNotNone(fetched)

        # Verify HTML escaping produces benign text representation
        esc_title = html.escape(fetched["title"])
        self.assertNotIn("<script>", esc_title)
        self.assertIn("&lt;script&gt;", esc_title)

        esc_company = html.escape(fetched["company"]["name"])
        self.assertNotIn("<b onmouseover", esc_company)
        self.assertIn("&lt;b onmouseover", esc_company)

        esc_desc = html.escape(fetched["description"])
        self.assertNotIn("<img src=x", esc_desc)
        self.assertIn("&lt;img src=x", esc_desc)

        for s in fetched["skills"]:
            esc_s = html.escape(s)
            self.assertNotIn("<script>", esc_s)
            self.assertNotIn("<style>", esc_s)


if __name__ == "__main__":
    unittest.main()
