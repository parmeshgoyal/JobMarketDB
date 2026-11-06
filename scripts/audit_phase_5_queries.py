"""
JobMarketDB - Reproducible Query Plan & ExecutionStats Audit Suite (Phase 5)

Executes explain("executionStats") for all representative operational queries (Operations 1-7)
and analytical aggregation pipelines (Operations 8-12) against the actual MongoDB database 'jobmarketdb'.

Captures:
- Exact winning-plan stages and actual index names (via recursive stage walking)
- totalKeysExamined, totalDocsExamined, nReturned, executionTimeMillis
- Scan types: IXSCAN, TEXT_INDEX, COVERED_IXSCAN, COLLSCAN
- Verifies documented collection scans for regex title search, unanchored continuous salary,
  and company_id lookups on the 'jobs' collection.
- Never modifies any documents or indexes.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import close_connection, get_connection_config, get_database


def walk_winning_plan(node: Any, stages: List[str], indexes: List[str]) -> None:
    """Recursively traverses query planner nodes to extract all stages and index names."""
    if not node or not isinstance(node, dict):
        return
    stage = node.get("stage")
    if stage and stage not in stages:
        stages.append(stage)
    idx = node.get("indexName")
    if idx and idx not in indexes:
        indexes.append(idx)
    if "inputStage" in node:
        walk_winning_plan(node["inputStage"], stages, indexes)
    if "inputStages" in node:
        for sub in node["inputStages"]:
            walk_winning_plan(sub, stages, indexes)
    if "queryPlan" in node:
        walk_winning_plan(node["queryPlan"], stages, indexes)


def extract_execution_details(explain_res: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts normalized execution stats and plan stages from explain output."""
    qp = explain_res.get("queryPlanner", {})
    wp = qp.get("winningPlan", {})
    stats = explain_res.get("executionStats", {})

    stages: List[str] = []
    indexes: List[str] = []
    walk_winning_plan(wp, stages, indexes)

    # In aggregation pipelines, stages may be in explain_res["stages"]
    if "stages" in explain_res:
        for st in explain_res["stages"]:
            cursor = st.get("$cursor", {})
            if cursor:
                c_wp = cursor.get("queryPlanner", {}).get("winningPlan", {})
                walk_winning_plan(c_wp, stages, indexes)
                c_stats = cursor.get("executionStats", {})
                if c_stats:
                    stats = c_stats
            else:
                for k in st.keys():
                    if k not in stages:
                        stages.append(k)

    # Determine scan type
    docs_examined = stats.get("totalDocsExamined", 0)
    keys_examined = stats.get("totalKeysExamined", 0)

    if not indexes:
        scan_type = "COLLSCAN"
    elif "TEXT_MATCH" in stages or "TEXT" in stages:
        scan_type = "TEXT_INDEX"
    elif docs_examined == 0 and keys_examined > 0:
        scan_type = "COVERED_IXSCAN"
    else:
        scan_type = "IXSCAN"

    return {
        "winning_stage": wp.get("stage") or (stages[0] if stages else "UNKNOWN"),
        "stages": stages,
        "index_name": indexes[0] if indexes else "None (COLLSCAN)",
        "all_indexes": indexes,
        "scan_type": scan_type,
        "totalKeysExamined": keys_examined,
        "totalDocsExamined": docs_examined,
        "nReturned": stats.get("nReturned", 0),
        "executionTimeMillis": stats.get("executionTimeMillis", 0),
    }


def run_query_plan_audit(close_conn_at_end: bool = False) -> Dict[str, Any]:
    print("=" * 80)
    print(" JobMarketDB — Reproducible Query Plan & ExecutionStats Audit Suite (Phase 5)")
    print("=" * 80)

    uri, db_name = get_connection_config()
    db = get_database(db_name)

    initial_jobs = db["jobs"].count_documents({})
    initial_comp = db["companies"].count_documents({})
    initial_jobs_indexes = db["jobs"].index_information()
    initial_comp_indexes = db["companies"].index_information()
    print(f" Database Deployment: {db_name}")
    print(f" Baseline Counts: jobs={initial_jobs:,}, companies={initial_comp:,}")
    print(f" Baseline Indexes: jobs={len(initial_jobs_indexes)}, companies={len(initial_comp_indexes)}\n")

    operational_queries = [
        ("Op 1a: Job Search (Full-Text)", {"$text": {"$search": "Data Scientist"}}, "TEXT_INDEX", "title_text_description_text"),
        ("Op 1b: Job Search (Title Regex)", {"title": {"$regex": "Data Scientist", "$options": "i"}}, "COLLSCAN", "None (COLLSCAN)"),
        ("Op 2a: Location (CA, remote=True)", {"location.state": "CA", "location.is_remote": True}, "IXSCAN", "location.state_1_location.is_remote_1"),
        ("Op 2b: Location (NY, remote=None)", {"location.state": "NY", "location.is_remote": None}, "IXSCAN", "location.state_1_location.is_remote_1"),
        ("Op 3a: Salary Bucket ('100000-119999')", {"salary.salary_bucket": "100000-119999"}, "IXSCAN", "salary.salary_bucket_1_salary.normalized_annual_1"),
        ("Op 3b: Salary Continuous Alone ($100k-$120k)", {"salary.normalized_annual": {"$gte": 100000.0, "$lte": 120000.0}}, "COLLSCAN", "None (COLLSCAN)"),
        ("Op 3c: Salary Bucket + Continuous", {"salary.salary_bucket": "100000-119999", "salary.normalized_annual": {"$gte": 100000.0, "$lte": 120000.0}}, "IXSCAN", "salary.salary_bucket_1_salary.normalized_annual_1"),
        ("Op 4a: Skills Demand ($all ['Python', 'SQL'])", {"skills": {"$all": ["Python", "SQL"]}}, "IXSCAN", "skills_1"),
        ("Op 4b: Skills Demand ($in ['Python'])", {"skills": {"$in": ["Python"]}}, "IXSCAN", "skills_1"),
        ("Op 5a: Company Name ('Express Scripts')", {"company.name": "Express Scripts"}, "IXSCAN", "company.name_1"),
        ("Op 5b: Company ID (23729571 - Orphan)", {"company.company_id": 23729571}, "COLLSCAN", "None (COLLSCAN)"),
        ("Op 6: Experience Level ('Mid-Senior level')", {"experience_level.value": "Mid-Senior level"}, "IXSCAN", "experience_level.value_1"),
        ("Op 7a: Source Platform ('linkedin')", {"source": "linkedin"}, "IXSCAN", "source_1"),
        ("Op 7b: Source Platform ('indeed')", {"source": "indeed"}, "IXSCAN", "source_1"),
    ]

    print(">>> 1. Auditing Operational Queries (Operations 1 to 7)...")
    op_results = {}
    for name, q_filter, expected_scan, expected_idx in operational_queries:
        cmd = {
            "explain": {"find": "jobs", "filter": q_filter},
            "verbosity": "executionStats",
        }
        res = db.command(cmd)
        details = extract_execution_details(res)
        details["expected_scan_type"] = expected_scan
        details["expected_index"] = expected_idx
        details["filter"] = str(q_filter)

        scan_matched = details["scan_type"] == expected_scan
        idx_matched = (expected_idx == "None (COLLSCAN)" and details["scan_type"] == "COLLSCAN") or (details["index_name"] == expected_idx)
        details["audit_pass"] = scan_matched and idx_matched

        print(f"  [{'PASS' if details['audit_pass'] else 'FAIL'}] {name}")
        print(f"       Scan Type: {details['scan_type']} (Expected: {expected_scan}) | Index: '{details['index_name']}'")
        print(f"       Keys Examined: {details['totalKeysExamined']:,} | Docs Examined: {details['totalDocsExamined']:,} | Returned: {details['nReturned']:,} ({details['executionTimeMillis']}ms)")

        op_results[name] = details

    print("\n>>> 2. Auditing Analytical Aggregations (Operations 8 to 12)...")
    aggregations = [
        (
            "Op 8: Top Skills (Unconstrained)",
            [
                {"$project": {"skills": {"$setUnion": [{"$ifNull": ["$skills", []]}, []]}}},
                {"$unwind": "$skills"},
                {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5},
            ],
            "COLLSCAN",
            "None (COLLSCAN)",
            "Unconstrained unwind scans collection across all postings.",
        ),
        (
            "Op 8b: Top Skills (Filtered by source='indeed')",
            [
                {"$match": {"source": "indeed"}},
                {"$project": {"skills": {"$setUnion": [{"$ifNull": ["$skills", []]}, []]}}},
                {"$unwind": "$skills"},
                {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5},
            ],
            "IXSCAN",
            "source_1",
            "Initial $match pushes index scan on source_1.",
        ),
        (
            "Op 9: Top Hiring Companies",
            [
                {"$match": {"company.name": {"$ne": None}}},
                {"$group": {"_id": "$company.name", "postings_count": {"$sum": 1}, "sources": {"$addToSet": "$source"}}},
                {"$sort": {"postings_count": -1}},
                {"$limit": 5},
            ],
            "IXSCAN",
            "company.name_1",
            "Pushes index scan on company.name_1 with bounds [MinKey, null), (null, MaxKey].",
        ),
        (
            "Op 10: Top Job Locations",
            [
                {"$match": {"location.state": {"$ne": None}}},
                {"$group": {"_id": "$location.state", "postings_count": {"$sum": 1}}},
                {"$sort": {"postings_count": -1}},
                {"$limit": 5},
            ],
            "COVERED_IXSCAN",
            "location.state_1_location.is_remote_1",
            "Covered index scan: 0 document fetches (totalDocsExamined = 0).",
        ),
        (
            "Op 11: Salary Distributions",
            [
                {"$match": {"salary.salary_bucket": {"$ne": None}}},
                {
                    "$group": {
                        "_id": "$salary.salary_bucket",
                        "total_count": {"$sum": 1},
                        "linkedin_count": {"$sum": {"$cond": [{"$eq": ["$source", "linkedin"]}, 1, 0]}},
                        "indeed_count": {"$sum": {"$cond": [{"$eq": ["$source", "indeed"]}, 1, 0]}},
                        "linkedin_avg": {"$avg": {"$cond": [{"$eq": ["$source", "linkedin"]}, "$salary.normalized_annual", None]}},
                        "indeed_avg": {"$avg": {"$cond": [{"$eq": ["$source", "indeed"]}, "$salary.estimated_midpoint", None]}},
                    }
                },
            ],
            "IXSCAN",
            "salary.salary_bucket_1_salary.normalized_annual_1",
            "Initial $match pushes index scan; document fields are fetched for group accumulators.",
        ),
        (
            "Op 12: Cross-Platform Comparison",
            [
                {"$group": {"_id": "$source", "count": {"$sum": 1}}},
            ],
            "COLLSCAN",
            "None (COLLSCAN)",
            "Market-wide summary scans all documents.",
        ),
    ]

    agg_results = {}
    for name, pipe, expected_scan, expected_idx, note in aggregations:
        cmd = {
            "explain": {"aggregate": "jobs", "pipeline": pipe, "cursor": {}},
            "verbosity": "executionStats",
        }
        res = db.command(cmd)
        details = extract_execution_details(res)
        details["expected_scan_type"] = expected_scan
        details["expected_index"] = expected_idx
        details["architectural_note"] = note

        scan_matched = details["scan_type"] == expected_scan
        idx_matched = (expected_idx == "None (COLLSCAN)" and details["scan_type"] == "COLLSCAN") or (details["index_name"] == expected_idx)
        details["audit_pass"] = scan_matched and idx_matched

        print(f"  [{'PASS' if details['audit_pass'] else 'FAIL'}] {name}")
        print(f"       Scan Type: {details['scan_type']} (Expected: {expected_scan}) | Index: '{details['index_name']}'")
        print(f"       Keys Examined: {details['totalKeysExamined']:,} | Docs Examined: {details['totalDocsExamined']:,} | Returned: {details['nReturned']:,} ({details['executionTimeMillis']}ms)")
        print(f"       Note: {note}")

        agg_results[name] = details

    # Database and Index invariant check
    final_jobs = db["jobs"].count_documents({})
    final_comp = db["companies"].count_documents({})
    final_jobs_indexes = db["jobs"].index_information()
    final_comp_indexes = db["companies"].index_information()

    counts_pass = (initial_jobs == 129550 and final_jobs == 129550 and initial_comp == 24472 and final_comp == 24472)
    indexes_pass = (initial_jobs_indexes == final_jobs_indexes and initial_comp_indexes == final_comp_indexes)
    integrity_pass = counts_pass and indexes_pass

    print("\n>>> 3. Database Safety & Invariant Verification...")
    print(f"  - Initial Jobs: {initial_jobs:,} | Final Jobs: {final_jobs:,} (Delta: {final_jobs - initial_jobs})")
    print(f"  - Initial Companies: {initial_comp:,} | Final Companies: {final_comp:,} (Delta: {final_comp - initial_comp})")
    print(f"  - jobs indexes invariant: {'PASS' if initial_jobs_indexes == final_jobs_indexes else 'FAIL'}")
    print(f"  - companies indexes invariant: {'PASS' if initial_comp_indexes == final_comp_indexes else 'FAIL'}")
    print(f"  - Read-Only Invariant: {'PASS' if integrity_pass else 'FAIL'}")

    all_op_passed = all(r["audit_pass"] for r in op_results.values())
    all_agg_passed = all(r["audit_pass"] for r in agg_results.values())
    overall_passed = all_op_passed and all_agg_passed and integrity_pass

    audit_artifact = {
        "audit_name": "Phase 5 Query Plan and ExecutionStats Reproducible Audit",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "database": db_name,
        "database_integrity": {
            "initial_jobs": initial_jobs,
            "final_jobs": final_jobs,
            "delta_jobs": final_jobs - initial_jobs,
            "initial_companies": initial_comp,
            "final_companies": final_comp,
            "delta_companies": final_comp - initial_comp,
            "initial_jobs_indexes_count": len(initial_jobs_indexes),
            "final_jobs_indexes_count": len(final_jobs_indexes),
            "initial_companies_indexes_count": len(initial_comp_indexes),
            "final_companies_indexes_count": len(final_comp_indexes),
            "indexes_strictly_unchanged": indexes_pass,
            "read_only_invariant_preserved": integrity_pass,
        },
        "overall_audit_passed": overall_passed,
        "operational_queries_count": len(op_results),
        "aggregation_pipelines_count": len(agg_results),
        "total_cases_audited": len(op_results) + len(agg_results),
        "operational_queries": op_results,
        "aggregation_pipelines": agg_results,
    }

    out_path = os.path.join("data", "processed", "phase_5_query_plan_audit.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit_artifact, f, indent=2)

    print(f"\nAudit artifact saved to: {out_path}")
    print("=" * 80)
    if close_conn_at_end:
        close_connection()
    return audit_artifact


if __name__ == "__main__":
    res = run_query_plan_audit(close_conn_at_end=True)
    sys.exit(0 if res["overall_audit_passed"] else 1)
