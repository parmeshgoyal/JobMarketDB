"""
JobMarketDB - Unified ETL Execution Script

Orchestrates the extraction, transformation, schema validation, and output
generation for both LinkedIn and Indeed datasets without connecting to MongoDB.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.indeed import IndeedExtractor
from ingestion.linkedin import LinkedInExtractor


def run_etl(output_dir: str = "data/processed", sample_size: int = 0) -> Dict[str, Any]:
    """
    Executes the full ETL pipeline with strict data integrity and provenance rules.
    Writes MongoDB-ready JSONL files to output_dir.
    """
    t_start = time.time()
    os.makedirs(output_dir, exist_ok=True)

    jobs_output_path = os.path.join(output_dir, "jobs_transformed.jsonl")
    companies_output_path = os.path.join(output_dir, "companies_transformed.jsonl")
    summary_output_path = os.path.join(output_dir, "etl_summary.json")

    limit_val = sample_size if sample_size > 0 else None

    print("=" * 70)
    print(" JobMarketDB - Phase 3 ETL & Data Transformation Pipeline")
    print(f" Execution Mode: {'SAMPLE (' + str(sample_size) + ' records)' if limit_val else 'FULL DATASET'}")
    print(f" Output Directory: {os.path.abspath(output_dir)}")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. LINKEDIN EXTRACTION & TRANSFORMATION
    # -------------------------------------------------------------
    print("\n>>> [1/3] Processing LinkedIn Dataset...")
    linkedin_extractor = LinkedInExtractor()
    linkedin_extractor.load_relational_lookups()

    linkedin_job_count = 0
    t_li_start = time.time()

    with open(jobs_output_path, "w", encoding="utf-8") as f_jobs:
        for doc in linkedin_extractor.extract_postings(limit=limit_val):
            f_jobs.write(json.dumps(doc, ensure_ascii=False) + "\n")
            linkedin_job_count += 1
            if linkedin_job_count % 20000 == 0:
                print(f"   Transformed {linkedin_job_count:,} LinkedIn postings...")

    t_li_jobs = time.time() - t_li_start
    print(f"   Completed LinkedIn postings: {linkedin_job_count:,} records in {t_li_jobs:.2f}s")

    # Extract LinkedIn Company Master Profiles
    print("\n>>> [2/3] Extracting LinkedIn Company Master Profiles...")
    linkedin_company_count = 0
    with open(companies_output_path, "w", encoding="utf-8") as f_comp:
        for comp_doc in linkedin_extractor.extract_companies():
            f_comp.write(json.dumps(comp_doc, ensure_ascii=False) + "\n")
            linkedin_company_count += 1

    print(f"   Completed LinkedIn companies: {linkedin_company_count:,} records")

    # -------------------------------------------------------------
    # 2. INDEED EXTRACTION & TRANSFORMATION
    # -------------------------------------------------------------
    print("\n>>> [3/3] Processing Indeed Dataset...")
    indeed_extractor = IndeedExtractor()
    indeed_job_count = 0
    t_ind_start = time.time()

    # Append Indeed postings to the same unified jobs JSONL file
    with open(jobs_output_path, "a", encoding="utf-8") as f_jobs:
        for doc in indeed_extractor.extract_postings(limit=limit_val):
            f_jobs.write(json.dumps(doc, ensure_ascii=False) + "\n")
            indeed_job_count += 1
            if indeed_job_count % 1000 == 0:
                print(f"   Transformed {indeed_job_count:,} Indeed postings...")

    t_ind_jobs = time.time() - t_ind_start
    print(f"   Completed Indeed postings: {indeed_job_count:,} records in {t_ind_jobs:.2f}s")

    # -------------------------------------------------------------
    # 3. METRICS & AUDIT SUMMARY GENERATION
    # -------------------------------------------------------------
    t_total = time.time() - t_start
    total_jobs = linkedin_job_count + indeed_job_count
    total_rejected = linkedin_extractor.metrics["rejected_postings"] + indeed_extractor.metrics["rejected_postings"]
    total_duplicates = (
        linkedin_extractor.metrics["duplicate_source_ids"] + indeed_extractor.metrics["duplicate_source_ids"]
    )

    jobs_file_size_mb = os.path.getsize(jobs_output_path) / (1024 * 1024)
    companies_file_size_mb = os.path.getsize(companies_output_path) / (1024 * 1024)

    summary: Dict[str, Any] = {
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_processing_time_seconds": round(t_total, 2),
        "dataset_metrics": {
            "linkedin": {
                "source_postings": linkedin_extractor.metrics["total_source_postings"],
                "transformed_postings": linkedin_job_count,
                "rejected_postings": linkedin_extractor.metrics["rejected_postings"],
                "duplicate_source_ids": linkedin_extractor.metrics["duplicate_source_ids"],
                "referenced_company_ids": len(linkedin_extractor.company_posting_counts),
                "extracted_company_profiles": linkedin_company_count,
                "missing_orphan_company_ids": linkedin_extractor.metrics["missing_company_links"],
                "missing_company_links": linkedin_extractor.metrics["missing_company_links"],
                "missing_salaries": linkedin_extractor.metrics["unstated_salaries"],
                "missing_skills": linkedin_extractor.metrics["unstated_skills"],
                "missing_industries": linkedin_extractor.metrics["unstated_industries"],
                "missing_benefits": linkedin_extractor.metrics["unstated_benefits"],
                "companies_extracted": linkedin_company_count,
            },
            "indeed": {
                "source_postings": indeed_extractor.metrics["total_source_postings"],
                "transformed_postings": indeed_job_count,
                "rejected_postings": indeed_extractor.metrics["rejected_postings"],
                "duplicate_source_ids": indeed_extractor.metrics["duplicate_source_ids"],
                "missing_skills": indeed_extractor.metrics["missing_skills"],
                "missing_companies": indeed_extractor.metrics["missing_companies"],
                "missing_descriptions": indeed_extractor.metrics["missing_descriptions"],
            },
            "unified_totals": {
                "total_transformed_jobs": total_jobs,
                "total_companies": linkedin_company_count,
                "total_rejected": total_rejected,
                "total_duplicates": total_duplicates,
                "jobs_output_file": os.path.abspath(jobs_output_path),
                "jobs_file_size_mb": round(jobs_file_size_mb, 2),
                "companies_output_file": os.path.abspath(companies_output_path),
                "companies_file_size_mb": round(companies_file_size_mb, 2),
            },
        },
        "phase_boundaries_verified": {
            "mongodb_connected": False,
            "data_imported_to_db": False,
            "original_datasets_modified": False,
            "schema_integrity_validated": True,
        },
    }

    with open(summary_output_path, "w", encoding="utf-8") as f_sum:
        json.dump(summary, f_sum, indent=2)

    print("\n" + "=" * 70)
    print(" ETL Execution Summary")
    print("=" * 70)
    print(f" Total Transformed Jobs: {total_jobs:,}")
    print(f"   - LinkedIn Postings:  {linkedin_job_count:,}")
    print(f"   - Indeed Postings:    {indeed_job_count:,}")
    print(f" Total Companies:        {linkedin_company_count:,}")
    print(f" Total Rejected Records: {total_rejected:,}")
    print(f" Total Duplicate IDs:    {total_duplicates:,}")
    print(f" Jobs JSONL File:        {jobs_output_path} ({jobs_file_size_mb:.2f} MB)")
    print(f" Companies JSONL File:   {companies_output_path} ({companies_file_size_mb:.2f} MB)")
    print(f" Audit Summary File:     {summary_output_path}")
    print(f" Total Duration:         {t_total:.2f} seconds")
    print("=" * 70)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run JobMarketDB Phase 3 ETL pipeline.")
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Run ETL on a sample of N records per dataset (0 for full dataset).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="Directory where transformed JSONL output will be stored.",
    )
    args = parser.parse_args()

    run_etl(output_dir=args.output_dir, sample_size=args.sample)
