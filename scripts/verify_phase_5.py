"""
JobMarketDB - Comprehensive Phase 5 Verification & Test Suite

Executes and verifies all 12 core query and analytics operations against MongoDB database 'jobmarketdb':
1. Job search by title (full-text search and title regex)
2. Location filtering (compound index: state + tri-state remote)
3. Salary filtering (salary bucket, continuous range, and combined)
4. Skill-demand filtering ($all, $in) and distinct posting semantics
5. Company filtering (company name and orphan company_id)
6. Experience-level filtering
7. Source filtering (LinkedIn and Indeed)
8. Top demanded skills aggregation (combined and separate platform rankings)
9. Top hiring companies aggregation
10. Top job locations aggregation (covered index scan verification)
11. Salary distributions aggregation (outlier audit, median, threshold-adjusted mean)
12. LinkedIn vs Indeed comparison aggregation

Verifies:
- Statistical reproducibility of all metrics
- Outlier audit classification and threshold-adjusted metrics
- Distinct posting skill-count semantics (zero token duplication)
- Recursive executionStats query plan analysis (IXSCAN, TEXT_INDEX, COVERED_IXSCAN, COLLSCAN)
- Read-only safety (document counts strictly remain 129,550 jobs and 24,472 companies)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analytics.service import JobMarketAnalyticsService
from database.connection import close_connection, get_connection_config, get_database
from scripts.audit_phase_5_queries import extract_execution_details


def run_phase_5_verification() -> bool:
    print("=" * 80)
    print(" JobMarketDB — Phase 5 Core Query & Analytics Layer Verification Suite")
    print("=" * 80)

    uri, db_name = get_connection_config()
    db = get_database(db_name)
    service = JobMarketAnalyticsService(db)

    # 1. Baseline Document Counts and Index Definitions (Must be strictly preserved)
    initial_jobs = db["jobs"].count_documents({})
    initial_comp = db["companies"].count_documents({})
    initial_jobs_indexes = db["jobs"].index_information()
    initial_comp_indexes = db["companies"].index_information()

    print(f" Initial Database State:")
    print(f"    - Target Database:   {db_name}")
    print(f"    - jobs:              {initial_jobs:,} (Expected: 129,550)")
    print(f"    - companies:         {initial_comp:,} (Expected: 24,472)")
    print(f"    - jobs indexes:      {len(initial_jobs_indexes)} verified")
    print(f"    - companies indexes: {len(initial_comp_indexes)} verified")

    if initial_jobs != 129550 or initial_comp != 24472:
        print(" [FAIL] Initial document counts do not match verified Phase 4 baselines!")
        return False

    all_passed = True
    operation_results: Dict[str, Any] = {}

    # -------------------------------------------------------------------------
    # Operation 1: Job Search by Title
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 1: Job Search by Title...")
    t0 = time.time()
    op1_docs, op1_count = service.search_jobs("Data Scientist", search_mode="text", limit=5)
    t1 = time.time() - t0
    print(f"    - Query: 'Data Scientist' (Text Search) | Matches: {op1_count:,} | Duration: {t1:.3f}s")
    for d in op1_docs[:2]:
        print(f"      * [{d.get('source')}] {d.get('title')} | Company: {d.get('company', {}).get('name')}")
    op1_pass = op1_count > 0 and len(op1_docs) > 0 and all("source" in d and "source_job_id" in d for d in op1_docs)
    print(f"    - Operation 1 Status: {'PASS' if op1_pass else 'FAIL'}")
    all_passed = all_passed and op1_pass
    operation_results["op1_job_search_by_title"] = {
        "status": "PASS" if op1_pass else "FAIL",
        "matches": op1_count,
        "sample_returned": len(op1_docs),
        "duration_seconds": round(t1, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 2: Location & Tri-State Remote Filtering
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 2: Location & Tri-State Remote Filtering...")
    t0 = time.time()
    ca_remote_docs, ca_remote_count = service.filter_by_location(state="CA", is_remote=True, limit=5)
    ny_unknown_docs, ny_unknown_count = service.filter_by_location(state="NY", is_remote=None, limit=5)
    t2 = time.time() - t0
    print(f"    - Filter: state='CA', is_remote=True  | Matches: {ca_remote_count:,}")
    print(f"    - Filter: state='NY', is_remote=None  | Matches: {ny_unknown_count:,} | Duration: {t2:.3f}s")
    op2_pass = ca_remote_count == 975 and ny_unknown_count > 0
    print(f"    - Operation 2 Status: {'PASS' if op2_pass else 'FAIL'}")
    all_passed = all_passed and op2_pass
    operation_results["op2_location_filtering"] = {
        "status": "PASS" if op2_pass else "FAIL",
        "ca_remote_count": ca_remote_count,
        "ny_unknown_remote_count": ny_unknown_count,
        "duration_seconds": round(t2, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 3: Salary Range & Bucket Filtering
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 3: Salary Range & Bucket Filtering...")
    t0 = time.time()
    b_docs, b_count = service.filter_by_salary(salary_bucket="100000-119999", limit=5)
    ann_docs, ann_count = service.filter_by_salary(min_annual=100000, max_annual=120000, limit=5)
    t3 = time.time() - t0
    print(f"    - Filter: bucket='100000-119999'      | Matches: {b_count:,}")
    print(f"    - Filter: annual [100k, 120k]          | Matches: {ann_count:,} | Duration: {t3:.3f}s")
    all_ann_valid = all(d.get("salary", {}).get("normalized_annual") is not None for d in ann_docs)
    indeed_continuous = db["jobs"].count_documents({"source": "indeed", "salary.normalized_annual": {"$ne": None}})
    op3_pass = b_count == 5486 and ann_count == 4358 and all_ann_valid and indeed_continuous == 0
    print(f"    - Indeed continuous salary violations: {indeed_continuous}")
    print(f"    - Operation 3 Status: {'PASS' if op3_pass else 'FAIL'}")
    all_passed = all_passed and op3_pass
    operation_results["op3_salary_filtering"] = {
        "status": "PASS" if op3_pass else "FAIL",
        "bucket_100k_120k_matches": b_count,
        "continuous_100k_120k_matches": ann_count,
        "indeed_continuous_violations": indeed_continuous,
        "duration_seconds": round(t3, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 4: Skill Demand Filtering & Token Uniqueness Verification
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 4: Skill Demand Filtering & Token Uniqueness...")
    t0 = time.time()
    skill_docs, skill_count = service.filter_by_skills(["Python", "SQL"], match_all=True, limit=5)
    t4 = time.time() - t0
    print(f"    - Filter: skills $all ['Python', 'SQL'] | Matches: {skill_count:,} | Duration: {t4:.3f}s")
    for d in skill_docs[:2]:
        print(f"      * {d.get('title')} | Skills: {d.get('skills')}")
    op4_pass = skill_count == 2075 and all("Python" in d.get("skills", []) and "SQL" in d.get("skills", []) for d in skill_docs)

    # Distinct posting token guarantee check
    print("    - Verifying distinct posting token guarantee across database...")
    dup_check_pipe = [
        {"$project": {"skills_count": {"$size": {"$ifNull": ["$skills", []]}}, "skills": 1}},
        {"$match": {"skills_count": {"$gt": 1}}},
    ]
    multi_skill_docs = list(db["jobs"].aggregate(dup_check_pipe))
    dup_docs_count = sum(1 for d in multi_skill_docs if len(d.get("skills", [])) != len(set(d.get("skills", []))))
    print(f"      * Multi-skill postings audited: {len(multi_skill_docs):,} | Duplicate token arrays found: {dup_docs_count}")
    token_guarantee_pass = (dup_docs_count == 0)

    op4_pass = op4_pass and token_guarantee_pass
    print(f"    - Operation 4 Status: {'PASS' if op4_pass else 'FAIL'}")
    all_passed = all_passed and op4_pass
    operation_results["op4_skill_filtering"] = {
        "status": "PASS" if op4_pass else "FAIL",
        "matches_python_sql": skill_count,
        "multi_skill_postings_checked": len(multi_skill_docs),
        "duplicate_token_postings": dup_docs_count,
        "token_uniqueness_guarantee_verified": token_guarantee_pass,
        "duration_seconds": round(t4, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 5: Company Filtering & Orphan Handling
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 5: Company Filtering & Orphan Handling...")
    t0 = time.time()
    comp_docs, comp_count = service.filter_by_company(company_name="Express Scripts", limit=5)
    orphan_docs, orphan_count = service.filter_by_company(company_id=23729571, limit=5)
    t5 = time.time() - t0
    print(f"    - Filter: company.name='Express Scripts' | Matches: {comp_count:,}")
    print(f"    - Filter: company.company_id=23729571   | Matches: {orphan_count:,} (Orphan Posting) | Duration: {t5:.3f}s")
    op5_pass = comp_count == 2 and orphan_count == 1 and orphan_docs[0].get("company", {}).get("name") is None
    print(f"    - Operation 5 Status: {'PASS' if op5_pass else 'FAIL'}")
    all_passed = all_passed and op5_pass
    operation_results["op5_company_filtering"] = {
        "status": "PASS" if op5_pass else "FAIL",
        "express_scripts_matches": comp_count,
        "orphan_company_matches": orphan_count,
        "orphan_name_is_null": orphan_docs[0].get("company", {}).get("name") is None if orphan_docs else False,
        "duration_seconds": round(t5, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 6: Experience Level Filtering
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 6: Experience Level Filtering...")
    t0 = time.time()
    exp_docs, exp_count = service.filter_by_experience("Mid-Senior level", limit=5)
    t6 = time.time() - t0
    print(f"    - Filter: experience_level.value='Mid-Senior level' | Matches: {exp_count:,} | Duration: {t6:.3f}s")
    op6_pass = exp_count == 41488 and all(d.get("experience_level", {}).get("value") == "Mid-Senior level" for d in exp_docs)
    print(f"    - Operation 6 Status: {'PASS' if op6_pass else 'FAIL'}")
    all_passed = all_passed and op6_pass
    operation_results["op6_experience_filtering"] = {
        "status": "PASS" if op6_pass else "FAIL",
        "mid_senior_matches": exp_count,
        "duration_seconds": round(t6, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 7: Source Platform Filtering
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 7: Source Platform Filtering...")
    t0 = time.time()
    li_docs, li_count = service.filter_by_source("linkedin", limit=5)
    ind_docs, ind_count = service.filter_by_source("indeed", limit=5)
    t7 = time.time() - t0
    print(f"    - Filter: source='linkedin' | Matches: {li_count:,}")
    print(f"    - Filter: source='indeed'   | Matches: {ind_count:,} | Duration: {t7:.3f}s")
    op7_pass = li_count == 123835 and ind_count == 5715
    print(f"    - Operation 7 Status: {'PASS' if op7_pass else 'FAIL'}")
    all_passed = all_passed and op7_pass
    operation_results["op7_source_filtering"] = {
        "status": "PASS" if op7_pass else "FAIL",
        "linkedin_matches": li_count,
        "indeed_matches": ind_count,
        "duration_seconds": round(t7, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 8: Top Demanded Skills Aggregation & Priority 2 Platform Checks
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 8: Top Demanded Skills & Platform Taxonomy Separation...")
    t0 = time.time()
    skills_agg = service.get_top_skills(limit=5)
    platform_skills = service.get_skills_by_platform(limit=5)
    t8 = time.time() - t0

    print(f"    - Overall Top 5 Skills (Population-Weighted Combined View, {t8:.3f}s):")
    for s in skills_agg["skills"]:
        print(f"      * {s['skill']}: {s['count']:,} postings ({s['percentage_of_postings']}%)")

    top_skill_name = skills_agg["skills"][0]["skill"]
    top_skill_count = skills_agg["skills"][0]["count"]

    li_top = platform_skills["linkedin"]["skills"][0]
    ind_top = platform_skills["indeed"]["skills"][0]
    print(f"    - LinkedIn Top Discipline: '{li_top['skill']}' ({li_top['count']:,} / {platform_skills['linkedin']['total_postings']:,} = {li_top['percentage_of_postings']}%)")
    print(f"    - Indeed Top Tool:         '{ind_top['skill']}' ({ind_top['count']:,} / {platform_skills['indeed']['total_postings']:,} = {ind_top['percentage_of_postings']}%)")

    # Priority 2 validations
    p2_pass = (
        len(skills_agg["skills"]) == 5
        and top_skill_name == "Information Technology"
        and top_skill_count == 25252
        and platform_skills["linkedin"]["total_postings"] == 123835
        and platform_skills["indeed"]["total_postings"] == 5715
        and li_top["skill"] == "Information Technology"
        and li_top["count"] == 25252
        and li_top["percentage_of_postings"] == 20.39
        and ind_top["skill"] == "Python"
        and ind_top["count"] == 3325
        and ind_top["percentage_of_postings"] == 58.18
        and "cross_platform_taxonomy_warning" in platform_skills
    )

    # Edge cases check: nonexistent role category (with valid limit) and negative limit rejection
    nonexistent_res = service.get_skills_by_platform(limit=5, role_category="NonexistentRoleXYZ")
    nonexistent_pass = (
        nonexistent_res["linkedin"]["total_postings"] == 0
        and nonexistent_res["indeed"]["total_postings"] == 0
        and len(nonexistent_res["linkedin"]["skills"]) == 0
        and len(nonexistent_res["indeed"]["skills"]) == 0
    )
    try:
        service.get_skills_by_platform(limit=-5, role_category="Engineering")
        neg_limit_rejected = False
    except ValueError:
        neg_limit_rejected = True

    edge_cases_pass = nonexistent_pass and neg_limit_rejected
    print(f"    - Edge Cases Validation (Nonexistent Role & Negative Limit): {'PASS' if edge_cases_pass else 'FAIL'}")

    op8_pass = p2_pass and edge_cases_pass
    print(f"    - Operation 8 Status: {'PASS' if op8_pass else 'FAIL'}")
    all_passed = all_passed and op8_pass
    operation_results["op8_top_skills"] = {
        "status": "PASS" if op8_pass else "FAIL",
        "top_skill_combined": top_skill_name,
        "top_skill_count_combined": top_skill_count,
        "linkedin_top_discipline": li_top["skill"],
        "linkedin_top_count": li_top["count"],
        "linkedin_top_percentage": li_top["percentage_of_postings"],
        "indeed_top_tool": ind_top["skill"],
        "indeed_top_count": ind_top["count"],
        "indeed_top_percentage": ind_top["percentage_of_postings"],
        "edge_cases_handled": edge_cases_pass,
        "duration_seconds": round(t8, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 9: Top Hiring Companies Aggregation
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 9: Top Hiring Companies Aggregation...")
    t0 = time.time()
    comp_agg = service.get_top_companies(limit=5)
    t9 = time.time() - t0
    print(f"    - Top 5 Hiring Companies ({t9:.3f}s):")
    for c in comp_agg["companies"]:
        print(f"      * {c['company_name']}: {c['postings_count']:,} postings | platforms: {c['platforms']}")
    top_company_name = comp_agg["companies"][0]["company_name"]
    top_company_count = comp_agg["companies"][0]["postings_count"]
    op9_pass = len(comp_agg["companies"]) == 5 and top_company_name == "Liberty Healthcare and Rehabilitation Services" and top_company_count == 1108
    print(f"    - Operation 9 Status: {'PASS' if op9_pass else 'FAIL'}")
    all_passed = all_passed and op9_pass
    operation_results["op9_top_companies"] = {
        "status": "PASS" if op9_pass else "FAIL",
        "top_company": top_company_name,
        "top_company_count": top_company_count,
        "duration_seconds": round(t9, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 10: Top Job Locations Aggregation
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 10: Top Job Locations Aggregation...")
    t0 = time.time()
    loc_agg = service.get_top_locations(limit=5)
    t10 = time.time() - t0
    print(f"    - Top 5 States ({t10:.3f}s):")
    for l in loc_agg["locations"]:
        print(f"      * {l['state']}: {l['postings_count']:,} postings")
    top_state = loc_agg["locations"][0]["state"]
    top_state_count = loc_agg["locations"][0]["postings_count"]
    op10_pass = len(loc_agg["locations"]) == 5 and top_state == "CA" and top_state_count == 13892
    print(f"    - Operation 10 Status: {'PASS' if op10_pass else 'FAIL'}")
    all_passed = all_passed and op10_pass
    operation_results["op10_top_locations"] = {
        "status": "PASS" if op10_pass else "FAIL",
        "top_state": top_state,
        "top_state_count": top_state_count,
        "duration_seconds": round(t10, 4),
    }

    # -------------------------------------------------------------------------
    # Operation 11: Salary Distributions & Priority 1 Outlier Audit Tests
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 11: Salary Distributions & Priority 1 Outlier Tests...")
    t0 = time.time()
    sal_agg = service.get_salary_distribution()
    t11 = time.time() - t0
    print(f"    - Salary Buckets ({t11:.3f}s): {len(sal_agg['buckets'])} buckets found")

    # Safe null-handling formatting
    for b in sal_agg["buckets"]:
        li_avg_str = f"${b['linkedin_avg_normalized_annual']:,.2f}" if b.get("linkedin_avg_normalized_annual") is not None else "None"
        li_med_str = f"${b['linkedin_approx_median_annual']:,.2f}" if b.get("linkedin_approx_median_annual") is not None else "None"
        li_adj_str = f"${b['linkedin_threshold_adjusted_avg_annual']:,.2f}" if b.get("linkedin_threshold_adjusted_avg_annual") is not None else "None"
        ind_avg_str = f"${b['indeed_avg_estimated_midpoint']:,.2f}" if b.get("indeed_avg_estimated_midpoint") is not None else "None"
        print(f"      * Bucket '{b['salary_bucket']}': {b['total_count']:,} postings | LI: {b['linkedin_count']:,} (Unadjusted Avg: {li_avg_str}, Approx Median: {li_med_str}, Threshold-Adjusted Avg: {li_adj_str}) | Ind: {b['indeed_count']:,} (Avg Midpoint: {ind_avg_str})")

    # Find bucket >160000 safely
    b_gt_160k = next((b for b in sal_agg["buckets"] if b["salary_bucket"] == ">160000"), None)

    if b_gt_160k is None:
        p1_gt_160k_pass = False
        print("    - [FAIL] Expected salary bucket '>160000' is missing from aggregation result!")
    else:
        p1_gt_160k_pass = (
            b_gt_160k["linkedin_count"] == 4418
            and b_gt_160k["linkedin_approx_median_annual"] == 190000.0
            and b_gt_160k["linkedin_threshold_adjusted_avg_annual"] == 213464.73
            and b_gt_160k["linkedin_avg_normalized_annual"] == 1109368.91
            and b_gt_160k["outlier_count_gt_1m"] == 38
        )
        print(f"    - Bucket >160000 Verified Metrics:")
        print(f"        * LinkedIn Count:                    {b_gt_160k['linkedin_count']:,} (Expected: 4,418)")
        print(f"        * Approximate Median:                ${b_gt_160k['linkedin_approx_median_annual']:,.2f} (Expected: $190,000.00)")
        print(f"        * Threshold-Adjusted Mean (<$1M):    ${b_gt_160k['linkedin_threshold_adjusted_avg_annual']:,.2f} (Expected: $213,464.73)")
        print(f"        * Unadjusted Stored Mean:            ${b_gt_160k['linkedin_avg_normalized_annual']:,.2f} (Expected: $1,109,368.91)")
        print(f"        * Outlier Count (> $1,000,000):      {b_gt_160k['outlier_count_gt_1m']} (Expected: 38)")
        print(f"        * >160000 Verification Result:       {'PASS' if p1_gt_160k_pass else 'FAIL'}")

    # Verify source filtering keeps Indeed continuous annual salary statistics null
    indeed_only_agg = service.get_salary_distribution(source="indeed")
    indeed_has_no_norm = all(
        b["linkedin_avg_normalized_annual"] is None
        and b["linkedin_approx_median_annual"] is None
        and b["linkedin_threshold_adjusted_avg_annual"] is None
        and b["outlier_count_gt_1m"] == 0
        for b in indeed_only_agg["buckets"]
    )
    print(f"    - Source Filtering Provenance (Indeed has 0 continuous pay statistics): {indeed_has_no_norm}")

    # Verify LinkedIn filtering keeps Indeed midpoint null
    li_only_agg = service.get_salary_distribution(source="linkedin")
    li_has_no_midpoint = all(b["indeed_avg_estimated_midpoint"] is None for b in li_only_agg["buckets"])
    print(f"    - Source Filtering Provenance (LinkedIn has 0 Indeed midpoints): {li_has_no_midpoint}")

    op11_pass = len(sal_agg["buckets"]) == 6 and p1_gt_160k_pass and indeed_has_no_norm and li_has_no_midpoint
    print(f"    - Operation 11 Status: {'PASS' if op11_pass else 'FAIL'}")
    all_passed = all_passed and op11_pass
    operation_results["op11_salary_distributions"] = {
        "status": "PASS" if op11_pass else "FAIL",
        "buckets_count": len(sal_agg["buckets"]),
        "bucket_gt_160k_metrics": {
            "linkedin_count": b_gt_160k["linkedin_count"] if b_gt_160k else None,
            "approx_median": b_gt_160k["linkedin_approx_median_annual"] if b_gt_160k else None,
            "threshold_adjusted_mean": b_gt_160k["linkedin_threshold_adjusted_avg_annual"] if b_gt_160k else None,
            "unadjusted_mean": b_gt_160k["linkedin_avg_normalized_annual"] if b_gt_160k else None,
            "outliers_above_1m": b_gt_160k["outlier_count_gt_1m"] if b_gt_160k else None,
        },
        "indeed_continuous_pay_is_strictly_null": indeed_has_no_norm,
        "linkedin_midpoint_is_strictly_null": li_has_no_midpoint,
        "duration_seconds": round(t11, 4),
    }

    # -------------------------------------------------------------------------
    # Priority 1: Salary Outlier Audit Artifact Verification
    # -------------------------------------------------------------------------
    print("\n>>> Verifying Salary Outlier Audit Artifact (Priority 1)...")
    outlier_artifact_path = os.path.join("data", "processed", "phase_5_salary_outlier_audit.json")
    outlier_audit_pass = False
    art_recs = []
    art_counts = {}
    if not os.path.exists(outlier_artifact_path):
        print(f"    - [FAIL] Outlier audit artifact not found at {outlier_artifact_path}")
    else:
        try:
            with open(outlier_artifact_path, "r", encoding="utf-8") as f_art:
                art_data = json.load(f_art)
            art_recs = art_data.get("records", [])
            art_counts = art_data.get("category_counts", {})
            unique_ids = set(r.get("job_id") for r in art_recs)

            has_38_records = len(art_recs) == 38
            has_38_unique = len(unique_ids) == 38
            counts_match = (
                art_counts.get("Confirmed hourly-to-annual conversion error") == 19
                and art_counts.get("Recruiter/source salary-entry error") == 10
                and art_counts.get("Other confirmed issue") == 1
                and art_counts.get("Unresolved case") == 8
            )
            complete = all(
                r.get("evidence")
                and r.get("category")
                and (r.get("normalized_annual") is not None and r["normalized_annual"] > 1000000)
                for r in art_recs
            )
            outlier_audit_pass = has_38_records and has_38_unique and counts_match and complete
            print(f"    - Artifact Records Count:        {len(art_recs)} (Expected: 38)")
            print(f"    - Distinct Record IDs:           {len(unique_ids)} (Expected: 38)")
            print(f"    - Category Totals Verified:      {counts_match} (19 conversion, 10 recruiter, 1 other, 8 unresolved)")
            print(f"    - Completeness & Valid Evidence: {complete}")
            print(f"    - Outlier Audit Artifact Status: {'PASS' if outlier_audit_pass else 'FAIL'}")
        except Exception as e:
            print(f"    - [FAIL] Error parsing outlier audit artifact: {e}")
            outlier_audit_pass = False

    all_passed = all_passed and outlier_audit_pass
    operation_results["salary_outlier_audit_artifact"] = {
        "status": "PASS" if outlier_audit_pass else "FAIL",
        "total_records": len(art_recs),
        "unique_records": len(set(r.get("job_id") for r in art_recs)),
        "category_counts": art_counts,
        "artifact_path": "data/processed/phase_5_salary_outlier_audit.json",
    }

    # -------------------------------------------------------------------------
    # Operation 12: Cross-Platform Comparison Aggregation
    # -------------------------------------------------------------------------
    print("\n>>> Testing Operation 12: LinkedIn vs Indeed Comparison...")
    t0 = time.time()
    comp_res = service.compare_platforms()
    t12 = time.time() - t0
    print(f"    - Platform Comparison ({t12:.3f}s):")
    for p_name, p_data in comp_res["platforms"].items():
        print(f"      * Platform '{p_name}':")
        print(f"         Total Postings:        {p_data['total_postings']:,}")
        print(f"         Salary Coverage:       {p_data['salary_coverage']['postings_with_salary']:,} ({p_data['salary_coverage']['coverage_percentage']}%)")
        print(f"         Remote Breakdown:      explicitly_remote={p_data['remote_work_breakdown']['explicitly_remote']:,}, on_site={p_data['remote_work_breakdown']['explicitly_on_site']:,}, unknown={p_data['remote_work_breakdown']['unknown_unspecified']:,}")
        print(f"         Distinct Companies:    {p_data['coverage_metrics']['distinct_companies_count']:,}")
        print(f"         Distinct States:       {p_data['coverage_metrics']['distinct_states_count']:,}")
    li_data = comp_res["platforms"].get("linkedin", {})
    ind_data = comp_res["platforms"].get("indeed", {})
    op12_pass = (
        li_data.get("total_postings") == 123835
        and ind_data.get("total_postings") == 5715
        and li_data.get("remote_work_breakdown", {}).get("explicitly_remote") == 15236
        and ind_data.get("remote_work_breakdown", {}).get("unknown_unspecified") == 5715
    )
    print(f"    - Operation 12 Status: {'PASS' if op12_pass else 'FAIL'}")
    all_passed = all_passed and op12_pass
    operation_results["op12_platform_comparison"] = {
        "status": "PASS" if op12_pass else "FAIL",
        "linkedin_total": li_data.get("total_postings"),
        "indeed_total": ind_data.get("total_postings"),
        "linkedin_remote": li_data.get("remote_work_breakdown", {}).get("explicitly_remote"),
        "indeed_unknown_remote": ind_data.get("remote_work_breakdown", {}).get("unknown_unspecified"),
        "duration_seconds": round(t12, 4),
    }

    # -------------------------------------------------------------------------
    # API Input Validation & Guardrail Regression Tests
    # -------------------------------------------------------------------------
    print("\n>>> Testing API Input Validation & Query Guardrails...")
    val_pass = True
    executed_cases: List[Dict[str, Any]] = []

    def record_case(category: str, name: str, passed: bool, error_msg: Optional[str] = None) -> None:
        nonlocal val_pass
        if not passed:
            val_pass = False
        executed_cases.append({
            "category": category,
            "name": name,
            "passed": passed,
            "error": error_msg,
        })

    try:
        # 1. Invalid search_mode rejected
        try:
            service.search_jobs("Data Scientist", search_mode="fuzzy")
            print("    [FAIL] search_mode='fuzzy' was not rejected!")
            record_case("search_mode", "search_mode='fuzzy' rejected", False, "Did not raise ValueError")
        except ValueError:
            record_case("search_mode", "search_mode='fuzzy' rejected", True)
        except Exception as e:
            print(f"    [FAIL] search_mode='fuzzy' raised unexpected exception: {e}")
            record_case("search_mode", "search_mode='fuzzy' rejected", False, str(e))

        # 2. Limit=0 and negative limit/skip rejected across all 8 operational queries (24 explicit cases)
        op_limit_test_cases = [
            # 1. search_jobs
            ("search_jobs limit=0", lambda: service.search_jobs("Data Scientist", limit=0)),
            ("search_jobs limit=-1", lambda: service.search_jobs("Data Scientist", limit=-1)),
            ("search_jobs skip=-1", lambda: service.search_jobs("Data Scientist", skip=-1)),
            # 2. filter_by_location
            ("filter_by_location limit=0", lambda: service.filter_by_location(state="CA", limit=0)),
            ("filter_by_location limit=-1", lambda: service.filter_by_location(state="CA", limit=-1)),
            ("filter_by_location skip=-1", lambda: service.filter_by_location(state="CA", skip=-1)),
            # 3. filter_by_salary
            ("filter_by_salary limit=0", lambda: service.filter_by_salary(salary_bucket="100000-119999", limit=0)),
            ("filter_by_salary limit=-1", lambda: service.filter_by_salary(salary_bucket="100000-119999", limit=-1)),
            ("filter_by_salary skip=-1", lambda: service.filter_by_salary(salary_bucket="100000-119999", skip=-1)),
            # 4. filter_by_skills
            ("filter_by_skills limit=0", lambda: service.filter_by_skills(skills=["Python"], limit=0)),
            ("filter_by_skills limit=-1", lambda: service.filter_by_skills(skills=["Python"], limit=-1)),
            ("filter_by_skills skip=-1", lambda: service.filter_by_skills(skills=["Python"], skip=-1)),
            # 5. filter_by_company
            ("filter_by_company limit=0", lambda: service.filter_by_company(company_name="Express Scripts", limit=0)),
            ("filter_by_company limit=-1", lambda: service.filter_by_company(company_name="Express Scripts", limit=-1)),
            ("filter_by_company skip=-1", lambda: service.filter_by_company(company_name="Express Scripts", skip=-1)),
            # 6. filter_by_experience
            ("filter_by_experience limit=0", lambda: service.filter_by_experience(experience_level="Mid-Senior level", limit=0)),
            ("filter_by_experience limit=-1", lambda: service.filter_by_experience(experience_level="Mid-Senior level", limit=-1)),
            ("filter_by_experience skip=-1", lambda: service.filter_by_experience(experience_level="Mid-Senior level", skip=-1)),
            # 7. filter_by_source
            ("filter_by_source limit=0", lambda: service.filter_by_source(source="linkedin", limit=0)),
            ("filter_by_source limit=-1", lambda: service.filter_by_source(source="linkedin", limit=-1)),
            ("filter_by_source skip=-1", lambda: service.filter_by_source(source="linkedin", skip=-1)),
            # 8. search_and_filter
            ("search_and_filter limit=0", lambda: service.search_and_filter(role_category="Engineering", limit=0)),
            ("search_and_filter limit=-1", lambda: service.search_and_filter(role_category="Engineering", limit=-1)),
            ("search_and_filter skip=-1", lambda: service.search_and_filter(role_category="Engineering", skip=-1)),
        ]
        for case_name, func in op_limit_test_cases:
            try:
                func()
                print(f"    [FAIL] Operational query {case_name} did not raise ValueError!")
                record_case("operational_pagination", case_name, False, "Did not raise ValueError")
            except ValueError:
                record_case("operational_pagination", case_name, True)
            except Exception as e:
                print(f"    [FAIL] Operational query {case_name} raised unexpected exception: {e}")
                record_case("operational_pagination", case_name, False, str(e))

        # 3. Limit=0 and negative limit rejected across all four public aggregation functions that accept limit
        # Uses existing, populated role categories ("Engineering", "Data Science") to prevent empty sets from concealing errors
        agg_limit_test_cases = [
            ("get_top_skills limit=0", lambda: service.get_top_skills(role_category="Engineering", limit=0)),
            ("get_top_skills limit=-1", lambda: service.get_top_skills(role_category="Engineering", limit=-1)),
            ("get_skills_by_platform limit=0", lambda: service.get_skills_by_platform(role_category="Data Science", limit=0)),
            ("get_skills_by_platform limit=-1", lambda: service.get_skills_by_platform(role_category="Data Science", limit=-1)),
            ("get_top_companies limit=0", lambda: service.get_top_companies(limit=0)),
            ("get_top_companies limit=-1", lambda: service.get_top_companies(limit=-1)),
            ("get_top_locations limit=0", lambda: service.get_top_locations(limit=0)),
            ("get_top_locations limit=-1", lambda: service.get_top_locations(limit=-1)),
        ]
        for case_name, func in agg_limit_test_cases:
            try:
                func()
                print(f"    [FAIL] Aggregation {case_name} did not raise ValueError!")
                record_case("aggregation_limit", case_name, False, "Did not raise ValueError")
            except ValueError:
                record_case("aggregation_limit", case_name, True)
            except Exception as e:
                print(f"    [FAIL] Aggregation {case_name} raised unexpected exception: {e}")
                record_case("aggregation_limit", case_name, False, str(e))

        # 4. Invalid salary range (min > max) rejected
        try:
            service.filter_by_salary(min_annual=150000, max_annual=100000)
            print("    [FAIL] min_annual > max_annual was not rejected!")
            record_case("salary_range", "min_annual > max_annual rejected", False, "Did not raise ValueError")
        except ValueError:
            record_case("salary_range", "min_annual > max_annual rejected", True)
        except Exception as e:
            print(f"    [FAIL] filter_by_salary raised unexpected exception: {e}")
            record_case("salary_range", "min_annual > max_annual rejected", False, str(e))

        # 5. Remote-status validation: Arbitrary integers (e.g. 2, 1, 0) strictly rejected
        for bad_remote in (2, 1, 0, -1, "invalid_status", 3.14):
            try:
                service.filter_by_location(state="CA", is_remote=bad_remote)
                print(f"    [FAIL] is_remote={bad_remote!r} in filter_by_location was not rejected!")
                record_case("invalid_remote", f"filter_by_location is_remote={bad_remote!r} rejected", False, "Did not raise ValueError")
            except ValueError:
                record_case("invalid_remote", f"filter_by_location is_remote={bad_remote!r} rejected", True)
            except Exception as e:
                print(f"    [FAIL] filter_by_location with is_remote={bad_remote!r} raised unexpected exception: {e}")
                record_case("invalid_remote", f"filter_by_location is_remote={bad_remote!r} rejected", False, str(e))

            try:
                service.get_top_locations(is_remote=bad_remote)
                print(f"    [FAIL] is_remote={bad_remote!r} in get_top_locations was not rejected!")
                record_case("invalid_remote", f"get_top_locations is_remote={bad_remote!r} rejected", False, "Did not raise ValueError")
            except ValueError:
                record_case("invalid_remote", f"get_top_locations is_remote={bad_remote!r} rejected", True)
            except Exception as e:
                print(f"    [FAIL] get_top_locations with is_remote={bad_remote!r} raised unexpected exception: {e}")
                record_case("invalid_remote", f"get_top_locations is_remote={bad_remote!r} rejected", False, str(e))

        # 6. Remote-status validation: Valid tri-state semantics and documented string parsing
        try:
            _, ca_rem_true_cnt = service.filter_by_location(state="CA", is_remote=True)
            _, ca_rem_str_cnt = service.filter_by_location(state="CA", is_remote="remote")
            _, ca_rem_false_cnt = service.filter_by_location(state="CA", is_remote=False)
            _, ny_unknown_cnt = service.filter_by_location(state="NY", is_remote=None)
            _, ny_unknown_str = service.filter_by_location(state="NY", is_remote="unknown")
            _, ny_any_cnt = service.filter_by_location(state="NY", is_remote="any")

            p_true = (ca_rem_true_cnt == 975)
            p_str = (ca_rem_str_cnt == 975)
            p_false = (ca_rem_false_cnt == 0)
            p_none = (ny_unknown_cnt == 7693)
            p_unk = (ny_unknown_str == 7693)
            p_any = (ny_any_cnt == 8155 and ny_any_cnt > ny_unknown_cnt)

            record_case("valid_remote_semantics", "filter_by_location is_remote=True yields 975 in CA", p_true)
            record_case("valid_remote_semantics", "filter_by_location is_remote='remote' yields 975 in CA", p_str)
            record_case("valid_remote_semantics", "filter_by_location is_remote=False yields 0 in CA", p_false)
            record_case("valid_remote_semantics", "filter_by_location is_remote=None yields 7693 in NY", p_none)
            record_case("valid_remote_semantics", "filter_by_location is_remote='unknown' yields 7693 in NY", p_unk)
            record_case("valid_remote_semantics", "filter_by_location is_remote='any' yields 8155 in NY", p_any)

            if not p_true or not p_str:
                print(f"    [FAIL] is_remote=True/remote expected 975, got true={ca_rem_true_cnt}, str={ca_rem_str_cnt}")
            if not p_false:
                print(f"    [FAIL] is_remote=False expected 0, got {ca_rem_false_cnt}")
            if not p_none or not p_unk:
                print(f"    [FAIL] is_remote=None/'unknown' expected 7693, got none={ny_unknown_cnt}, str={ny_unknown_str}")
            if not p_any:
                print(f"    [FAIL] is_remote='any' expected 8155, got {ny_any_cnt} (must be strictly > unknown {ny_unknown_cnt})")
        except Exception as e:
            print(f"    [FAIL] Exception during valid remote semantics tests: {e}")
            record_case("valid_remote_semantics", "valid remote semantics execution", False, str(e))

    except Exception as e:
        print(f"    [FAIL] Unexpected exception during input validation: {e}")
        val_pass = False

    total_executed = len(executed_cases)
    total_passed = sum(1 for c in executed_cases if c["passed"])
    cat_summary = {}
    for c in executed_cases:
        cat = c["category"]
        if cat not in cat_summary:
            cat_summary[cat] = {"executed": 0, "passed": 0, "failed": 0}
        cat_summary[cat]["executed"] += 1
        if c["passed"]:
            cat_summary[cat]["passed"] += 1
        else:
            cat_summary[cat]["failed"] += 1

    op_exec = cat_summary.get("operational_pagination", {}).get("executed", 0)
    op_pass = cat_summary.get("operational_pagination", {}).get("passed", 0)
    agg_exec = cat_summary.get("aggregation_limit", {}).get("executed", 0)
    agg_pass = cat_summary.get("aggregation_limit", {}).get("passed", 0)

    print(f"    - Operational pagination tests: {op_pass}/{op_exec} passed (8 functions x 3 conditions [limit=0, limit<0, skip<0])")
    print(f"    - Aggregation limit tests:      {agg_pass}/{agg_exec} passed (4 functions x 2 conditions [limit=0, limit<0])")
    print(f"    - Total guardrail cases tested: {total_passed}/{total_executed} passed")
    guardrail_pass = val_pass and total_executed > 0 and total_passed == total_executed
    print(f"    - Input Validation Guardrails Status: {'PASS' if guardrail_pass else 'FAIL'}")

    all_passed = all_passed and guardrail_pass
    operation_results["input_validation_guardrails"] = {
        "status": "PASS" if guardrail_pass else "FAIL",
        "total_cases_executed": total_executed,
        "total_cases_passed": total_passed,
        "operational_pagination_cases_executed": op_exec,
        "operational_pagination_cases_passed": op_pass,
        "aggregation_limit_cases_executed": agg_exec,
        "aggregation_limit_cases_passed": agg_pass,
        "categories": cat_summary,
        "executed_case_names": [c["name"] for c in executed_cases],
    }

    # -------------------------------------------------------------------------
    # Comprehensive Query Plan Audit via explain("executionStats") (20 Cases)
    # -------------------------------------------------------------------------
    print("\n>>> Verifying Query Plans via explain('executionStats') on Operational & Aggregation Queries...")
    from scripts.audit_phase_5_queries import run_query_plan_audit
    query_audit_res = run_query_plan_audit(close_conn_at_end=False)
    
    op_cases = len(query_audit_res["operational_queries"])
    agg_cases = len(query_audit_res["aggregation_pipelines"])
    total_cases = op_cases + agg_cases
    query_cases_pass = (op_cases == 14 and agg_cases == 6 and total_cases == 20)
    query_plan_audit_pass = query_audit_res["overall_audit_passed"] and query_cases_pass

    print(f"    - Operational Query Cases Audited:    {op_cases} (Expected: 14)")
    print(f"    - Aggregation Pipeline Cases Audited: {agg_cases} (Expected: 6)")
    print(f"    - Total Query-Plan Cases Audited:     {total_cases} (Expected: 20)")
    print(f"    - 20-Case Plan Audit Status:          {'PASS' if query_plan_audit_pass else 'FAIL'}")
    all_passed = all_passed and query_plan_audit_pass

    # -------------------------------------------------------------------------
    # Read-Only Safety & Database Integrity Verification (Counts & Indexes)
    # -------------------------------------------------------------------------
    print("\n>>> Verifying Database Integrity & Read-Only Safety Invariants...")
    final_jobs = db["jobs"].count_documents({})
    final_comp = db["companies"].count_documents({})
    final_jobs_indexes = db["jobs"].index_information()
    final_comp_indexes = db["companies"].index_information()

    counts_pass = (initial_jobs == 129550 and final_jobs == 129550 and initial_comp == 24472 and final_comp == 24472)
    indexes_pass = (initial_jobs_indexes == final_jobs_indexes and initial_comp_indexes == final_comp_indexes)
    integrity_pass = counts_pass and indexes_pass

    print(f"    - Post-Execution jobs count:       {final_jobs:,} (Delta: {final_jobs - initial_jobs})")
    print(f"    - Post-Execution companies count:  {final_comp:,} (Delta: {final_comp - initial_comp})")
    print(f"    - jobs indexes invariant:          {'PASS' if initial_jobs_indexes == final_jobs_indexes else 'FAIL'}")
    print(f"    - companies indexes invariant:     {'PASS' if initial_comp_indexes == final_comp_indexes else 'FAIL'}")
    print(f"    - Integrity Verification Status:    {'PASS' if integrity_pass else 'FAIL'}")
    all_passed = all_passed and integrity_pass

    # Save comprehensive verification summary artifact
    summary_path = os.path.join("data", "processed", "phase_5_verification_summary.json")
    summary_data = {
        "database": db_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "all_passed": all_passed,
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
        "operations": operation_results,
        "salary_outlier_audit_summary": {
            "verified": outlier_audit_pass,
            "artifact_path": "data/processed/phase_5_salary_outlier_audit.json",
            "total_records": len(art_recs),
            "category_counts": art_counts,
        },
        "query_plan_audit_summary": {
            "overall_passed": query_plan_audit_pass,
            "operational_queries_count": op_cases,
            "aggregation_pipelines_count": agg_cases,
            "total_cases_audited": total_cases,
            "audit_artifact_path": "data/processed/phase_5_query_plan_audit.json",
        },
    }
    with open(summary_path, "w", encoding="utf-8") as f_sum:
        json.dump(summary_data, f_sum, indent=2)
    print(f"\n    Verification summary saved to: {summary_path}")

    print("\n" + "=" * 80)
    print(f" Phase 5 Overall Result: {'ALL CHECKS PASSED' if all_passed else 'VERIFICATION FAILED'}")
    print("=" * 80)

    close_connection()
    return all_passed


if __name__ == "__main__":
    success = run_phase_5_verification()
    sys.exit(0 if success else 1)
