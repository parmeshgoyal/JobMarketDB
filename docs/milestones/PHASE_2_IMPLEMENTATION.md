# Phase 2 Implementation Report: Dataset Analysis & MongoDB Data Model

## 1. Phase 2 Objective
Perform deep exploratory data analysis on the two real-world datasets powering **JobMarketDB** (LinkedIn Job Postings 2023–2024 and Indeed Dataset for Data Scientists/Analysts/Engineers), discover real data structures, data quality characteristics, and relationships, and design an optimized, practical MongoDB/NoSQL data model tailored for the Streamlit analytics and search application.

---

## 2. Dataset Files Inspected
All 12 dataset files across the LinkedIn and Indeed archives were directly profiled:

| Dataset | File Path | Uncompressed Size | Row Count | Columns |
| :--- | :--- | :--- | :--- | :--- |
| **LinkedIn** | `archive/postings.csv` | 492.90 MB | 123,849 | 31 |
| **LinkedIn** | `archive/companies/companies.csv` | 22.12 MB | 24,473 | 10 |
| **LinkedIn** | `archive/companies/company_industries.csv` | 0.75 MB | 24,375 | 2 |
| **LinkedIn** | `archive/companies/company_specialities.csv` | 4.23 MB | 169,387 | 2 |
| **LinkedIn** | `archive/companies/employee_counts.csv` | 1.00 MB | 35,787 | 4 |
| **LinkedIn** | `archive/jobs/benefits.csv` | 1.84 MB | 67,943 | 3 |
| **LinkedIn** | `archive/jobs/job_industries.csv` | 2.39 MB | 164,808 | 2 |
| **LinkedIn** | `archive/jobs/job_skills.csv` | 3.34 MB | 213,768 | 2 |
| **LinkedIn** | `archive/jobs/salaries.csv` | 2.15 MB | 40,785 | 8 |
| **LinkedIn** | `archive/mappings/industries.csv` | 0.01 MB | 422 | 2 |
| **LinkedIn** | `archive/mappings/skills.csv` | 0.001 MB | 35 | 2 |
| **Indeed** | `indeed_job_dataset.csv/indeed_job_dataset.csv` | 18.14 MB | 5,715 | 43 |

---

## 3. Dataset Statistics & Key Numbers
- **Total Combined Postings:** 129,564 job listings (123,849 LinkedIn + 5,715 Indeed).
- **Date Span (LinkedIn):** December 5, 2023 to April 20, 2024.
- **Indeed Focus Roles:** 2,543 Data Scientists (44.5%), 1,793 Data Analysts (31.4%), 1,379 Data Engineers (24.1%).
- **Employer Coverage:** 24,413 distinct employers in LinkedIn; 2,231 in Indeed.
- **Company Overlap:** 599 companies appear in both LinkedIn and Indeed datasets (e.g., Goldman Sachs, NVIDIA, Lenovo, LabCorp).

---

## 4. Formal Data Provenance Framework
All fields in the schema and data dictionary are classified into three strict provenance tiers:
1. **SOURCE:** Directly present in the original dataset without alteration of meaning or structure (e.g. LinkedIn `title`, `formatted_work_type`, `original_listed_time`; Indeed `Job_Title`, `Queried_Salary`, `Job_Type`, `Date_Since_Posted`).
2. **NORMALIZED:** Converted into a common, standardized representation without claiming it was originally present in exactly that form (e.g. 2-letter state codes, harmonized salary bucket strings).
3. **DERIVED / INFERRED:** Calculated, estimated, or inferred from one or more source fields using heuristic rules or mathematical formulas (e.g. `salary.estimated_midpoint`, `role_category`, `estimated_posted_date`).

---

## 5. Specific Provenance Corrections & Modeling Decisions
1. **Employment Type — Source vs. Normalized:**
   - **LinkedIn:** Preserves `source_employment_type` directly from `formatted_work_type` (`Full-time`, `Contract`, etc.) and provides a standardized `normalized_employment_type`.
   - **Indeed:** Records `source_employment_type: null` and `normalized_employment_type: null`. The Indeed dataset contains **no employment contract type column** (`Job_Type` denotes professional discipline). We do not silently invent an employment type.
2. **Role Category — Application-Level Derived Field:**
   - `role_category` is documented as an application-level field created for cross-dataset analysis.
   - For LinkedIn: derived/inferred from `title`.
   - For Indeed: normalized from `Job_Type` (`data_scientist` -> `Data Scientist`).
   - Clearly documented that this is NOT a native source column.
3. **Publication Date — Source vs. Estimated:**
   - **LinkedIn `posted_date` [SOURCE]:** Authentic publication timestamp converted from `original_listed_time` epoch milliseconds to ISO Date.
   - **Indeed:** Native publication date is **NOT AVAILABLE** in the dataset (`posted_date: null`). A separate field `estimated_posted_date` [DERIVED / ESTIMATED] is calculated from `Date_Since_Posted` and a reference crawl date. No fake publication timestamp is invented.
4. **Source Skills Preserved (No False Equivalencies):**
   - LinkedIn skills represent 35 broad functional categories (`IT`, `Engineering`, `Analyst`, `Finance`), whereas Indeed skills represent specific software tools (`Python`, `SQL`, `Machine Learning`, `AWS`).
   - We do **NOT** assert false mappings (e.g., claiming LinkedIn `"IT"` equals Indeed `"Python"`). The `skills` array preserves authentic source data. Any unified taxonomy is documented as an analytical layer.
5. **Salary Integrity & Midpoint Estimation:**
   - Discrete salary ranges (e.g. Indeed's `"100000-119999"`) are **never converted into fake exact salaries**.
   - Derived midpoints are stored in a dedicated `salary.estimated_midpoint` field, clearly separated from stated compensation.
   - Missing salary values are preserved as `null`, **never converted to 0**.
6. **Remote Status Tri-State Representation:**
   - Represented as a tri-state boolean: `true` (explicitly remote), `false` (explicitly on-site), and `null` (unknown / not provided in source). Indeed postings without remote indicators are set to `null` rather than defaulted to `false`.
7. **Source Job Identifier Disambiguation:**
   - Distinguished `_id` (MongoDB `ObjectId`), `source` (`"linkedin"` / `"indeed"`), and `source_job_id`.
   - For LinkedIn: native integer `job_id` preserved.
   - For Indeed: extracted `jk` URL parameter preserved, with explicit audit documentation that Indeed has no native `job_id` column.

---

## 6. Proposed Common Job Model & Collection Architecture
A hybrid two-collection architecture is recommended:
1. **`jobs` (Primary Collection):** Designed for the 129,564 source job postings from LinkedIn and Indeed. After Phase 3 validation, 129,550 postings are eligible for MongoDB import because 14 LinkedIn records with null titles were rejected.
2. **`companies` (Supporting Collection):** Contains 24,472 valid employer profiles extracted during Phase 3. One LinkedIn company_id referenced by a posting was absent from the authoritative company source data, and one company source row had no usable name; therefore no fabricated company documents were created.

---

## 7. Files Created & Refined in Phase 2
All documentation was created and refined within [JobMarketDB](file:///C:/ADBMS%20PROJECT/JobMarketDB):
1. [PHASE_2_DATASET_ANALYSIS.md](file:///C:/ADBMS%20PROJECT/JobMarketDB/PHASE_2_DATASET_ANALYSIS.md): Comprehensive inventory, column profiling, relationships, orphans, data quality findings, and source taxonomy distinctions.
2. [PHASE_2_DATA_DICTIONARY.md](file:///C:/ADBMS%20PROJECT/JobMarketDB/PHASE_2_DATA_DICTIONARY.md): Field-by-field BSON specification, explicit provenance tiers (SOURCE, NORMALIZED, DERIVED), transformations, nullability, and usage.
3. [PHASE_2_MONGODB_SCHEMA.md](file:///C:/ADBMS%20PROJECT/JobMarketDB/PHASE_2_MONGODB_SCHEMA.md): Architecture rationale, representative JSON documents for LinkedIn and Indeed, embedding trade-offs, and query-driven indexing.
4. [PHASE_2_IMPLEMENTATION.md](file:///C:/ADBMS%20PROJECT/JobMarketDB/PHASE_2_IMPLEMENTATION.md): Execution summary, correction log, and verification report.

---

## 8. Verification & Phase 1 Preservation
- [app.py](file:///C:/ADBMS%20PROJECT/JobMarketDB/app.py) was verified with `py_compile` (exit code `0`, no syntax errors).
- All Phase 1 files (`requirements.txt`, `.gitignore`, `.env.example`, `README.md`, `PHASE_1_IMPLEMENTATION.md`) remain untouched and functional.
- Original datasets in `datasets/archive.zip` and `datasets/indeed_job_dataset.csv.zip` remain completely unmodified.
- **No MongoDB connection, collection creation, index creation, or data ingestion occurred.**

---

### Success Criteria Checklist
- [x] Actual LinkedIn files inspected
- [x] Actual Indeed file inspected
- [x] Dataset inventory completed
- [x] Important columns documented
- [x] Relationships verified
- [x] Missing values documented
- [x] Duplicate analysis completed
- [x] Data-quality issues documented
- [x] Cross-dataset compatibility documented
- [x] Common job model proposed
- [x] MongoDB collection design proposed
- [x] Embedding/reference decisions justified
- [x] Representative MongoDB document created
- [x] Query-driven schema decisions documented
- [x] Data dictionary created
- [x] Provenance tiers (SOURCE, NORMALIZED, DERIVED / INFERRED) consistently applied
- [x] Employment type distinguishes LinkedIn source from Indeed missing (`null`)
- [x] Role category documented as derived/normalized application field
- [x] Posted date distinguishes LinkedIn source from Indeed derived/estimated
- [x] Source skills preserved without false equivalencies
- [x] Experience level distinguished as Observed vs Inferred
- [x] Source job identifiers disambiguated from MongoDB `_id`
- [x] Salary normalization distinguishes exact, bucket, and estimated midpoint (nulls never converted to 0)
- [x] Indeed remote status uses `null` for unknown
- [x] Phase 1 remains intact
- [x] Original datasets remain untouched
- [x] No MongoDB connection
- [x] No data import
- [x] No ETL
- [x] No UI
- [x] Implementation report created

**Phase 2 documentation corrections are complete. STOPPING as instructed.**
