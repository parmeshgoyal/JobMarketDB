# Phase 5 Implementation Report — Core Query & Analytics Services**Project:** JobMarketDB — Advanced Database Management System (ADBMS)  
**Database:** `jobmarketdb`  
**Initial Implementation:** 2026-10-28T18:56:14 UTC / Local Time: 2026-10-29 00:26 IST  
**Final Audit & Verification Run:** 2026-10-29T11:12:49 UTC / Local Time: 2026-10-29 16:42 IST  
**Status:** **AUDITED, CORRECTED & VERIFIED (Phase 5 Complete)**

---

## 1. Executive Summary & Audit Overview

Phase 5 implements and validates the query and analytical aggregation service layer for JobMarketDB. Building upon the verified MongoDB deployment established in Phase 4, Phase 5 translates the 12 core query/analytics operations specified in [PHASE_2_MONGODB_SCHEMA.md](file:///c:/ADBMS%20PROJECT/JobMarketDB/PHASE_2_MONGODB_SCHEMA.md) into high-performance, modular Python services with strict provenance fidelity, reproducible metrics, and read-only safety guarantees.

Following the initial Phase 5 milestone, a targeted empirical audit and correction pass was conducted across five core priorities:
1. **Salary Outlier Audit (Priority 1 — CORRECTED & VERIFIED):** Investigated the reported LinkedIn average of $1,109,368.91 in the `>160000` salary bucket. An exhaustive evidentiary audit of all 38 LinkedIn records with `salary.normalized_annual > 1,000,000` classified them into four distinct categories and persisted them to [data/processed/phase_5_salary_outlier_audit.json](file:///c:/ADBMS%20PROJECT/JobMarketDB/data/processed/phase_5_salary_outlier_audit.json):
   - **Confirmed hourly-to-annual conversion errors (19 records):** Recruiter entered an annual base salary ($26k–$275k) under `pay_period: 'HOURLY'`, which Kaggle upstream ETL multiplied by 2,080.
   - **Recruiter/source salary-entry errors (10 records):** Recruiter typo/concatenation errors (e.g. max $6,570/hr for $70/hr, or $85M–$120M yearly), 6 Sherwin-Williams postings entering annual salaries under `pay_period: 'BIWEEKLY'` multiplied by 26 ($1.57M–$2.10M), and 1 posting entering annual salary under `pay_period: 'MONTHLY'` multiplied by 12 ($1.20M).
   - **Other confirmed issues (1 record):** Job 3885103252 (Secret Shopper task fee of $600 tagged `HOURLY` and multiplied by 2,080 to $1.248M).
   - **Unresolved cases (8 records):** Kaiser Permanente Student Nurse and Summer Intern postings with hourly rates ($16–$21/hr) in descriptions but $15.6k–$20k recorded under `HOURLY`, yielding $32.4M–$41.6M; unresolved whether recruiter entered partial-year earnings or an internship stipend.
   - **Analytics Enhancement:** Computed the approximate median continuous pay ($190,000.00) using MongoDB's native `$median` accumulator (`method: "approximate"`), a threshold-adjusted mean ($213,464.73) strictly excluding LinkedIn continuous salary values greater than $1,000,000 (explicitly conditional on `source == "linkedin"`), and preserved the unadjusted stored mean ($1,109,368.91) for mathematical transparency. Filter-independent methodology notes replaced hard-coded bucket statistics. All imported MongoDB documents remain strictly immutable.
2. **Skill Taxonomy & Distinct Posting Counts (Priority 2 — CORRECTED & VERIFIED):** Audited `analytics/aggregations.py` to address the fundamental abstraction gap between LinkedIn's 35 broad functional disciplines and Indeed's 464 specific technical tools. Demonstrated via database-wide verification that 100% of multi-skill postings (74,016 postings) contain zero duplicate tokens; additionally implemented defensive `$setUnion` deduplication in the aggregation pipeline to guarantee distinct posting counts. Reported LinkedIn and Indeed skill demand rankings separately via `get_skills_by_platform()`, calculated percentages against platform-specific denominators, and retained the combined ranking only as a caveated, population-weighted view.
3. **Reproducible Query Plan Audit via `explain("executionStats")` (Priority 3 & 4 — CORRECTED & VERIFIED):** Built a reproducible standalone audit suite ([scripts/audit_phase_5_queries.py](file:///c:/ADBMS%20PROJECT/JobMarketDB/scripts/audit_phase_5_queries.py)) capturing `explain("executionStats")` across exactly **20 audited cases** (14 operational queries and 6 aggregation pipelines) with recursive stage walking. Persisted results to [data/processed/phase_5_query_plan_audit.json](file:///c:/ADBMS%20PROJECT/JobMarketDB/data/processed/phase_5_query_plan_audit.json). Accurately distinguished `TEXT_INDEX`, `IXSCAN`, `COVERED_IXSCAN`, and legitimate `COLLSCAN` operations (regex title search, continuous salary without bucket prefix, orphan company ID on `jobs`, and unconstrained aggregations).
4. **Read-Only Invariants & Strict Index Safety (Priority 4 — ALL PASS):** Audited document counts and index definitions before and after verification. Confirmed collection counts remained strictly unchanged (**129,550 jobs** and **24,472 companies**; Delta = 0). Verified that index configurations remained 100% identical (**11 indexes on `jobs`**, **4 indexes on `companies`**; zero index changes).
5. **API Guardrails & Input Validation (Priority 5 — PASS):** Enforced strict validation across `analytics/queries.py`, `analytics/aggregations.py`, and `analytics/service.py`: invalid `search_mode` values, negative `skip`, non-positive limits (`limit <= 0` across all queries and aggregations, removing silent conversion via `max(1, limit)`), arbitrary integers like `2` for `is_remote` (properly handling Python boolean subclassing), and invalid salary ranges (`min_annual > max_annual`) raise `ValueError`. Verified that `is_remote=None` intentionally filters for unknown remote status while `is_remote='any'` performs no remote filtering across all query and aggregation functions. Tested against populated role categories to guarantee no errors are concealed.

---

## 2. Architecture & Modular Package Structure

The analytics layer is organized as a decoupled Python package in [analytics/](file:///c:/ADBMS%20PROJECT/JobMarketDB/analytics/):

```text
analytics/
├── __init__.py           # Package exports for service class and standalone functions
├── queries.py            # Operational search and filtering queries (Operations 1–7 + Faceted Search)
├── aggregations.py       # Analytical aggregations and platform comparisons (Operations 8–12)
└── service.py            # JobMarketAnalyticsService unified API client
```

### Module Responsibilities & Audit Enhancements
1. **[analytics/queries.py](file:///c:/ADBMS%20PROJECT/JobMarketDB/analytics/queries.py)**: Encapsulates document-level search, filtering, pagination, and projection logic. Supports both full-text search (utilizing `title_text_description_text`) and title regex matching, compound geographic filtering with tri-state remote semantics, continuous and bucketed salary ranges, multi-key skill filtering (`$all` / `$in`), company lookups, and multi-faceted search. Validates pagination, salary ranges, search modes, and remote states.
2. **[analytics/aggregations.py](file:///c:/ADBMS%20PROJECT/JobMarketDB/analytics/aggregations.py)**: Implements multi-stage aggregation pipelines:
   - `get_top_demanded_skills()`: Enhanced with `$setUnion` distinct posting deduplication, explicit taxonomy notes, and embedded platform breakdowns.
   - `get_skills_by_platform()`: Dedicated separate namespace reporting LinkedIn disciplines versus Indeed technical tools with distinct denominators.
   - `get_salary_distributions()`: Enhanced with MongoDB `$median` accumulator (`method: "approximate"`), threshold-adjusted mean strictly excluding values > $1,000,000, outlier counts, and filter-independent provenance notes.
   - `get_top_hiring_companies()`, `get_top_job_locations()`, and `compare_sources()`.
3. **[analytics/service.py](file:///c:/ADBMS%20PROJECT/JobMarketDB/analytics/service.py)**: Encapsulates `JobMarketAnalyticsService`, providing consuming applications (such as the upcoming Phase 6 Streamlit UI) with a single, typed, parameter-validated, and audit-safe interface.

---

## 3. Implementation of the 12 Core Operations

### 3.1 Operational Queries (Operations 1 to 7)

All metrics below reflect the synchronized single audit run recorded at **2026-10-29T11:12:49 UTC**:

| Op # | Operation Name | Query Invocation | Supporting Index / Mechanism | Execution Stage | totalKeysExamined | totalDocsExamined | nReturned | Execution Time |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1a** | **Job Search (Text)** | `$text: { $search: "Data Scientist" }` | `title_text_description_text` | `TEXT_MATCH -> FETCH -> IXSCAN` | 49,665 | 45,112 | 45,112 | 430 ms |
| **1b** | **Job Search (Regex)** | `title: { $regex: "Data Scientist", $options: "i" }` | None (Unindexed regex on title) | `COLLSCAN` | 0 | 129,550 | 2,632 | 561 ms |
| **2a** | **Location Filtering** | `state: "CA", is_remote: true` | `location.state_1_location.is_remote_1` | `FETCH -> IXSCAN` | 975 | 975 | 975 | 6 ms |
| **2b** | **Location (Tri-State Null)**| `state: "NY", is_remote: null` | `location.state_1_location.is_remote_1` | `FETCH -> IXSCAN` | 7,693 | 7,693 | 7,693 | 52 ms |
| **3a** | **Salary Bucket Filter** | `salary.salary_bucket: "100000-119999"` | `salary.salary_bucket_1_salary.normalized_annual_1` | `FETCH -> IXSCAN` | 5,486 | 5,486 | 5,486 | 42 ms |
| **3b** | **Salary Range (Continuous)**| `salary.normalized_annual: [100k, 120k]` | None (Index prefix missing; see Note 1) | `COLLSCAN` | 0 | 129,550 | 4,358 | 351 ms |
| **3c** | **Salary Bucket + Range** | Bucket `"100000-119999"` + Range `[100k, 120k]` | `salary.salary_bucket_1_salary.normalized_annual_1` | `FETCH -> IXSCAN` | 4,092 | 4,092 | 4,092 | 28 ms |
| **4a** | **Skill Demand ($all)** | `skills: { $all: ["Python", "SQL"] }` | `skills_1` (Multi-key) | `FETCH -> IXSCAN` | 3,104 | 3,104 | 2,075 | 22 ms |
| **4b** | **Skill Demand ($in)** | `skills: { $in: ["Python"] }` | `skills_1` (Multi-key) | `FETCH -> IXSCAN` | 3,325 | 3,325 | 3,325 | 15 ms |
| **5a** | **Company Name Filter** | `company.name: "Express Scripts"` | `company.name_1` | `FETCH -> IXSCAN` | 2 | 2 | 2 | 0 ms |
| **5b** | **Company ID Filter** | `company.company_id: 23729571` | None (Index on `companies`, not `jobs`; see Note 2) | `COLLSCAN` | 0 | 129,550 | 1 | 307 ms |
| **6** | **Experience Level** | `experience_level.value: "Mid-Senior level"` | `experience_level.value_1` | `FETCH -> IXSCAN` | 41,488 | 41,488 | 41,488 | 204 ms |
| **7a** | **Source Filter (LinkedIn)**| `source: "linkedin"` | `source_1` | `FETCH -> IXSCAN` | 123,835 | 123,835 | 123,835 | 569 ms |
| **7b** | **Source Filter (Indeed)** | `source: "indeed"` | `source_1` | `FETCH -> IXSCAN` | 5,715 | 5,715 | 5,715 | 28 ms |

> [!NOTE]
> **Query Plan Clarifications (Priority 3 Audit):**
> 1. **Continuous Salary Filtering (Op 3b):** The Phase 2 compound index is `{ "salary.salary_bucket": 1, "salary.normalized_annual": 1 }`. Filtering on `normalized_annual` alone without a discrete bucket prefix does not satisfy MongoDB B-tree index prefix rules, resulting in a collection scan (`COLLSCAN`). When both bucket and continuous bounds are supplied (Op 3c), the index is fully utilized (`IXSCAN`).
> 2. **Company ID Lookups on `jobs` (Op 5b):** The unique index `company_id_1_unique` resides on the `companies` master collection. On the operational `jobs` collection, only `company.name_1` is indexed. Looking up orphan job postings by `company.company_id` scans `jobs` directly. This is an expected schema design trade-off, not a defect.

---

### 3.2 Analytical Aggregations (Operations 8 to 12)

#### Operation 8: Top Demanded Skills Aggregation & Skill Taxonomy Audit (Priority 2)

- **Execution Pipeline:** Optional `$match` $\rightarrow$ `$project: { skills: { $setUnion: ["$skills", []] }, source: 1 }` $\rightarrow$ `$unwind: "$skills"` $\rightarrow$ `$group: { _id: "$skills", count: { $sum: 1 } }` $\rightarrow$ `$sort: { count: -1 }` $\rightarrow$ `$limit: 5`
- **Counting Methodology:** Distinct job postings containing that skill (not repeated token occurrences within the same posting).
- **Token Uniqueness Audit & Guarantee:** Audited all 74,016 postings with multi-element skill arrays across the database. Exactly **0 postings** contain duplicate tokens in `skills`. The aggregation pipeline enforces `$setUnion` prior to `$unwind` to mathematically guarantee distinct posting counts across all filter scopes.
- **Percentage of Postings:** Computed as `(distinct_postings_with_skill / total_postings_in_filter_scope) * 100`.

##### Combined Ranking (Population-Weighted Corpus: 129,550 postings)
1. *Information Technology:* 25,252 postings (19.49% of all postings)
2. *Sales:* 21,188 postings (16.36%)
3. *Management:* 20,385 postings (15.74%)
4. *Manufacturing:* 17,728 postings (13.68%)
5. *Health Care Provider:* 16,674 postings (12.87%)

> [!WARNING]
> **Taxonomy Audit Finding & Limitation (Priority 2):**
> The combined ranking is overwhelmingly dominated by LinkedIn because LinkedIn comprises 95.59% (123,835 / 129,550) of total postings. LinkedIn skills represent 35 broad functional disciplines (e.g., Information Technology, Management, Sales), whereas Indeed skills represent 464 specific technical tools, programming languages, and frameworks (e.g., Python, SQL, Machine Learning).
> 
> Pooling them into a single ranking without disclaimers obscures technical skills: Python (58.18% of Indeed data science postings) and SQL (54.31% of Indeed) do not appear in the combined top 5. Only **4 skill names overlap** across both platforms: `Customer Service`, `Marketing`, `Public Relations`, and `Project Management`. Broad LinkedIn domain categories must never be claimed to be equivalent to specific Indeed tools.

##### Platform-Separated Rankings (Preserved Provenance)

| Rank | LinkedIn Top Disciplines (Denominator: 123,835) | Postings | Share | Indeed Top Tools & Technologies (Denominator: 5,715) | Postings | Share |
| :---: | :--- | :---: | :---: | :--- | :---: | :---: |
| **1** | **Information Technology** | 25,252 | 20.39% | **Python** | 3,325 | 58.18% |
| **2** | **Sales** | 21,188 | 17.11% | **SQL** | 3,104 | 54.31% |
| **3** | **Management** | 20,385 | 16.46% | **Machine Learning** | 2,297 | 40.19% |
| **4** | **Manufacturing** | 17,728 | 14.32% | **R** | 2,234 | 39.09% |
| **5** | **Health Care Provider** | 16,674 | 13.46% | **Hadoop** | 1,714 | 29.99% |
| **6** | Business Development | 13,302 | 10.74% | Spark | 1,531 | 26.79% |
| **7** | Engineering | 12,526 | 10.12% | Java | 1,480 | 25.90% |
| **8** | Other | 12,312 | 9.94% | Tableau | 1,236 | 21.63% |
| **9** | Finance | 8,011 | 6.47% | Data Mining | 1,059 | 18.53% |
| **10** | Marketing | 5,397 | 4.36% | Hive | 966 | 16.90% |

- **Taxonomy Granularity Disclosed:** LinkedIn: 35 unique codes; Indeed: 464 unique tools. Provenance is strictly preserved.

---

#### Operation 9: Top Hiring Companies Aggregation

- **Pipeline:** `$match: { "company.name": { "$ne": null } }` $\rightarrow$ `$group: { _id: "$company.name", postings_count: { $sum: 1 }, sources: { $addToSet: "$source" } }` $\rightarrow$ `$sort: { postings_count: -1 }` $\rightarrow$ `$limit: 5`
- **Execution Plan:** Index scan on `company.name_1` (`keysExamined: 127,728`, `docsExamined: 127,727`, `nReturned: 26,076`).
- **Verified Findings:**
  1. *Liberty Healthcare and Rehabilitation Services:* 1,108 postings (`['linkedin']`)
  2. *The Job Network:* 1,003 postings (`['linkedin']`)
  3. *J. Galt:* 604 postings (`['linkedin']`)
  4. *Capital One:* 550 postings (`['indeed', 'linkedin']` — cross-platform presence verified)
  5. *TEKsystems:* 529 postings (`['linkedin']`)
- **Latency:** 1.265s

---

#### Operation 10: Top Job Locations Aggregation

- **Pipeline:** `$match: { "location.state": { "$ne": null } }` $\rightarrow$ `$group: { _id: "$location.state", postings_count: { $sum: 1 } }` $\rightarrow$ `$sort: { postings_count: -1 }` $\rightarrow$ `$limit: 5`
- **Execution Plan:** **Covered Index Scan** on `location.state_1_location.is_remote_1` (`keysExamined: 117,541`, `docsExamined: 0` [zero document fetches required], `nReturned: 51`).
- **Verified Findings:**
  1. *CA (California):* 13,892 postings
  2. *TX (Texas):* 11,468 postings
  3. *NY (New York):* 8,155 postings
  4. *FL (Florida):* 6,347 postings
  5. *NC (North Carolina):* 5,285 postings
- **Latency:** 0.823s

---

#### Operation 11: Salary Distributions & Outlier Audit (Priority 1)

- **Pipeline:** `$match: { "salary.salary_bucket": { "$ne": null } }` $\rightarrow$ `$group` by bucket with arithmetic sums, unadjusted `$avg`, native `$median` accumulator (`method: "approximate"`), and threshold-adjusted mean excluding values > $1,000,000.
- **Conditional Source Logic:** All continuous annual salary calculations (`unadjusted_mean`, `approx_median`, `threshold_adjusted_mean`, and `outlier_count_gt_1m`) are explicitly conditional on `source == "linkedin"`. For Indeed, `avg_normalized_annual` remains strictly `null` across all buckets, and only `avg_estimated_midpoint` is reported.
- **Index Support:** `$match` leverages `salary.salary_bucket_1_salary.normalized_annual_1` (`keysExamined: 41,775`, `docsExamined: 41,774`).

##### Verified Salary Distribution Table

| Salary Bucket | Total Postings | LinkedIn Postings | Indeed Postings | LinkedIn Unadjusted Mean (Stored) | LinkedIn Approx Median | LinkedIn Threshold-Adjusted Mean (<= $1M) | Indeed Avg Midpoint (Derived) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `<80000` | 18,229 | 17,441 | 788 | $51,375.37 | $50,905.23 | $51,375.37 | $70,000.00 |
| `80000-99999` | 5,574 | 4,621 | 953 | $88,935.79 | $88,742.25 | $88,935.79 | $90,000.00 |
| `100000-119999` | 5,486 | 4,092 | 1,394 | $109,027.30 | $109,200.00 | $109,027.30 | $110,000.00 |
| `120000-139999` | 4,464 | 3,172 | 1,292 | $128,990.63 | $129,523.73 | $128,990.63 | $130,000.00 |
| `140000-159999` | 3,188 | 2,315 | 873 | $148,277.40 | $148,000.00 | $148,277.40 | $150,000.00 |
| `>160000` | 4,833 | 4,418 | 415 | **$1,109,368.91\*** | **$190,000.00** | **$213,464.73** | $175,000.00 |

##### Comprehensive Audit of the `>160000` LinkedIn Outlier (Priority 1 Findings)

1. **Statistical Distribution in `>160000` (4,418 LinkedIn Records):**
   - **Count:** 4,418 postings
   - **Minimum:** $160,000.00
   - **25th Percentile:** $172,100.00
   - **Approximate Median:** $190,000.00 (MongoDB native `$median`, method: `approximate`)
   - **75th Percentile:** $225,000.00
   - **90th Percentile:** $287,500.00
   - **95th Percentile:** $363,337.62
   - **99th Percentile:** $866,500.00
   - **Unadjusted Arithmetic Mean:** $1,109,368.91
   - **Threshold-Adjusted Mean (excluding > $1,000,000):** $213,464.73
   - **Maximum:** $535,600,000.00
   - **Count Above $1,000,000:** Exactly 38 postings

2. **Evidentiary Classification of All 38 Outliers (> $1,000,000):**
   Every single record of the 38 LinkedIn outliers was inspected across job titles, company names, descriptions, pay periods, raw min/max/med salary fields, and normalized values. All 38 records, their classifications, recorded values, and individual evidentiary justifications are formally audited and persisted in [data/processed/phase_5_salary_outlier_audit.json](file:///c:/ADBMS%20PROJECT/JobMarketDB/data/processed/phase_5_salary_outlier_audit.json). They fall into four mutually exclusive, collectively exhaustive categories:
   - **Confirmed hourly-to-annual conversion errors (19 records):**
     * *Mechanism:* Recruiter entered an annual base salary ($26,000–$275,000) under `pay_period: 'HOURLY'`. The Kaggle ETL multiplied this annual figure by 2,080 hours, inflating normalized values to between $54,080,000.00 and $535,600,000.00.
     * *Sample Records:*
       - Job 3886471794: "Intellectual Property Associate", Eastridge Workforce Solutions. Stated in description: *"Anticipated annual base salary ranges between $240,000 and $275,000"*. Recorded `min: 240k, max: 275k, pay_period: HOURLY` $\rightarrow$ `normalized_annual: $535,600,000.00`.
       - Job 3904989090: "Case Manager RN, Pedi Rheumatology", Kaiser Permanente. `min: 151.9k, max: 196.57k, pay_period: HOURLY` $\rightarrow$ `normalized_annual: $362,408,800.00`.
       - Job 3887837646: "Cloud Domain Architect", Applicantz. `min: 125k, max: 150k, pay_period: HOURLY` $\rightarrow$ `normalized_annual: $286,000,000.00`.
       - Job 3898176295: "Sales Representative- Entry Level ($50k base + commission)", Ultimate Staffing. `min: 50k, max: 70k, pay_period: HOURLY` $\rightarrow$ `normalized_annual: $124,800,000.00`.
   - **Recruiter/source salary-entry errors (10 records):**
     * *Mechanism:* Typographical and unit misconfigurations entered by recruiters at job posting creation:
       - *Numerical Typos (3 records):* Job 3898171094 (max 6,570 entered for $70/hr $\rightarrow$ normalized $6,832,800); Job 3901343736 (max 5,060 for $60/hr $\rightarrow$ normalized $5,262,400); Job 3904911743 ("Marketing Director", EOX Vantage; entered 85,000,000 to 120,000,000 yearly $\rightarrow$ normalized $102,500,000.00).
       - *Bi-Weekly Annual Entries (6 records):* Sherwin-Williams postings entering annual salaries ($54k–$90k) under `pay_period: 'BIWEEKLY'`, which Kaggle ETL multiplied by 26 $\rightarrow$ $1,570,400 to $2,106,000.
       - *Monthly Annual Entry (1 record):* Job 3905389656 ("React UI Developer", KTek Resourcing; entered annual salary $90k–$110k under `pay_period: 'MONTHLY'`, multiplied by 12 $\rightarrow$ $1,200,000.00).
   - **Other confirmed issues (1 record):**
     * *Mechanism:* Job 3885103252 ("Secret Shopper", Sinclair Customer Metrics). Recruiter entered a single gig task assignment fee of $600 with `pay_period: 'HOURLY'`, which Kaggle ETL multiplied by 2,080 $\rightarrow$ `normalized_annual: $1,248,000.00`.
   - **Unresolved cases (8 records):**
     * *Mechanism:* 8 Kaiser Permanente "Student Nurse" and "Summer Intern" postings. Job descriptions explicitly state legitimate hourly wages ($16.00–$21.14/hr), but the structured data fields list `min_salary: 15600.0` to `20000.0` with `pay_period: 'HOURLY'`, yielding normalized salaries of $32,448,000.00 to $41,600,000.00. While clearly erroneous, it cannot be confirmed whether the recruiter entered a total summer internship stipend, a semester budget, or a partial-year compensation package. They are conservatively classified as Unresolved.

3. **Methodology Clarification & Safety Boundaries:**
   - **Zero Source Mutation:** In accordance with Phase 4 read-only invariants, source MongoDB documents were never deleted, modified, capped, or silently overwritten.
   - **Threshold-Adjusted Metric Definition:** The adjusted mean ($213,464.73) filters `salary.normalized_annual <= 1,000,000` as a pragmatic statistical threshold to report a central tendency free of multi-million-dollar arithmetic distortions. This threshold does not imply or prove that every excluded value is erroneous, nor does it imply values below $1M are entirely free of error.
   - **Approximate Median:** The median continuous salary ($190,000.00) is computed using MongoDB's `$median` accumulator with `method: "approximate"`.
   - **Dynamic Result Provenance:** Removed hard-coded overall-bucket constants from provenance notes; methodology notes are now filter-independent and dynamically derived from query results.


---

#### Operation 12: Cross-Platform Comparison Aggregation (LinkedIn vs. Indeed)

- **Pipeline:** `$group` by `$source` computing posting volumes, salary coverage rates, tri-state remote breakdowns, and distinct organizational/geographic footprints.
- **Verified Findings:**

| Dimension | LinkedIn (`linkedin`) | Indeed (`indeed`) | Cross-Platform Rationale |
| :--- | :--- | :--- | :--- |
| **Total Postings** | **123,835** (95.59%) | **5,715** (4.41%) | Verified exact Phase 4 counts |
| **Salary Data Available** | **36,059** (29.12%) | **5,715** (100.0%) | LinkedIn pay is opt-in stated; Indeed query is organized by discrete salary bands |
| **Explicitly Remote (`True`)** | **15,236** (12.30%) | **0** (0.0%) | Verified LinkedIn `remote_allowed == 1.0` |
| **Explicitly On-Site (`False`)** | **0** (0.0%) | **0** (0.0%) | Neither dataset explicitly flags 0.0 on-site |
| **Unknown Remote (`None`)** | **108,599** (87.70%) | **5,715** (100.0%) | Unknown is preserved as `null`, never merged to `false` |
| **Distinct Employers** | **24,415** | **2,231** | 599 employers present in both datasets |
| **Distinct US States Covered** | **51** (50 States + DC) | **49** | Near-universal national US geographic coverage |

- **Latency:** 1.394s

---

## 4. Comprehensive Index Utilization & Execution Plan Audit (`explain("executionStats")`)

To maintain academic and performance rigor under ADBMS standards, execution plans were audited using MongoDB's `explain("executionStats")` diagnostics against the live `jobmarketdb` database:

### 4.1 Operational Queries Execution Statistics Table

All metrics below reflect the synchronized single audit run recorded at **2026-10-29T11:12:49 UTC**:

| Operation / Query Filter | Winning Plan Stage | Index Name Used | totalKeysExamined | totalDocsExamined | nReturned | executionTimeMs | Index Utilization Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Op 1a:** Text Search `"Data Scientist"` | `TEXT_MATCH` | `title_text_description_text` | 49,665 | 45,112 | 45,112 | 430 ms | **PASS (TEXT Index)** |
| **Op 1b:** Title Regex `/"Data Scientist"/i` | `COLLSCAN` | None | 0 | 129,550 | 2,632 | 561 ms | **COLLSCAN (Expected — unindexed regex)** |
| **Op 2a:** CA + Remote=True | `FETCH` | `location.state_1_location.is_remote_1` | 975 | 975 | 975 | 6 ms | **PASS (IXSCAN)** |
| **Op 2b:** NY + Remote=None (Tri-State) | `FETCH` | `location.state_1_location.is_remote_1` | 7,693 | 7,693 | 7,693 | 52 ms | **PASS (IXSCAN)** |
| **Op 3a:** Salary Bucket `"100000-119999"` | `FETCH` | `salary.salary_bucket_1_salary.normalized_annual_1` | 5,486 | 5,486 | 5,486 | 42 ms | **PASS (IXSCAN)** |
| **Op 3b:** Continuous Annual ($100k–$120k) | `COLLSCAN` | None | 0 | 129,550 | 4,358 | 351 ms | **COLLSCAN (Index prefix missing; Note 1)** |
| **Op 3c:** Bucket + Continuous Annual | `FETCH` | `salary.salary_bucket_1_salary.normalized_annual_1` | 4,092 | 4,092 | 4,092 | 28 ms | **PASS (IXSCAN)** |
| **Op 4a:** Skills `$all: ["Python", "SQL"]` | `FETCH` | `skills_1` | 3,104 | 3,104 | 2,075 | 22 ms | **PASS (Multi-key IXSCAN)** |
| **Op 4b:** Skills `$in: ["Python"]` | `FETCH` | `skills_1` | 3,325 | 3,325 | 3,325 | 15 ms | **PASS (Multi-key IXSCAN)** |
| **Op 5a:** Company Name `"Express Scripts"` | `FETCH` | `company.name_1` | 2 | 2 | 2 | 0 ms | **PASS (IXSCAN)** |
| **Op 5b:** Company ID `23729571` | `COLLSCAN` | None | 0 | 129,550 | 1 | 307 ms | **COLLSCAN (Orphan ID on jobs; Note 2)** |
| **Op 6:** Experience `"Mid-Senior level"` | `FETCH` | `experience_level.value_1` | 41,488 | 41,488 | 41,488 | 204 ms | **PASS (IXSCAN)** |
| **Op 7a:** Source `"linkedin"` | `FETCH` | `source_1` | 123,835 | 123,835 | 123,835 | 569 ms | **PASS (IXSCAN)** |
| **Op 7b:** Source `"indeed"` | `FETCH` | `source_1` | 5,715 | 5,715 | 5,715 | 28 ms | **PASS (IXSCAN)** |

### 4.2 Aggregation Pipelines Index Support Analysis

| Pipeline Operation | Winning Stage | Index Utilized in Initial Stage | totalKeysExamined | totalDocsExamined | nReturned | executionTimeMs | Scan Type | Architectural Notes |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Op 8: Top Skills (Overall)** | `PROJECTION_DEFAULT` | None | 0 | 129,550 | 129,550 | 1393 ms | **COLLSCAN** | Unconstrained unwind scans collection across all postings. |
| **Op 8b: Top Skills (Filtered)** | `PROJECTION_DEFAULT` | `source_1` | 5,715 | 5,715 | 5,715 | 147 ms | **IXSCAN** | Initial `$match` pushes index scan on `source_1`. |
| **Op 9: Top Companies** | `GROUP` | `company.name_1` | 127,728 | 127,727 | 26,076 | 1206 ms | **IXSCAN** | Pushes index scan on `company.name_1` with bounds `[MinKey, null), (null, MaxKey]`. |
| **Op 10: Top Locations** | `GROUP` | `location.state_1_location.is_remote_1` | 117,541 | **0** | 51 | 771 ms | **COVERED_IXSCAN** | Covered index scan: 0 document fetches (totalDocsExamined = 0). |
| **Op 11: Salary Distributions** | `GROUP` | `salary.salary_bucket_1_salary.normalized_annual_1` | 41,775 | 41,774 | 6 | 414 ms | **IXSCAN** | Pushes index scan to group accumulator; document fields fetched for accumulators. |
| **Op 12: Platform Comparison** | `GROUP` | None | 0 | 129,550 | 2 | 268 ms | **COLLSCAN** | Market-wide summary scans all documents. |

### 4.3 Complete 20-Case Audit Coverage Summary

The query plan audit encompasses exactly **20 distinct, verified cases**:
- **14 Operational Query Variations:** Operations 1a through 7b, covering full-text, unindexed regex, compound location + tri-state remote, discrete salary bucket, unanchored continuous salary, combined bucket + continuous, multi-key `$all` and `$in` skill searches, company name, orphan company ID, experience level, and source filtering.
- **6 Aggregation Pipelines:** Operations 8 (unconstrained), 8b (filtered by source), 9 (top companies), 10 (top locations with covered index scan), 11 (salary distributions with conditional statistics), and 12 (cross-platform summary).

Every single case matches its expected plan stage and index name. Results are persisted to [data/processed/phase_5_query_plan_audit.json](file:///c:/ADBMS%20PROJECT/JobMarketDB/data/processed/phase_5_query_plan_audit.json).

> [!IMPORTANT]
> **Index Audit Conclusion (Priority 3 & 4):**
> The evidence confirms that targeted queries specifying indexed attributes (text search, state + remote, salary bucket, skills, company name, experience level, and source) execute through index scans (`IXSCAN`, `TEXT_INDEX`, or `COVERED_IXSCAN`). Queries that filter on non-prefix fields of compound indexes (`salary.normalized_annual` alone), perform unanchored regex searches on `title`, or filter by orphan `company.company_id` on the `jobs` collection execute via `COLLSCAN`. In strict compliance with safety rules, zero indexes were created, dropped, or modified.


---

## 5. Strict Provenance & Integrity Rule Adherence

Phase 5 adheres strictly to all Phase 2 modeling and Phase 3 transformation rules:

1. **Salary Rules:**
   - LinkedIn `salary.normalized_annual` is utilized only when source-supported.
   - Indeed `salary.normalized_annual` is verified to be `null` in 100% of Indeed documents (0 violations).
   - `salary.estimated_midpoint` is treated strictly as an analytical estimate and never presented as an observed continuous salary.
   - Missing salary values are preserved as `null` and **never converted to 0**.
2. **Role Category Rules:**
   - Preserves `role_category` as an embedded object containing `{ "value": ..., "status": ..., "derived_from": ... }`.
   - LinkedIn provenance: `status: "DERIVED / INFERRED"`, `derived_from: "title"`.
   - Indeed provenance: `status: "NORMALIZED"`, `derived_from: "Job_Type"`.
3. **Tri-State Remote Rule:**
   - Remote status is strictly tri-state: `True`, `False`, or `None` (`null`).
   - The 114,314 postings with unstated remote status are preserved as `None` and are **never silently converted to `False`**.
4. **Source Identity Rule:**
   - Both `source` (`"linkedin"` / `"indeed"`) and `source_job_id` are preserved and projected on 100% of returned query documents.
5. **Orphan Company Handling:**
   - Verified that job posting `3708903045` referencing authentic orphan LinkedIn company ID `23729571` is queryable by company ID (`count = 1`), with `company.name: null`.
   - Zero fabricated company records exist in the `companies` collection (`count = 0`).
6. **Skill Taxonomy Preservation:**
   - Authentic source-level skills are preserved without artificial mapping (35 LinkedIn disciplines, 464 Indeed tools).
   - Separate namespace reporting is available via `get_skills_by_platform()`.

---

## 6. Comprehensive Audit Findings Matrix

Every item investigated during the targeted Phase 5 audit pass is summarized below with its status (**PASS**, **CORRECTED**, or **REQUIRES REVIEW**):

| Audit Focus Area | Item Investigated | Status | Findings & Corrections Performed |
| :--- | :--- | :---: | :--- |
| **Priority 1: Salary Outlier** | LinkedIn `>160000` bucket average ($1,109,368.91) and 38 records > $1M | **CORRECTED** | Investigated all 38 records > $1M: 19 confirmed hourly-to-annual conversion errors; 10 recruiter/source entry errors (typos, bi-weekly, monthly); 1 other confirmed issue (secret shopper gig task); 8 unresolved cases (Kaiser student nurse/intern stipends). All 38 records and individual evidence verified and persisted in [data/processed/phase_5_salary_outlier_audit.json](file:///c:/ADBMS%20PROJECT/JobMarketDB/data/processed/phase_5_salary_outlier_audit.json). Calculations made explicitly conditional on `source == 'linkedin'`. Computed approximate median ($190,000.00) and threshold-adjusted mean ($213,464.73). Preserved unadjusted stored mean ($1,109,368.91) and verified Indeed continuous pay remains strictly null. Filter-independent methodology notes implemented. |
| **Priority 2: Skill Taxonomy & Distinct Postings** | Skill counting semantics and platform rankings in `analytics/aggregations.py` | **CORRECTED** | Verified empirically that 100% of 74,016 multi-skill postings have zero duplicate tokens. Added defensive `$setUnion` deduplication before `$unwind` to mathematically guarantee distinct posting counts. Implemented `get_skills_by_platform()` with separate denominators (LinkedIn: 123,835; Indeed: 5,715). Tested and verified role filtering, limit handling, and edge cases. Retained combined view only as caveated, population-weighted metric. |
| **Priority 3 & 4: Query Plans & Verification** | Reproducible executionStats audit & test suite coverage across 20 cases | **PASS** | Implemented standalone reproducible audit script `scripts/audit_phase_5_queries.py` producing `data/processed/phase_5_query_plan_audit.json`. Audited exactly 20 cases (14 operational queries + 6 aggregation pipelines) using recursive stage walking. Accurately documented `TEXT_INDEX`, `IXSCAN`, `COVERED_IXSCAN` (Op 10), and legitimate `COLLSCAN` operations (regex search, continuous salary without bucket prefix, orphan company ID on `jobs`, and unconstrained aggregations). Verified all 20 query-plan cases match expected stages. |
| **Integrity Invariant** | Total `jobs` collection document count (129,550) | **PASS** | Pre-execution: 129,550; Post-execution: 129,550. Delta = 0. Read-only invariant strictly enforced. |
| **Integrity Invariant** | Total `companies` collection document count (24,472) | **PASS** | Pre-execution: 24,472; Post-execution: 24,472. Delta = 0. Zero orphan company fabrication. |
| **Index Invariant** | Collection index definitions (`jobs`: 11, `companies`: 4) | **PASS** | Pre- and post-audit index definitions compared across names, keys, and options. 100% identical match. Zero indexes created, dropped, or modified. |
| **Provenance Invariant** | Indeed continuous salary is null | **PASS** | Verified 0 Indeed documents have non-null `salary.normalized_annual`. |
| **Provenance Invariant** | Tri-state remote representation | **PASS** | Verified 108,599 LinkedIn and 5,715 Indeed postings retain unstated remote as `None`, never converted to `False`. |

---

## 7. Read-Only Safety & Verification Confirmation

Before and immediately after executing all audit scripts, queries, and aggregations, database collection counts and index definitions were captured and audited:

### Collection Document Counts
| Collection | Pre-Audit Count | Post-Audit Count | Delta | Status |
| :--- | :--- | :--- | :---: | :--- |
| `jobs` | 129,550 | 129,550 | **0** | **VERIFIED UNCHANGED** |
| `companies` | 24,472 | 24,472 | **0** | **VERIFIED UNCHANGED** |

### Index Definition Invariants
| Collection | Pre-Audit Index Count | Post-Audit Index Count | Keys & Options Comparison | Status |
| :--- | :---: | :---: | :---: | :--- |
| `jobs` | 11 | 11 | **100% Identical** | **VERIFIED UNCHANGED** |
| `companies` | 4 | 4 | **100% Identical** | **VERIFIED UNCHANGED** |

The audit summary is persisted in [data/processed/phase_5_verification_summary.json](file:///c:/ADBMS%20PROJECT/JobMarketDB/data/processed/phase_5_verification_summary.json).

---

## 8. Phase Boundary & Completion Status

Phase 5 is **audited, corrected, and verified**.

Per project boundary rules:
- Streamlit UI development has **NOT** been started.
- Phase 6 dashboard views have **NOT** been built.
- Application code in `app.py` has **NOT** been modified.
- Work stops here pending review before proceeding to Phase 6.
