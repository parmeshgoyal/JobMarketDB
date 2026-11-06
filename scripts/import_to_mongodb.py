"""
JobMarketDB - MongoDB Controlled Batch Ingestion Pipeline (Phase 4)

Imports validated JSONL files into local MongoDB Community Server:
- data/processed/jobs_transformed.jsonl (129,550 records)
- data/processed/companies_transformed.jsonl (24,472 records)

Enforces idempotency, creates query-driven indexes, and generates an audit report.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

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
from pymongo.errors import BulkWriteError, PyMongoError


def create_unique_indexes(db: Database) -> List[str]:
    """
    Creates unique compound identity indexes before ingestion to guarantee idempotency.
    """
    print("\n>>> Setting up unique identity indexes for idempotency...")
    created: List[str] = []

    # Jobs unique source identity
    idx_job_unique = db["jobs"].create_index(
        [("source", 1), ("source_job_id", 1)],
        unique=True,
        name="source_1_source_job_id_1_unique",
    )
    created.append(f"jobs: {idx_job_unique} (unique)")

    # Companies unique identity
    idx_comp_unique = db["companies"].create_index(
        [("company_id", 1)],
        unique=True,
        name="company_id_1_unique",
    )
    created.append(f"companies: {idx_comp_unique} (unique)")

    print(f"   Unique identity indexes verified on 'jobs' and 'companies'.")
    return created


def create_query_indexes(db: Database) -> List[str]:
    """
    Creates the required Phase 2 query-driven secondary indexes after bulk loading.
    """
    print("\n>>> Setting up required Phase 2 query-driven secondary indexes...")
    created: List[str] = []

    jobs_col = db["jobs"]
    comp_col = db["companies"]

    # 1. Full text search index on title and description
    idx_job_text = jobs_col.create_index(
        [("title", "text"), ("description", "text")],
        name="title_text_description_text",
    )
    created.append(f"jobs: {idx_job_text}")

    # 2. Location compound index
    idx_job_loc = jobs_col.create_index(
        [("location.state", 1), ("location.is_remote", 1)],
        name="location.state_1_location.is_remote_1",
    )
    created.append(f"jobs: {idx_job_loc}")

    # 3. Salary compound index
    idx_job_sal = jobs_col.create_index(
        [("salary.salary_bucket", 1), ("salary.normalized_annual", 1)],
        name="salary.salary_bucket_1_salary.normalized_annual_1",
    )
    created.append(f"jobs: {idx_job_sal}")

    # 4. Skills multi-key index
    idx_job_skills = jobs_col.create_index([("skills", 1)], name="skills_1")
    created.append(f"jobs: {idx_job_skills}")

    # 5. Company name index
    idx_job_comp = jobs_col.create_index([("company.name", 1)], name="company.name_1")
    created.append(f"jobs: {idx_job_comp}")

    # 6. Experience level index
    idx_job_exp = jobs_col.create_index([("experience_level.value", 1)], name="experience_level.value_1")
    created.append(f"jobs: {idx_job_exp}")

    # 7. Source platform index
    idx_job_src = jobs_col.create_index([("source", 1)], name="source_1")
    created.append(f"jobs: {idx_job_src}")

    # 8. Role category index
    idx_job_role = jobs_col.create_index([("role_category.value", 1)], name="role_category.value_1")
    created.append(f"jobs: {idx_job_role}")

    # 9. Source + Salary bucket comparison index (Phase 2 Query 12)
    idx_job_src_sal = jobs_col.create_index(
        [("source", 1), ("salary.salary_bucket", 1)],
        name="source_1_salary.salary_bucket_1",
    )
    created.append(f"jobs: {idx_job_src_sal}")

    # 10. Companies name index
    idx_comp_name = comp_col.create_index([("name", 1)], name="name_1")
    created.append(f"companies: {idx_comp_name}")

    # 11. Companies industries multi-key index
    idx_comp_ind = comp_col.create_index([("industries", 1)], name="industries_1")
    created.append(f"companies: {idx_comp_ind}")

    print(f"   Secondary query indexes created successfully ({len(created)} indexes).")
    return created


def import_collection(
    collection: Collection,
    file_path: str,
    collection_name: str,
    batch_size: int = 2000,
    progress_interval: int = 20000,
) -> Tuple[int, int, int, int]:
    """
    Incrementally imports a JSONL file into the specified MongoDB collection in batches.
    Returns: (total_lines_read, inserted_count, already_existing_count, failed_count)
    """
    total_read = 0
    inserted = 0
    already_existing = 0
    failed = 0

    batch: List[Dict[str, Any]] = []

    def flush_batch(b: List[Dict[str, Any]]) -> Tuple[int, int, int]:
        if not b:
            return 0, 0, 0
        ins = 0
        dup = 0
        fail = 0
        try:
            res = collection.insert_many(b, ordered=False)
            ins = len(res.inserted_ids)
        except BulkWriteError as bwe:
            ins = bwe.details.get("nInserted", 0)
            for write_err in bwe.details.get("writeErrors", []):
                if write_err.get("code") == 11000:
                    dup += 1
                else:
                    fail += 1
                    print(f"      [Write Error]: {write_err.get('errmsg')}")
        except PyMongoError as pme:
            fail += len(b)
            print(f"      [Fatal Batch Error in {collection_name}]: {pme}")
        return ins, dup, fail

    print(f"\n>>> Importing '{collection_name}' from {file_path}...")
    t_start = time.time()

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            total_read += 1

            try:
                doc = json.loads(line_str)
                batch.append(doc)
            except json.JSONDecodeError as jde:
                failed += 1
                print(f"   [Malformed JSON line {line_num}]: {jde}")
                continue

            if len(batch) >= batch_size:
                b_ins, b_dup, b_fail = flush_batch(batch)
                inserted += b_ins
                already_existing += b_dup
                failed += b_fail
                batch.clear()

                if total_read % progress_interval == 0:
                    print(
                        f"   Processed {total_read:,} lines | Inserted: {inserted:,} | "
                        f"Existing/Skipped: {already_existing:,} | Failed: {failed}"
                    )

        # Flush final remaining batch
        if batch:
            b_ins, b_dup, b_fail = flush_batch(batch)
            inserted += b_ins
            already_existing += b_dup
            failed += b_fail
            batch.clear()

    t_duration = time.time() - t_start
    print(
        f"   Finished '{collection_name}': {total_read:,} read in {t_duration:.2f}s | "
        f"Inserted: {inserted:,} | Existing/Skipped: {already_existing:,} | Failed: {failed}"
    )
    return total_read, inserted, already_existing, failed


def run_import(
    data_dir: str = "data/processed",
    batch_size: int = 2000,
    confirm: bool = False,
) -> Dict[str, Any]:
    """
    Executes the complete Phase 4 controlled MongoDB import.
    """
    jobs_file = os.path.join(data_dir, "jobs_transformed.jsonl")
    companies_file = os.path.join(data_dir, "companies_transformed.jsonl")
    summary_file = os.path.join(data_dir, "mongodb_import_summary.json")

    # 1. Verify source files exist
    if not os.path.exists(jobs_file):
        raise FileNotFoundError(f"Jobs transformed file not found: {jobs_file}")
    if not os.path.exists(companies_file):
        raise FileNotFoundError(f"Companies transformed file not found: {companies_file}")

    # 2. Get connection config
    uri, db_name = get_connection_config()
    masked_uri = mask_mongo_uri(uri)

    # 3. Print safety summary as required by Section 18
    print("=" * 70)
    print(" JobMarketDB - Phase 4 MongoDB Controlled Ingestion")
    print("=" * 70)
    print(f" MongoDB URI:      {masked_uri}")
    print(f" MongoDB database: {db_name}")
    print(f" Jobs to import: 129,550")
    print(f" Companies to import: 24,472")
    print("=" * 70)

    # Confirmation safety mechanism
    if not confirm:
        if sys.stdin.isatty():
            ans = input("\nProceed with import to MongoDB? [yes/N]: ").strip().lower()
            if ans not in ("y", "yes"):
                print("Import aborted by user.")
                sys.exit(0)
        else:
            raise RuntimeError(
                "Safety requirement: Ingestion requires explicit confirmation.\n"
                "Pass '--confirm' to proceed with import."
            )

    # 4. Verify connectivity
    print("\n>>> Connecting and pinging MongoDB deployment...")
    t_overall_start = time.time()
    db = get_database(db_name)
    verify_connection(timeout_ms=5000)
    print("   Connection established and ping successful.")

    # 5. Set up required unique identity indexes for idempotency before bulk import
    unique_indexes = create_unique_indexes(db)

    # 6. Import Companies first (supporting collection)
    comp_read, comp_ins, comp_dup, comp_fail = import_collection(
        collection=db["companies"],
        file_path=companies_file,
        collection_name="companies",
        batch_size=batch_size,
        progress_interval=5000,
    )

    # 7. Import Jobs (primary operational collection)
    jobs_read, jobs_ins, jobs_dup, jobs_fail = import_collection(
        collection=db["jobs"],
        file_path=jobs_file,
        collection_name="jobs",
        batch_size=batch_size,
        progress_interval=20000,
    )

    # 8. Set up secondary query-driven indexes after bulk loading
    query_indexes = create_query_indexes(db)
    indexes_created = unique_indexes + query_indexes

    # 9. Post-insertion verification counts
    final_jobs_count = db["jobs"].count_documents({})
    final_comp_count = db["companies"].count_documents({})

    t_total = time.time() - t_overall_start
    verification_passed = (
        jobs_fail == 0
        and comp_fail == 0
        and final_jobs_count == 129550
        and final_comp_count == 24472
    )

    # 9. Build and write import summary JSON (Section 14)
    summary_data: Dict[str, Any] = {
        "database": db_name,
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_duration_seconds": round(t_total, 2),
        "jobs": {
            "source_records": jobs_read,
            "inserted": jobs_ins,
            "already_existing": jobs_dup,
            "failed": jobs_fail,
            "final_count": final_jobs_count,
        },
        "companies": {
            "source_records": comp_read,
            "inserted": comp_ins,
            "already_existing": comp_dup,
            "failed": comp_fail,
            "final_count": final_comp_count,
        },
        "indexes_verified": indexes_created,
        "verification_passed": verification_passed,
    }

    with open(summary_file, "w", encoding="utf-8") as f_sum:
        json.dump(summary_data, f_sum, indent=2)

    print("\n" + "=" * 70)
    print(" MongoDB Import Summary")
    print("=" * 70)
    print(f" Database:               {db_name}")
    print(f" Jobs Final Count:       {final_jobs_count:,} / 129,550 expected")
    print(f" Companies Final Count:  {final_comp_count:,} / 24,472 expected")
    print(f" Total Duration:         {t_total:.2f} seconds")
    print(f" Audit Summary File:     {summary_file}")
    print(f" Verification Status:    {'PASSED' if verification_passed else 'CHECK REQUIRED'}")
    print("=" * 70)

    close_connection()
    return summary_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JobMarketDB MongoDB Controlled Ingestion.")
    parser.add_argument("--confirm", action="store_true", help="Explicit confirmation to execute import.")
    parser.add_argument("--batch-size", type=int, default=2000, help="Batch size for bulk insertion.")
    parser.add_argument("--data-dir", type=str, default="data/processed", help="Directory with processed JSONL files.")
    args = parser.parse_args()

    run_import(data_dir=args.data_dir, batch_size=args.batch_size, confirm=args.confirm)
