# Phase 3 Implementation Report: ETL & Data Transformation (Corrected & Finalized)

## 1. Phase 3 Overview & Scope Boundaries

JobMarketDB Phase 3 implements an autonomous, production-grade Extract, Transform, Load (ETL) pipeline that reads raw LinkedIn and Indeed datasets from local disk, enforces strict data provenance tiers, applies Phase 2 schema validation, and generates MongoDB-ready JSONL output files.

### Scope Boundaries Strictly Preserved:
- **No MongoDB Connection:** Neither PyMongo client nor database connections were initialized.
- **No Database Operations:** No MongoDB databases, collections, or indexes were created.
- **No Streamlit UI:** No frontend application code, dashboards, or UI components were created or modified.
- **Raw Datasets Untouched:** All source archives and files (`datasets/archive.zip`, `datasets/indeed_job_dataset.csv.zip`, and uncompressed folders) remain in their original raw state.
- **Phase 2 Schema Locked:** Document structure, field names, and collection definitions established in Phase 2 remain completely unchanged.

---

## 2. ETL Architecture & Module Structure

The ETL pipeline is implemented as a modular package within [ingestion/](file:///C:/ADBMS%20PROJECT/JobMarketDB/ingestion) and [scripts/](file:///C:/ADBMS%20PROJECT/JobMarketDB/scripts):

```text
JobMarketDB/
│
├── ingestion/
│   ├── __init__.py          # Ingestion package exports
│   ├── transformers.py      # US state normalization, tri-state remote, job location parsing, cleaning, bucketing
│   ├── validators.py        # Schema validation (validate_job_document, validate_company_document)
│   ├── linkedin.py          # Relational lookups, streaming chunk extractor, and posting/company transformer
│   └── indeed.py            # Indeed URL key parsing, tool indicators, authentic skill preservation, deduplication
│
├── scripts/
│   ├── __init__.py
│   └── run_etl.py           # Unified execution script for full dataset runs and metric generation
│
└── data/
    └── processed/           # (Excluded by .gitignore)
        ├── jobs_transformed.jsonl        # 129,550 validated MongoDB job documents (647.31 MB)
        ├── companies_transformed.jsonl   # 24,472 validated MongoDB company master profiles (35.24 MB)
        └── etl_summary.json              # Full audit metrics and validation status (1.41 KB)
```

---

## 3. Data Integrity Corrections Implemented

Following the review of the initial Phase 3 implementation, five critical data-integrity corrections were applied to the pipeline:

### 3.1 Tri-State LinkedIn Remote Work Representation
- **Problem:** Missing `remote_allowed` values were previously converted to `false` via binary comparison (`True if remote_allowed == 1.0 else False`).
- **Correction:** Implemented `parse_remote_status()` enforcing strict tri-state logic:
  - `remote_allowed == 1 / 1.0` → `true` (explicitly confirmed remote)
  - `remote_allowed == 0 / 0.0` → `false` (explicitly confirmed on-site)
  - `NaN / null / missing` → `null` (unknown / unstated)
- **Result:** In the transformed LinkedIn output, 15,236 postings are confirmed `is_remote: true`, 0 postings are `is_remote: false`, and 108,599 postings with unstated remote status are strictly preserved as `is_remote: null`. Indeed postings also consistently record `is_remote: null`.

### 3.2 Decoupling Job Location from Company Headquarters
- **Problem:** Company headquarters city, state, and zip code were previously passed as fallback values for job postings when job-level location details were partial.
- **Correction:** Completely removed company headquarters fallbacks from `parse_job_location()`. A job posting's location is derived exclusively from its own source fields (`location` and `zip_code`).
  - If a job-level city, state, or zip code is missing or unresolvable, the corresponding fields are set strictly to `null`.
  - Corporate headquarters location remains preserved exclusively within the separate `companies` collection (`headquarters` subdocument).
- **Test Case Verified:** Job postings such as The National Exemplar (`location = "Cincinnati, OH"`) now consistently parse as `city = "Cincinnati", state = "OH"`, completely eliminating the prior issue where the company's HQ municipality (`Mariemont`) overwrote the job's location.

### 3.3 Explicit US State Normalization
- **Problem:** Inconsistent state representations (full names vs. postal abbreviations) were appearing in `location.state`.
- **Correction:** Implemented `normalize_us_state()` with an exhaustive mapping covering all 50 US states, DC, and territories:
  - Full state names (e.g., `"Ohio"` → `"OH"`, `"New Jersey"` → `"NJ"`, `"California"` → `"CA"`, `"Texas"` → `"TX"`) are mapped to standard 2-letter uppercase postal abbreviations.
  - Already-valid 2-letter postal codes (e.g., `"OH"`, `"NJ"`, `"CA"`) are validated and preserved.
  - Safe trimming and case-insensitive handling are applied.
  - If a state cannot be confidently normalized (e.g., country strings like `"United States"`, international locations, or unstated), `state = null`.
- **Result:** Across all 129,550 transformed job documents, 117,540 contain validated 2-letter postal codes and 12,010 contain `null`. Zero full state names or invalid state strings remain in `location.state`.

### 3.4 Preservation of Authentic Source Job Identifiers
- **Problem:** Duplicate Indeed job keys previously had their DataFrame row index appended (e.g., transforming `6a105f495c36afe3` into `6a105f495c36afe3_472`).
- **Correction:** Removed all identifier modification logic. The authentic source identifier is preserved exactly as extracted from the source URL `jk` parameter.
- **Duplicate Handling Rule:**
  - If a source ID appears multiple times, the first valid occurrence is retained.
  - Subsequent duplicate occurrences are rejected/skipped.
  - Each duplicate is tracked and recorded in the audit metrics under `duplicate_source_ids`.

### 3.5 Elimination of Leaked NaN/NaT Values
- **Problem:** Pandas float NaN values could convert to string `"nan"` under certain text cleaning paths.
- **Correction:** `clean_text()` explicitly filters float NaN conditions (`text != text`) and rejects literal strings matching `"nan"`, `"none"`, and `"null"`. All missing values serialize cleanly as JSON `null`.
- **Result:** Recursive scan across all 129,550 jobs and 24,472 companies verified 0 NaN, 0 Inf, and 0 `"nan"` string leaks.

### 3.6 Role Category Provenance by Dataset
The provenance of `role_category` is explicitly distinct by source dataset:
- **LinkedIn: DERIVED / INFERRED**
  - Derived from the job `title` using role classification rules (e.g., title containing "Data Analyst" -> `role_category.value: "Data Analyst"`, `role_category.status: "DERIVED / INFERRED"`).
- **Indeed: NORMALIZED**
  - Normalized from the source `Job_Type` field (`data_scientist` -> `role_category.value: "Data Scientist"`, `role_category.status: "NORMALIZED"`).

The provenance is not identical between sources: Indeed normalizes an authentic source discipline field, whereas LinkedIn infers the role category heuristically from title text.

---

## 4. Audit of LinkedIn Company Profiles & Orphan ID Resolution

An explicit reconciliation audit was conducted between `postings.csv` and `companies.csv` to resolve the relationship between referenced company IDs and extracted company profiles.

### 4.1 Audit Findings for Missing Company ID `23729571`
1. **Identified Missing Company ID:** `23729571`
2. **Appears in `postings.csv`?** **Yes**, exactly 1 posting references it (`job_id: 3708903045`, title: `"Associate Attorney"`). The posting provides `company_name = nan`.
3. **Appears in `companies.csv`?** **No**, `company_id = 23729571` is completely absent from `companies.csv` (0 records).
4. **Appears in supporting company relational tables?** **No**, 0 matches exist in `companies/company_industries.csv`, `companies/company_specialities.csv`, and `companies/employee_counts.csv`.
5. **Can a company profile legitimately be created?** **No.** There is zero authoritative source metadata (no name, no size, no description, no address, no industry). Under Phase 2 rules, fabricating a synthetic company document is strictly prohibited.
6. **Resolution:** 
   - The job posting (`job_id: 3708903045`) is retained in `jobs_transformed.jsonl`.
   - Its authentic `company.company_id: 23729571` is preserved in the embedded snapshot, with `company.name: null`.
   - The master company profile remains absent from `companies_transformed.jsonl`.
   - The orphan relationship is recorded in `etl_summary.json` as `missing_orphan_company_ids: 1`.

### 4.2 Discrepancy Reconciliation for the 24,472 Extracted Profiles
A detailed analysis explains the exact numbers across the pipeline:
- **`postings.csv` distinct referenced company IDs:** `24,474`
- **`companies.csv` source rows:** `24,473`
- **Missing in `companies.csv`:** Company ID `23729571` (referenced by 1 posting, but absent from `companies.csv`).
- **Unnamed Company Row in `companies.csv`:** Company ID `6423583` exists in `companies.csv` (row 14,435), but has `name = nan` (referenced by job `3904959827`, which also has `company_name = nan`). Under Phase 2 schema validation (`validate_company_document`), a company document requires a non-empty name string. An unnamed company cannot form a valid profile without fabrication.
- **Net Valid Master Company Documents Extracted:** $24,473 - 1 = 24,472$.

`etl_summary.json` explicitly distinguishes these counts:
```json
"referenced_company_ids": 24474,
"extracted_company_profiles": 24472,
"missing_orphan_company_ids": 1,
```

---

## 5. Salary Semantics & Cross-Source Comparability

### 5.1 Indeed Salary Semantics
Indeed postings provide salary data strictly as discrete query search brackets:
- `salary.salary_bucket` [SOURCE / NORMALIZED]: Preserves the queried salary bracket (e.g., `"<80000"`, `"80000-99999"`, `"100000-119999"`, etc.).
- `salary.normalized_annual`: **UNAVAILABLE (`null`)**. Indeed does not provide an authoritative numeric continuous annual salary. Discrete brackets are **never converted into fake exact salaries**.
- `salary.estimated_midpoint` [DERIVED]: Mathematical midpoint estimated from the discrete salary band (e.g., `<80000` → `70000.0`, `100000-119999` → `110000.0`). Stored exclusively in the dedicated midpoint field and documented as a derived estimate.

### 5.2 LinkedIn Salary Semantics
LinkedIn postings provide stated compensation boundaries when available:
- `salary.normalized_annual` [SOURCE]: Stored directly from LinkedIn's source column `normalized_salary` (an annualized calculation provided by LinkedIn for yearly/hourly pay). When unstated (70.9% of postings), remains strictly `null` (never 0).
- `salary.salary_bucket` [NORMALIZED]: Standardized query bracket into which the stated salary falls.
- `salary.estimated_midpoint`: **UNAVAILABLE (`null`)**. Stated continuous boundaries exist; midpoint estimation is not performed for LinkedIn.

### 5.3 Cross-Source Salary Comparability Note
**Analytical Caution for Phase 5 Queries & Aggregations:**
LinkedIn and Indeed salary values are **NOT equally precise**:
- **LinkedIn:** Offers continuous, exact annual compensation (e.g., `$105,000.00`) when stated, but is missing in ~70.9% of postings.
- **Indeed:** Offers discrete query brackets (e.g., `"<80000"`) for 100% of postings, but lacks exact continuous numbers.

**Mandatory Rule for Future Analytics:**
Any future analytical queries or visualizations must explicitly differentiate between:
1. **Exact / Source-Supported Annual Salary:** `salary.normalized_annual` (LinkedIn only).
2. **Discrete Salary Band:** `salary.salary_bucket` (Common normalized dimension across both sources).
3. **Derived Midpoint Estimate:** `salary.estimated_midpoint` (Indeed derived estimate).

An Indeed midpoint estimate must **NEVER** be treated or aggregated as an observed or authoritative exact salary.

---

## 6. Final ETL Execution Metrics

The full ETL pipeline was rerun across the entire source datasets using `python scripts/run_etl.py`:

```json
{
  "execution_timestamp": "2026-10-28T16:33:02.327602+00:00",
  "total_processing_time_seconds": 72.88,
  "dataset_metrics": {
    "linkedin": {
      "source_postings": 123849,
      "transformed_postings": 123835,
      "rejected_postings": 14,
      "duplicate_source_ids": 0,
      "referenced_company_ids": 24474,
      "extracted_company_profiles": 24472,
      "missing_orphan_company_ids": 1,
      "missing_company_links": 1,
      "missing_salaries": 87776,
      "missing_skills": 1753,
      "missing_industries": 1436,
      "missing_benefits": 95114,
      "companies_extracted": 24472
    },
    "indeed": {
      "source_postings": 5715,
      "transformed_postings": 5715,
      "rejected_postings": 0,
      "duplicate_source_ids": 0,
      "missing_skills": 232,
      "missing_companies": 104,
      "missing_descriptions": 302
    },
    "unified_totals": {
      "total_transformed_jobs": 129550,
      "total_companies": 24472,
      "total_rejected": 14,
      "total_duplicates": 0,
      "jobs_output_file": "C:\\ADBMS PROJECT\\JobMarketDB\\data\\processed\\jobs_transformed.jsonl",
      "jobs_file_size_mb": 647.31,
      "companies_output_file": "C:\\ADBMS PROJECT\\JobMarketDB\\data\\processed\\companies_transformed.jsonl",
      "companies_file_size_mb": 35.24
    }
  },
  "phase_boundaries_verified": {
    "mongodb_connected": false,
    "data_imported_to_db": false,
    "original_datasets_modified": false,
    "schema_integrity_validated": true
  }
}
```

### Metrics Summary Table

| Metric | LinkedIn Dataset | Indeed Dataset | Unified Total |
| :--- | :--- | :--- | :--- |
| **Source Postings** | 123,849 | 5,715 | **129,564** |
| **Transformed Postings** | 123,835 | 5,715 | **129,550** |
| **Rejected Postings** | 14 *(null title in source)* | 0 | **14** |
| **Duplicate Source IDs** | 0 | 0 | **0** |
| **Referenced Company IDs** | 24,474 | N/A *(embedded by name)* | **24,474** |
| **Extracted Company Profiles** | 24,472 | N/A | **24,472** |
| **Missing / Orphan Company IDs** | 1 *(ID 23729571)* | N/A | **1** |
| **Missing Company Links / Names** | 1 | 104 | **105** |
| **Missing / Unstated Salaries** | 87,776 *(70.9%)* | 0 *(all have query bands)* | **87,776** |
| **Missing / Unstated Skills** | 1,753 | 232 | **1,985** |
| **Missing Industries** | 1,436 | 1,027 | **2,463** |
| **Missing Benefits** | 95,114 | 5,715 *(Indeed lacks benefits)* | **100,829** |
| **Missing Descriptions** | 0 | 302 | **302** |
| **Processing Duration** | 55.83s | 6.67s | **72.88s** |

---

## 7. Output Verification & Scope Checklist

All validation criteria were executed and verified:

- [x] **All Python files compile cleanly:** Confirmed via `python -m py_compile app.py ingestion/*.py scripts/*.py`.
- [x] **Raw datasets remain untouched:** Confirmed (`datasets/archive.zip` and `datasets/indeed_job_dataset.csv.zip` unmodified).
- [x] **Phase 2 schema is unchanged except for documentation clarification:** Confirmed.
- [x] **Indeed `normalized_annual` remains `null`:** Confirmed across all 5,715 Indeed postings.
- [x] **Indeed `estimated_midpoint` remains derived:** Confirmed. Midpoint calculated solely from discrete queried brackets.
- [x] **LinkedIn salary semantics remain correct:** Confirmed. `normalized_annual` populated strictly from source; `estimated_midpoint` remains `null`.
- [x] **Missing LinkedIn company ID explicitly identified:** Confirmed (`company_id: 23729571` in job `3708903045`).
- [x] **No fabricated company document exists:** Confirmed. Exactly 24,472 authentic company master profiles exist in `companies_transformed.jsonl`.
- [x] **Existing transformed job count remains 129,550:** Confirmed (123,835 LinkedIn + 5,715 Indeed).
- [x] **Duplicate source IDs remain 0:** Confirmed for both datasets.
- [x] **MongoDB remains unused:** Confirmed. No connection opened; no collections or indexes created; no data imported.
- [x] **No Streamlit UI created:** Confirmed.

---

## 8. Representative Transformed Records

### 8.1 Corrected LinkedIn Job Document (Stated City/State, Tri-State Remote Null)
```json
{
  "source": "linkedin",
  "source_job_id": "10998357",
  "title": "Assitant Restaurant Manager",
  "description": "The National Exemplar is accepting applications for an Assistant Restaurant Manager...",
  "company": {
    "company_id": 64896719,
    "name": "The National Exemplar",
    "company_size": "1-10",
    "industry": "Restaurants"
  },
  "location": {
    "raw": "Cincinnati, OH",
    "city": "Cincinnati",
    "state": "OH",
    "country": "United States",
    "zip_code": "45202",
    "is_remote": null
  },
  "salary": {
    "min_salary": 45000.0,
    "max_salary": 65000.0,
    "med_salary": null,
    "pay_period": "YEARLY",
    "currency": "USD",
    "compensation_type": "BASE_SALARY",
    "normalized_annual": 55000.0,
    "salary_bucket": "<80000",
    "estimated_midpoint": null
  },
  "skills": [
    "Management",
    "Manufacturing"
  ],
  "industries": [
    "Restaurants"
  ],
  "benefits": [],
  "source_employment_type": "Full-time",
  "normalized_employment_type": "Full-time",
  "experience_level": {
    "value": null,
    "status": "NOT_AVAILABLE"
  },
  "role_category": {
    "value": "Other",
    "status": "DERIVED / INFERRED",
    "derived_from": "title"
  },
  "job_url": "https://www.linkedin.com/jobs/view/10998357/?trk=jobs_biz_prem_srch",
  "application_url": null,
  "application_type": "ComplexOnsiteApply",
  "posted_date": "2024-04-16T14:26:54+00:00",
  "estimated_posted_date": null,
  "expiry_date": "2024-05-16T14:26:54+00:00",
  "views_count": 8,
  "applies_count": null,
  "is_sponsored": false,
  "source_data": {
    "linkedin": {
      "fips": 39061.0,
      "posting_domain": null,
      "closed_time": null,
      "skills_desc": "We are currently accepting resumes for FOH..."
    }
  }
}
```

### 8.2 Corrected Indeed Job Document (Preserved Authentic Source Key & Null Remote)
```json
{
  "source": "indeed",
  "source_job_id": "6a105f495c36afe3",
  "title": "Data Scientist",
  "description": "[ What do we need? , You to have an amazing personality and communication style... ]",
  "company": {
    "company_id": null,
    "name": "Express Scripts",
    "company_size": "10,000+",
    "industry": "Health Care"
  },
  "location": {
    "raw": "MO",
    "city": null,
    "state": "MO",
    "country": "United States",
    "zip_code": null,
    "is_remote": null
  },
  "salary": {
    "min_salary": null,
    "max_salary": null,
    "med_salary": null,
    "pay_period": null,
    "currency": "USD",
    "compensation_type": "QUERY_BUCKET",
    "normalized_annual": null,
    "salary_bucket": "<80000",
    "estimated_midpoint": 70000.0
  },
  "skills": [
    "SAP",
    "SQL"
  ],
  "industries": [
    "Health Care"
  ],
  "benefits": [],
  "source_employment_type": null,
  "normalized_employment_type": null,
  "experience_level": {
    "value": null,
    "status": "NOT_AVAILABLE"
  },
  "role_category": {
    "value": "Data Scientist",
    "status": "NORMALIZED",
    "derived_from": "Job_Type"
  },
  "job_url": "https://www.indeed.com/rc/clk?jk=6a105f495c36afe3&fccid=281a27deb89bbe92&vjs=3",
  "application_url": null,
  "application_type": "IndeedApply",
  "posted_date": null,
  "estimated_posted_date": "2024-03-31T00:00:00+00:00",
  "expiry_date": null,
  "views_count": null,
  "applies_count": null,
  "is_sponsored": false,
  "source_data": {
    "indeed": {
      "row_index": 0,
      "source_job_id_extracted_from_url": true,
      "date_since_posted_days": 1.0,
      "company_revenue": "More than $10B (USD)",
      "company_employees_category": "10,000+",
      "company_reviews_count": 3301.0,
      "company_star_rating": 3.3,
      "skill_count": 2,
      "tool_indicators": {
        "python": 0,
        "sql": 1,
        "machine_learning": 0,
        "r": 0,
        "hadoop": 0,
        "tableau": 0,
        "sas": 0,
        "spark": 0,
        "java": 0,
        "others": 1
      }
    }
  }
}
```

---

## 9. Phase 3 Final Status

The Phase 3 ETL implementation, audits, and validations are complete and locked. The generated outputs in `data/processed/` are ready for Phase 4:

1. `data/processed/jobs_transformed.jsonl` (129,550 documents, 647.31 MB)
2. `data/processed/companies_transformed.jsonl` (24,472 documents, 35.24 MB)
3. `data/processed/etl_summary.json` (1.41 KB)
