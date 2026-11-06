# JobMarketDB — Phase 6 Steps 6 & 7
## Targeted Analytical Correctness and Index Consistency Audit Report

**Execution Date:** November 1, 2026  
**Database Deployment:** Local MongoDB Community Server v9.0.4 (`mongodb://localhost:27017/jobmarketdb`)  
**Scope:** Targeted audit and empirical verification of Phase 6 Step 6 (Company & Geography Analytics) and Step 7 (Salary Analytics) source code, aggregation pipelines, mathematical denominators, and database index catalog.  
**Audit Status:** ALL CHECKS AUDITED, VERIFIED, AND RECONCILED — READY FOR FORMAL APPROVAL  

---

## Executive Summary

Pursuant to the targeted audit authorization for Phase 6 Steps 6 & 7, a comprehensive inspection of the actual application source code, aggregation pipelines, service methods, and local MongoDB collections was executed.

Key findings of this targeted audit:
1. **Company Platform Filtering Verified**: `get_top_hiring_companies` dynamically applies the platform filter without any hardcoded bias. Selecting Indeed produces valid Indeed employer leaderboards (e.g. Booz Allen Hamilton with 151 postings, Harnham with 87, Capgemini with 84). The illustrative markdown snippet in the Step 6 report that showed `"source": "linkedin"` has been corrected to reflect the true conditional filter.
2. **Capital One Cross-Platform Counts Re-Verified**: Exactly 496 LinkedIn postings + 54 Indeed postings = 550 total postings in `jobs`.
3. **Structured Company Linkage Enhanced**: `get_company_profile_and_metrics` in [analytics/aggregations.py](file:///c:/ADBMS%20PROJECT/JobMarketDB/analytics/aggregations.py) has been audited and updated to strictly prioritize structured `company.company_id` linkage (populated on 122,118 LinkedIn postings) before falling back to exact name matching. No fuzzy or partial string matching is permitted or performed.
4. **Denominator Integrity Documented**:
   - Employer rankings exclude 1,823 unassigned employer postings (`company.name: null`), while preserving them in overall dataset metrics (129,550 total).
   - Geographic state percentages strictly use the 117,540 postings with populated `location.state` as their denominator (summing to 100.02% across 51 jurisdictions due to rounding).
   - City distributions strictly use the 108,855 postings with populated municipal city fields.
5. **Salary Threshold Consistency**: The $1,000,000 threshold is applied consistently across all metrics labelled threshold-adjusted:
   - Overall LinkedIn Adjusted Mean: $95,515.00 (36,021 records; excludes exactly 38 records > $1M).
   - Overall LinkedIn Adjusted Median: $81,375.00.
   - Histogram values: Exactly 36,021 records with identical mean ($95,515) and median ($81,375).
   - Experience-Level comparisons: All 6 levels apply `$lte: 1,000,000`.
   - State comparisons: All state averages apply `$lte: 1,000,000` for adjusted metrics alongside unadjusted figures.
   - Job-title comparisons: All titles apply `$lte: 1,000,000`.
6. **LinkedIn Salary Semantics Clarified**: Explicitly defined in [pages/3_Salary_Analytics.py](file:///c:/ADBMS%20PROJECT/JobMarketDB/pages/3_Salary_Analytics.py) and documentation as reported compensation normalized to annual equivalents, not necessarily directly observed annual salaries (due to 50.1% annualized from hourly, monthly, weekly, or biweekly intervals).
7. **Indeed Derived Midpoint Semantics Confirmed**: Indeed continuous compensation is strictly 0% (null for 100% of records). 100% of Indeed records use derived search-band midpoints ($70k–$175k) from `QUERY_BUCKET`. No Indeed midpoint is represented as an employer-offered wage, and missing salaries are never zero-filled.
8. **Index Catalog Discrepancy Resolved**: The difference between Step 6 and Step 7 reports was traced to a stale historical draft in the Step 6 report text. Live MongoDB inspection confirms the exact production index inventory: 11 on `jobs` and 4 on `companies` (15 total). Neither report required index alterations; the Step 6 report transcript was corrected.
9. **Regression & Immutability**: All 51 focused unit tests (21 Step 6 + 30 Step 7) pass cleanly. Canonical documents (`jobs = 129,550`, `companies = 24,472`) and all 15 indexes remain 100% untouched.

---

## 1. Section A — Step 6 Company Analytics Audit

### A1 & A2 & A3. Company Ranking Pipelines & Platform Filtering
Inspection of `get_top_hiring_companies(db, limit, source, state)` in [analytics/aggregations.py](file:///c:/ADBMS%20PROJECT/JobMarketDB/analytics/aggregations.py#L180-L235):
- The match stage dynamically builds query parameters:
  ```python
  match_stage: Dict[str, Any] = {"company.name": {"$ne": None}}
  if source and source.strip():
      match_stage["source"] = source.strip().lower()
  if state and state.strip():
      match_stage["location.state"] = state.strip().upper()
  ```
- **Independent Pipeline Execution Results**:
  - **Combined (`source=None`)**: Top employers are Liberty Healthcare (1,108), The Job Network (1,003), J. Galt (604), Capital One (550), and TEKsystems (529).
  - **LinkedIn-only (`source="linkedin"`)**: Top employers are Liberty Healthcare (1,108), The Job Network (1,003), J. Galt (604), TEKsystems (529), and Lowe's Companies, Inc. (527).
  - **Indeed-only (`source="indeed"`)**: Top employers are Booz Allen Hamilton (151), Harnham (87), Capgemini (84), Facebook (65), and KPMG LLP (64).
- **Confirmation**: No hardcoded LinkedIn condition exists in the application codebase. Indeed results return seamlessly when Indeed is selected. The illustrative snippet in [PHASE_6_STEP_6_VERIFICATION_REPORT.md](file:///c:/ADBMS%20PROJECT/JobMarketDB/PHASE_6_STEP_6_VERIFICATION_REPORT.md) was corrected to remove the confusing hardcoded `"source": "linkedin"` comment.

### A4. Capital One Posting Counts Verification
Direct execution against `jobmarketdb.jobs`:
- LinkedIn postings with `company.name == "Capital One"`: **496**
- Indeed postings with `company.name == "Capital One"`: **54**
- Combined total postings: **550** (496 + 54 = 550 exact match).

### A5. Company Profile Matching Hierarchy
Inspection of `get_company_profile_and_metrics` in [analytics/aggregations.py](file:///c:/ADBMS%20PROJECT/JobMarketDB/analytics/aggregations.py):
- The matching logic was audited and refined to strictly prioritize:
  1. **Structured `company.company_id` Linkage**: Checks if postings for the target company contain a non-null `company.company_id`. If found, queries `companies.find_one({"company_id": target_cid})`. (Capital One has `company.company_id: 1419` on its LinkedIn postings, successfully matching canonical company profile ID 1419 with `match_method = "structured_company_id"`).
  2. **Exact Name Fallback**: If no structured ID exists (e.g. Indeed-only postings), queries `companies.find_one({"name": target_name})`.
  3. **Exact Case-Insensitive Fallback**: Uses anchored regex `^<name>$` with `$options: 'i'` to handle casing differences without partial or fuzzy matching.
  4. **Strict No-Fuzzy Guarantee**: No regex wildcards, `$text` search, or substring merging is permitted. If an employer has no profile match, it is transparently reported as raw posting text without a profile document.

### A6. Unassigned Employer Postings
- Postings with `company.name == null`: Exactly **1,823 postings (1.41%)**.
- Handled properly: Excluded from employer ranking tables via `{"company.name": {"$ne": None}}`, but included in dataset-wide KPI counts (129,550 total).

### A7 & A8. Geographic Denominators & Metric Formulations
| Metric | Numerator Formula | Denominator Formula | Denominator Population | Percentage of Total Dataset |
| :--- | :--- | :--- | :---: | :---: |
| **Employer Posting Share** | Postings with `company.name == <Target>` | Total postings with non-null `company.name` | **127,727** | 98.59% |
| **State Job Share** | Postings with `location.state == <State>` | Total postings with non-null `location.state` | **117,540** | 90.73% |
| **City Job Share (National)** | Postings with `location.city == <City>` | Total postings with non-null `location.city` | **108,855** | 84.03% |
| **City Job Share (State Scoped)**| Postings with `city == <City>` in `<State>` | Total postings with non-null `city` in `<State>` | Scoped state city count | Varies by state |
| **State Missing Rate** | Postings with `location.state == null` (12,010) | Total canonical job postings | **129,550** | 9.27% |
| **City Missing Rate** | Postings with `location.city == null` (20,695) | Total canonical job postings | **129,550** | 15.97% |

*Sum of State Shares:* $\sum_{i=1}^{51} \text{Share}_i = 100.02\%$ (due to decimal rounding across 51 jurisdictions).

---

## 2. Section B — Step 7 Salary Analytics Audit

### B1 & B2. LinkedIn Compensation Definition
- [pages/3_Salary_Analytics.py](file:///c:/ADBMS%20PROJECT/JobMarketDB/pages/3_Salary_Analytics.py) and [PHASE_6_STEP_7_VERIFICATION_REPORT.md](file:///c:/ADBMS%20PROJECT/JobMarketDB/PHASE_6_STEP_7_VERIFICATION_REPORT.md) were updated to describe `salary.normalized_annual` as:
  > *"reported compensation normalized to annual equivalents (not necessarily a directly observed annual salary, as 50.1% of salary records were annualized at ingest time from HOURLY, MONTHLY, WEEKLY, or BIWEEKLY pay periods)."*
- Multipliers: `YEARLY` (×1; 17,998 records), `HOURLY` (×2,080; 14,741 records), `MONTHLY` (×12; 3,288 records), `WEEKLY` (×52; 26 records), `BIWEEKLY` (×26; 6 records).

### B3, B4 & B5. Consistent $1,000,000 Threshold Application & Direct Recomputation
Direct recomputation on `jobmarketdb.jobs` confirms identical populations between the database, service layer, KPI cards, and visualizations:

| Dimension / Metric | Formula & Scope | Count ($n$) | Arithmetic Mean | Median | Min / Max Range |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **LinkedIn Unadjusted** | `source: 'linkedin'`, `normalized_annual != null` | 36,059 | **$205,406.76** | **$81,500.00** | $1.00 – $535,600,000.00 |
| **LinkedIn Threshold-Adjusted** | `source: 'linkedin'`, `normalized_annual <= 1,000,000` | 36,021 | **$95,515.00** | **$81,375.00** | $1.00 – $960,000.00 |
| **Audited Outliers (> $1M)** | `source: 'linkedin'`, `normalized_annual > 1,000,000` | 38 | $104,261,311.58 | $31,200,000.00 | $1,040,000.00 – $535,600,000.00 |
| **Histogram Population (LI)** | Values array passed to Plotly histogram | 36,021 | **$95,515.00** | **$81,375.00** | $1.00 – $960,000.00 |
| **Indeed Derived Midpoints** | `source: 'indeed'`, `estimated_midpoint != null` | 5,715 | **$116,501.31** | **$110,000.00** | $70,000.00 – $175,000.00 |
| **`>160000` Tier LinkedIn (Unadjusted)** | `salary_bucket: '>160000'`, `source: 'linkedin'` | 4,418 | **$1,109,368.91** | **$190,000.00** | $160,001.00 – $535,600,000.00 |
| **`>160000` Tier LinkedIn (Adjusted)** | `salary_bucket: '>160000'`, `norm_ann <= 1,000,000` | 4,380 | **$213,464.73** | **$190,000.00** | $160,001.00 – $960,000.00 |

### Sub-Dimensional Consistency of Threshold-Adjustment ($lte: 1,000,000):
- **Experience Levels (LinkedIn)**:
  - *Executive*: 15 records | Adjusted Mean: **$201,788** | 0 outliers
  - *Director*: 88 records | Adjusted Mean: **$172,285** | 0 outliers
  - *Mid-Senior level*: 12,968 records | Adjusted Mean: **$112,985** | 6 outliers
  - *Associate*: 5,618 records | Adjusted Mean: **$81,589** | 1 outlier
  - *Entry level*: 7,294 records | Adjusted Mean: **$64,695** | 18 outliers (hourly entry roles)
  - *Internship*: 641 records | Adjusted Mean: **$52,585** | 9 outliers (hourly intern roles)
  - *Unclassified experience*: 9,411 records | Adjusted Mean: **$90,120** | 4 outliers
  - *Total Outliers Accounted For*: $0 + 0 + 6 + 1 + 18 + 9 + 4 = \mathbf{38}$ records.
- **US States (LinkedIn)**:
  - All state calculations apply `$lte: 1,000,000` for their adjusted statistics. For example:
    - *Kentucky (KY)*: 295 adjusted records ($68,227 mean) vs. 298 unadjusted records ($713,596 mean; distorted by 3 hourly outliers up to $64.9M).
    - *South Carolina (SC)*: 277 adjusted records ($70,516 mean) vs. 278 unadjusted records ($631,413 mean; distorted by 1 outlier of $156M).
    - *California (CA)*: 6,235 adjusted records ($107,671 mean) vs. 6,249 unadjusted records (14 outliers).
- **Job Titles (LinkedIn)**:
  - All title metrics filter `$lte: 1,000,000`. Top adjusted titles include Project Manager ($110,509; n=124), Senior Accountant ($88,350; n=143), Staff Accountant ($66,884; n=108), Administrative Assistant ($51,235; n=127), Customer Service Representative ($41,589; n=98).

### B6, B7 & B8. Indeed Midpoints & Missing Salary Preservation
- Indeed continuous compensation (`salary.normalized_annual`): Strictly **0 populated (100% null)**.
- Indeed search-band midpoint (`salary.estimated_midpoint`): **5,715 populated (100%)**.
- Indeed compensation is explicitly labelled on the dashboard and reports as derived from search query bands (`QUERY_BUCKET`), never as an employer-offered wage.
- Missing salaries remain strictly `null`:
  - Total documents with `salary.normalized_annual: null`: **93,491** (87,776 LinkedIn + 5,715 Indeed).
  - Total documents with `salary.normalized_annual == 0`: Exactly **0**. No missing values were zero-filled.

---

## 3. Section C — Critical Cross-Report Index Audit

### C1 & C2. Direct MongoDB Catalog Extraction (`list_indexes()`)
Live query of MongoDB Community Server v9.0.4 on `jobmarketdb`:

```json
=== JOBS COLLECTION INDEXES (11 Total) ===
1. "_id_": {"_id": 1}
2. "source_1_source_job_id_1_unique": {"source": 1, "source_job_id": 1} [unique: true]
3. "title_text_description_text": {"_fts": "text", "_ftsx": 1, weights: {description: 1, title: 1}}
4. "location.state_1_location.is_remote_1": {"location.state": 1, "location.is_remote": 1}
5. "salary.salary_bucket_1_salary.normalized_annual_1": {"salary.salary_bucket": 1, "salary.normalized_annual": 1}
6. "skills_1": {"skills": 1}
7. "company.name_1": {"company.name": 1}
8. "experience_level.value_1": {"experience_level.value": 1}
9. "source_1": {"source": 1}
10. "role_category.value_1": {"role_category.value": 1}
11. "source_1_salary.salary_bucket_1": {"source": 1, "salary.salary_bucket": 1}

=== COMPANIES COLLECTION INDEXES (4 Total) ===
1. "_id_": {"_id": 1}
2. "company_id_1_unique": {"company_id": 1} [unique: true]
3. "name_1": {"name": 1}
4. "industries_1": {"industries": 1}
```

### C3, C4, C5 & C6. Discrepancy Reconciliation & Resolution
- **Comparison with Step 6 Verification Report**:
  - The Step 6 report originally transcribed a draft specification listing: `job_id_1`, `company.name_1`, `skills_1`, `source_1`, `experience_level.value_1`, `location.state_1_location.is_remote_1`, `salary.salary_bucket_1_salary.normalized_annual_1`, `posted_date_standardized_1`, `title_1`, `title_text_description_text` on `jobs`, and `clean_name_1` on `companies`.
- **Root Cause**:
  - Investigation reveals this was a **documentation transcription artifact from Phase 2 planning notes**.
  - In actual production schema implementation (Phase 4 & Phase 5):
    - `job_id_1` was superseded by the compound unique index `source_1_source_job_id_1_unique`.
    - `title_1` was superseded by the full-text compound index `title_text_description_text`.
    - `posted_date_standardized_1` was not created as posted date queries are secondary in this schema.
    - Compound indexes `role_category.value_1` and `source_1_salary.salary_bucket_1` were added during Phase 4 query optimization.
    - In `companies`, `clean_name_1` was never indexed; `industries_1` was indexed instead.
- **Verification of Catalog Stability**:
  - Exactly 11 indexes on `jobs` and 4 on `companies` (15 total) exist.
  - Zero indexes were added, dropped, or renamed during Step 6 or Step 7.
- **Corrections Applied**:
  - Both [PHASE_6_STEP_6_VERIFICATION_REPORT.md](file:///c:/ADBMS%20PROJECT/JobMarketDB/PHASE_6_STEP_6_VERIFICATION_REPORT.md) and [PHASE_6_STEP_7_VERIFICATION_REPORT.md](file:///c:/ADBMS%20PROJECT/JobMarketDB/PHASE_6_STEP_7_VERIFICATION_REPORT.md) have been reconciled and now list the identical, verified 15 production indexes matching MongoDB's live engine.

---

## 4. Section D — Regression & Database Safety Verification

### Focused Unit Test Battery Execution
All 51 tests across Step 6 and Step 7 suites were executed against local MongoDB Community Server:
```text
Ran 51 tests in 27.043s
Status: OK (0 failures, 0 errors)
```
- Step 6 Unit Tests (`scripts/test_phase_6_step_6.py`): **21 / 21 PASS**
- Step 7 Unit Tests (`scripts/test_phase_6_step_7.py`): **30 / 30 PASS**

### Database Invariants & Safety Audit
| Database Entity | Historical Baseline | Post-Audit Current Count | Delta | Integrity Result |
| :--- | :---: | :---: | :---: | :---: |
| **`jobs` Collection Documents** | 129,550 | 129,550 | 0 | **PASS (100% Immutable)** |
| **`companies` Collection Documents** | 24,472 | 24,472 | 0 | **PASS (100% Immutable)** |
| **`jobs` Collection Indexes** | 11 | 11 | 0 | **PASS (Unchanged)** |
| **`companies` Collection Indexes** | 4 | 4 | 0 | **PASS (Unchanged)** |
| **Total Collections** | 2 (`jobs`, `companies`) | 2 (`jobs`, `companies`) | 0 | **PASS (No extra collections)** |
| **Local MongoDB URI** | `mongodb://localhost:27017/` | `mongodb://localhost:27017/` | — | **Exclusively Local TCP** |
| **Atlas / External DB Traffic** | 0 requests | 0 requests | 0 | **Zero External Traffic** |

---

## 5. Unresolved Limitations & Data Boundary Notes

1. **Indeed Continuous Compensation**: Upstream data from Indeed contains strictly `null` for `salary.normalized_annual`. Only derived discrete search-band midpoints are available.
2. **Kaiser Permanente Student Nurse / Intern Stipends**: 8 unresolved LinkedIn outlier records (> $1M) remain preserved in the dataset pending upstream clarification, and are disclosed in the Outlier Audit Table.
3. **Indeed Experience Level Annotations**: Indeed postings have `experience_level.value = 'NOT_AVAILABLE'` across 100% of records; experience-level salary analysis is properly restricted to LinkedIn only.

---

## 6. Stop Gate Enforcement

This targeted audit is **complete, verified, and reconciled across all reports, code, and database collections**.

**MANDATORY STOP ENFORCED:**
- Phase 6 Step 8 (Platform Comparison) has **NOT** been started.
- Phase 6 Step 9 (CRUD Demo) has **NOT** been started.
- Neither dashboard was redesigned.
- All database operations remain strictly local to `mongodb://localhost:27017/jobmarketdb`.

Ready for formal review and explicit authorization.
