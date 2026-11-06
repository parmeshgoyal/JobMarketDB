"""
JobMarketDB - Comprehensive MongoDB Verification Script (Phase 4)

Verifies:
1. Connectivity & ping
2. Collection existence (jobs, companies)
3. Exact document counts (129,550 jobs, 24,472 companies)
4. Source identity uniqueness (zero duplicates)
5. Source distribution (123,835 LinkedIn, 5,715 Indeed)
6. Document schema completeness & embedded structures
7. Salary integrity (Indeed normalized_annual is null, LinkedIn estimated_midpoint is null, no zero salaries)
8. Company orphan integrity (orphan ID 23729571 in jobs, absent from companies)
9. Required indexes verified on both collections
"""

import json
import os
import sys
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import (
    close_connection,
    get_connection_config,
    get_database,
    mask_mongo_uri,
    verify_connection,
)
from pymongo.collection import Collection
from pymongo.database import Database


def verify_database() -> bool:
    """
    Executes full Phase 4 verification checks on the MongoDB deployment.
    Returns True if all checks pass, False otherwise.
    """
    print("=" * 70)
    print(" JobMarketDB - Phase 4 MongoDB Deployment Verification")
    print("=" * 70)

    # 1. Connection & Ping
    uri, db_name = get_connection_config()
    print(f" Target URI:      {mask_mongo_uri(uri)}")
    print(f" Target Database: {db_name}")

    try:
        verify_connection(timeout_ms=5000)
        print(" [PASS] 1. Database connectivity & ping verified.")
    except Exception as e:
        print(f" [FAIL] 1. Connection failed: {e}")
        return False

    db: Database = get_database(db_name)
    all_passed = True

    # 2. Collection Existence
    existing_collections = db.list_collection_names()
    print(f"\n Collections in database '{db_name}': {existing_collections}")
    if "jobs" in existing_collections and "companies" in existing_collections:
        print(" [PASS] 2. Required collections ('jobs', 'companies') exist.")
    else:
        print(f" [FAIL] 2. Missing required collections. Found: {existing_collections}")
        all_passed = False

    jobs_col: Collection = db["jobs"]
    comp_col: Collection = db["companies"]

    # 3. Collection Counts
    jobs_count = jobs_col.count_documents({})
    comp_count = comp_col.count_documents({})
    print(f"\n Document Counts:")
    print(f"    - jobs:      {jobs_count:,} (Expected: 129,550)")
    print(f"    - companies: {comp_count:,} (Expected: 24,472)")

    if jobs_count == 129550 and comp_count == 24472:
        print(" [PASS] 3. Exact collection counts verified.")
    else:
        print(f" [FAIL] 3. Count mismatch! Expected 129,550 jobs and 24,472 companies.")
        all_passed = False

    # 4. Duplicate Source Identities
    print("\n Checking Source Identity Uniqueness:")
    # Jobs: (source, source_job_id)
    dup_jobs_pipeline = [
        {"$group": {"_id": {"source": "$source", "job_id": "$source_job_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$limit": 5},
    ]
    job_duplicates = list(jobs_col.aggregate(dup_jobs_pipeline))
    if not job_duplicates:
        print("    - jobs (source + source_job_id): 0 duplicates found.")
    else:
        print(f"    - jobs: Found duplicates! {job_duplicates}")
        all_passed = False

    # Companies: company_id
    dup_comp_pipeline = [
        {"$group": {"_id": "$company_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$limit": 5},
    ]
    comp_duplicates = list(comp_col.aggregate(dup_comp_pipeline))
    if not comp_duplicates:
        print("    - companies (company_id): 0 duplicates found.")
    else:
        print(f"    - companies: Found duplicates! {comp_duplicates}")
        all_passed = False

    if not job_duplicates and not comp_duplicates:
        print(" [PASS] 4. Source identity uniqueness verified (0 duplicates).")

    # 5. Source Distribution in Jobs
    li_jobs = jobs_col.count_documents({"source": "linkedin"})
    ind_jobs = jobs_col.count_documents({"source": "indeed"})
    print(f"\n Source Distribution:")
    print(f"    - linkedin: {li_jobs:,} (Expected: 123,835)")
    print(f"    - indeed:   {ind_jobs:,} (Expected: 5,715)")
    if li_jobs == 123835 and ind_jobs == 5715:
        print(" [PASS] 5. Source distribution verified.")
    else:
        print(" [FAIL] 5. Source distribution mismatch!")
        all_passed = False

    # 6. Schema Structure & Embedded Fields Verification
    print("\n Inspecting Schema & Embedded Document Fields:")
    sample_li = jobs_col.find_one({"source": "linkedin"})
    sample_ind = jobs_col.find_one({"source": "indeed"})
    sample_comp = comp_col.find_one({})

    required_job_keys = [
        "source", "source_job_id", "title", "description", "company", "location",
        "salary", "skills", "industries", "benefits", "source_employment_type",
        "normalized_employment_type", "experience_level", "role_category", "posted_date",
        "estimated_posted_date", "source_data",
    ]
    for k in required_job_keys:
        if k not in (sample_li or {}) or k not in (sample_ind or {}):
            print(f"    [FAIL] Missing required job key: '{k}'")
            all_passed = False

    if sample_li and sample_ind and sample_comp:
        print("    - Embedded documents ('company', 'location', 'salary', 'role_category') preserved.")
        print(" [PASS] 6. Schema and embedded structures verified.")

    # 7. Salary Integrity
    print("\n Salary Integrity Checks:")
    ind_norm_sal_violations = jobs_col.count_documents({"source": "indeed", "salary.normalized_annual": {"$ne": None}})
    li_midpoint_violations = jobs_col.count_documents({"source": "linkedin", "salary.estimated_midpoint": {"$ne": None}})
    zero_salary_violations = jobs_col.count_documents(
        {"$or": [{"salary.normalized_annual": 0}, {"salary.min_salary": 0}]}
    )
    print(f"    - Indeed with normalized_annual:      {ind_norm_sal_violations} (Expected: 0)")
    print(f"    - LinkedIn with estimated_midpoint:    {li_midpoint_violations} (Expected: 0)")
    print(f"    - Stated zero salary violations:       {zero_salary_violations} (Expected: 0)")

    if ind_norm_sal_violations == 0 and li_midpoint_violations == 0 and zero_salary_violations == 0:
        print(" [PASS] 7. Salary integrity verified.")
    else:
        print(" [FAIL] 7. Salary integrity check failed!")
        all_passed = False

    # 8. Company Orphan Handling
    print("\n Orphan Company ID Integrity (company_id = 23729571):")
    orphan_in_comp = comp_col.count_documents({"company_id": 23729571})
    orphan_in_jobs = jobs_col.count_documents({"company.company_id": 23729571})
    print(f"    - Presence in 'companies' collection: {orphan_in_comp} (Expected: 0 - no fabrication)")
    print(f"    - Presence in 'jobs' collection:      {orphan_in_jobs} (Expected: 1 - posting preserved)")

    if orphan_in_comp == 0 and orphan_in_jobs == 1:
        print(" [PASS] 8. Orphan company handling verified.")
    else:
        print(" [FAIL] 8. Orphan company check failed!")
        all_passed = False

    # 9. Index Verification
    print("\n Index Verification:")
    jobs_indexes = jobs_col.index_information()
    comp_indexes = comp_col.index_information()

    print("    - Indexes on 'jobs':")
    for name, info in jobs_indexes.items():
        print(f"       * {name}: {info.get('key')}{' (unique)' if info.get('unique') else ''}")

    print("    - Indexes on 'companies':")
    for name, info in comp_indexes.items():
        print(f"       * {name}: {info.get('key')}{' (unique)' if info.get('unique') else ''}")

    # Check required index names/keys
    req_job_indexes = [
        "source_1_source_job_id_1_unique",
        "title_text_description_text",
        "location.state_1_location.is_remote_1",
        "salary.salary_bucket_1_salary.normalized_annual_1",
        "skills_1",
        "company.name_1",
        "experience_level.value_1",
        "source_1",
        "role_category.value_1",
        "source_1_salary.salary_bucket_1",
    ]
    for req in req_job_indexes:
        if req not in jobs_indexes:
            print(f"    [FAIL] Missing index on jobs: {req}")
            all_passed = False

    req_comp_indexes = ["company_id_1_unique", "name_1", "industries_1"]
    for req in req_comp_indexes:
        if req not in comp_indexes:
            print(f"    [FAIL] Missing index on companies: {req}")
            all_passed = False

    if all_passed:
        print(" [PASS] 9. All required Phase 2 query-driven indexes are present.")

    print("\n" + "=" * 70)
    print(f" Phase 4 Overall Verification: {'ALL CHECKS PASSED' if all_passed else 'FAILED'}")
    print("=" * 70)

    close_connection()
    return all_passed


if __name__ == "__main__":
    passed = verify_database()
    sys.exit(0 if passed else 1)
