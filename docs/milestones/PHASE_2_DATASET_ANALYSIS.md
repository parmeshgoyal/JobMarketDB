# Phase 2: Dataset Analysis & Exploration Report

## 1. Executive Summary
This document presents the comprehensive exploratory data analysis of the two real-world datasets powering **JobMarketDB**:
1. **LinkedIn Job Postings (2023–2024)**: A broad-economy job dataset consisting of 11 relational CSV files covering 123,849 job postings across multiple industries, functions, and geographies.
2. **Indeed Job Dataset**: A focused dataset of 5,715 postings specifically targeting Data Science, Data Analytics, and Data Engineering roles across the United States.

Both datasets were inspected in their original forms without modification or data ingestion. All row counts, column counts, missing value statistics, and foreign key relationships presented below reflect direct profiling of the actual data files.

---

## 2. Dataset Inventory

### 2.1 File Catalog & Storage
The raw archives are located at `datasets/archive.zip` (LinkedIn) and `datasets/indeed_job_dataset.csv.zip` (Indeed) in the project root, with uncompressed working data verified in `archive/` and `indeed_job_dataset.csv/`.

| File Name | Relative Path | File Size | Row Count | Column Count | Primary Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **postings.csv** | `archive/postings.csv` | 492.90 MB | 123,849 | 31 | Primary LinkedIn Job Postings |
| **companies.csv** | `archive/companies/companies.csv` | 22.12 MB | 24,473 | 10 | LinkedIn Company Master Profiles |
| **company_industries.csv** | `archive/companies/company_industries.csv` | 0.75 MB | 24,375 | 2 | Company-to-Industry Mappings |
| **company_specialities.csv**| `archive/companies/company_specialities.csv`| 4.23 MB | 169,387 | 2 | Company Specialties & Keywords |
| **employee_counts.csv** | `archive/companies/employee_counts.csv` | 1.00 MB | 35,787 | 4 | Company Headcount & Followers over Time |
| **benefits.csv** | `archive/jobs/benefits.csv` | 1.84 MB | 67,943 | 3 | Job-level Benefits & Inferred Flags |
| **job_industries.csv** | `archive/jobs/job_industries.csv` | 2.39 MB | 164,808 | 2 | Job-to-Industry ID Bridge Table |
| **job_skills.csv** | `archive/jobs/job_skills.csv` | 3.34 MB | 213,768 | 2 | Job-to-Skill Abbreviation Bridge Table |
| **salaries.csv** | `archive/jobs/salaries.csv` | 2.15 MB | 40,785 | 8 | Granular Job Compensation Data |
| **industries.csv** | `archive/mappings/industries.csv` | 0.01 MB | 422 | 2 | Industry ID to Industry Name Lookup |
| **skills.csv** | `archive/mappings/skills.csv` | 0.001 MB | 35 | 2 | Skill Code to Skill Name Lookup |
| **indeed_job_dataset.csv** | `indeed_job_dataset.csv/...` | 18.14 MB | 5,715 | 43 | Indeed Specialized Data Roles Dataset |

---

## 3. LinkedIn Dataset Deep-Dive

### 3.1 Primary Table: `postings.csv`
- **Total Records:** 123,849 rows.
- **Uniqueness:** `job_id` is unique across all 123,849 rows (0 duplicates).
- **Date Range:** `original_listed_time` spans from **December 5, 2023** to **April 20, 2024**.

#### Column Profiling & Nullability
| Column Name | Data Type | Null Count | Null % | Distinct Values | Provenance & Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `job_id` | `int64` | 0 | 0.0% | 123,849 | **SOURCE:** Primary Key identifier in source |
| `company_name` | `str` | 1,719 | 1.4% | 24,413 | **SOURCE:** Employer display name |
| `title` | `str` | 0 | 0.0% | 46,128 | **SOURCE:** Job title |
| `description` | `str` | 7 | 0.0% | 114,874 | **SOURCE:** Full job description text (HTML/Markdown) |
| `max_salary` | `float64` | 94,056 | 75.9% | 4,891 | **SOURCE:** Upper bound of stated compensation |
| `pay_period` | `str` | 87,776 | 70.9% | 5 | **SOURCE:** `YEARLY`, `HOURLY`, `MONTHLY`, `WEEKLY`, `BIWEEKLY` |
| `location` | `str` | 0 | 0.0% | 8,526 | **SOURCE:** Geographic text (`New York, NY`, `United States`, `Chicago, IL`) |
| `company_id` | `float64` | 1,717 | 1.4% | 24,474 | **SOURCE:** Foreign key to `companies.csv` |
| `views` | `float64` | 1,689 | 1.4% | 1,778 | **SOURCE:** Number of times posting was viewed |
| `med_salary` | `float64` | 117,569 | 94.9% | 1,326 | **SOURCE:** Median salary (rarely populated) |
| `min_salary` | `float64` | 94,056 | 75.9% | 4,249 | **SOURCE:** Lower bound of compensation |
| `formatted_work_type` | `str` | 0 | 0.0% | 7 | **SOURCE:** Employment contract type: `Full-time`, `Contract`, `Part-time`, `Temporary`, `Internship`, `Volunteer`, `Other` |
| `applies` | `float64` | 100,529 | 81.2% | 884 | **SOURCE:** Number of applications submitted |
| `original_listed_time`| `float64` | 0 | 0.0% | 123,838 | **SOURCE:** Epoch milliseconds of authentic publication |
| `remote_allowed` | `float64` | 108,603 | 87.7% | 1 | **SOURCE:** `1.0` when remote work is allowed; `NaN` otherwise |
| `job_posting_url` | `str` | 0 | 0.0% | 123,849 | **SOURCE:** Direct LinkedIn posting URL |
| `application_url` | `str` | 36,665 | 29.6% | 76,469 | **SOURCE:** External company application portal URL |
| `application_type` | `str` | 0 | 0.0% | 2 | **SOURCE:** `OffsiteApply` (87,184) vs `ComplexOnsiteApply` (36,665) |
| `expiry` | `float64` | 0 | 0.0% | 123,849 | **SOURCE:** Epoch milliseconds of posting expiration |
| `closed_time` | `float64` | 122,776 | 99.1% | 1,073 | **SOURCE:** Epoch milliseconds when closed |
| `formatted_experience_level` | `str` | 29,409 | 23.7% | 6 | **SOURCE (OBSERVED):** `Mid-Senior level` (41,489), `Entry level` (36,708), `Associate` (9,826), `Director` (3,746), `Internship` (1,449), `Executive` (1,222) |
| `skills_desc` | `str` | 121,410 | 98.0% | 1,770 | **SOURCE:** Free-text skill description summary |
| `listed_time` | `float64` | 0 | 0.0% | 123,849 | **SOURCE:** Epoch milliseconds when listed |
| `posting_domain` | `str` | 39,968 | 32.3% | 7,869 | **SOURCE:** Domain of application redirect |
| `sponsored` | `int64` | 0 | 0.0% | 2 | **SOURCE:** `0` (unpaid) or `1` (sponsored) |
| `work_type` | `str` | 0 | 0.0% | 7 | **SOURCE:** Uppercase equivalent of `formatted_work_type` |
| `currency` | `str` | 87,776 | 70.9% | 6 | **SOURCE:** Currency code (`USD`, `CAD`, `EUR`, `GBP`, `AUD`, `SGD`) |
| `compensation_type`| `str` | 87,776 | 70.9% | 1 | **SOURCE:** `BASE_SALARY` |
| `normalized_salary`| `float64` | 87,776 | 70.9% | 7,163 | **SOURCE:** Annualized compensation in USD computed by LinkedIn |
| `zip_code` | `str` | 20,872 | 16.9% | 8,247 | **SOURCE:** Postal code of posting location |
| `fips` | `float64` | 27,415 | 22.1% | 1,816 | **SOURCE:** Federal county census code |

---

### 3.2 LinkedIn Relational Tables & Foreign Keys

#### A. Company Data (`companies.csv`, `company_industries.csv`, `company_specialities.csv`, `employee_counts.csv`)
- **`companies.csv` (24,473 rows):**
  - Primary key: `company_id`.
  - Columns: `name`, `description`, `company_size` (numeric 1.0–7.0 scale), `state`, `country`, `city`, `zip_code`, `address`, `url`.
  - Relationship to `postings.csv`: 24,474 distinct non-null `company_id`s exist in `postings.csv`. **24,473 match `companies.csv`**; exactly 1 company ID in postings has no record in `companies.csv`.
- **`company_industries.csv` (24,375 rows):** Maps companies to 144 industry strings.
- **`company_specialities.csv` (169,387 rows):** 82,960 distinct keywords describing company offerings.
- **`employee_counts.csv` (35,787 rows):** Historical snapshots of `employee_count` and `follower_count` with `time_recorded`.

#### B. Salary Data (`jobs/salaries.csv`)
- **40,785 rows:**
  - Foreign key: `job_id`.
  - Columns: `salary_id`, `job_id`, `max_salary`, `med_salary`, `min_salary`, `pay_period`, `currency`, `compensation_type`.
  - **Integrity Discovery:** Exactly 36,073 records correspond to jobs in `postings.csv` (100% of postings with salary data). The remaining **4,712 rows are orphans** from older/expired jobs no longer in `postings.csv`.
  - **Redundancy Discovery:** All salary values in `salaries.csv` for active jobs are already mirrored directly in `postings.csv`, while `postings.csv` includes the additional pre-computed `normalized_salary` field.

#### C. Job Skills & Mapping (`jobs/job_skills.csv` and `mappings/skills.csv`)
- **`job_skills.csv` (213,768 rows):**
  - Foreign key: `job_id` (126,807 unique jobs; **122,096 match `postings.csv`** with 4,711 orphan job IDs).
  - Column: `skill_abr` (35 distinct skill codes).
- **`mappings/skills.csv` (35 rows):**
  - Maps `skill_abr` to full descriptive category names: `IT` -> Information Technology, `ENG` -> Engineering, `ANLS` -> Analyst, `MGMT` -> Management, `FIN` -> Finance, `MRKT` -> Marketing, `SALE` -> Sales, `DSGN` -> Design, etc.
  - **Fundamental Nature:** LinkedIn "skills" represent broad functional job categories rather than specific technical tools.

#### D. Job Industries & Mapping (`jobs/job_industries.csv` and `mappings/industries.csv`)
- **`job_industries.csv` (164,808 rows):**
  - Foreign key: `job_id` (127,125 unique jobs; **122,413 match `postings.csv`** with 4,712 orphan job IDs).
  - Column: `industry_id` (422 unique integer IDs).
- **`mappings/industries.csv` (422 rows):**
  - Maps `industry_id` to `industry_name` (e.g., `Hospitals and Health Care`, `Retail`, `IT Services and IT Consulting`, `Software Development`).

#### E. Benefits Data (`jobs/benefits.csv`)
- **67,943 rows:**
  - Foreign key: `job_id` (30,023 unique jobs; **28,735 match `postings.csv`** with 1,288 orphan job IDs).
  - 12 distinct benefit types: `401(k)` (24,231), `Medical insurance` (9,873), `Vision insurance` (9,309), `Disability insurance` (7,930), `Dental insurance` (6,868), `Tuition assistance` (2,614), `Commuter benefits` (2,226), `Paid maternity leave` (1,808), `Paid paternity leave` (1,540), `Pension plan` (906), `Student loan assistance` (365), `Child care support` (273).

---

## 4. Indeed Dataset Deep-Dive

### 4.1 Overview & Structure
- **File:** `indeed_job_dataset.csv`
- **Total Records:** 5,715 rows.
- **Total Columns:** 43 columns.
- **Focus:** Specialized data profession postings across 3 core roles:
  - `data_scientist`: 2,543 postings (44.5%)
  - `data_analyst`: 1,793 postings (31.4%)
  - `data_engineer`: 1,379 postings (24.1%)

### 4.2 Column Profiling & Nullability
| Column Name | Type | Null Count | Null % | Distinct Values | Provenance & Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Unnamed: 0` | `int64` | 0 | 0.0% | 5,715 | **SOURCE:** Dataset sequential index (0 to 5,714) |
| `Job_Title` | `str` | 0 | 0.0% | 2,314 | **SOURCE:** Stated job title |
| `Link` | `str` | 0 | 0.0% | 5,715 | **SOURCE:** Unique Indeed redirect URL containing `jk=<hash>` |
| `Queried_Salary` | `str` | 0 | 0.0% | 6 | **SOURCE:** Discrete query salary bands: `<80000`, `80000-99999`, `100000-119999`, `120000-139999`, `140000-159999`, `>160000` |
| `Job_Type` | `str` | 0 | 0.0% | 3 | **SOURCE:** Target professional discipline: `data_scientist`, `data_analyst`, `data_engineer`. (NOT an employment contract type column). |
| `Skill` | `str` | 232 | 4.1% | 4,024 | **SOURCE:** Stringified Python list of specific tools (`"['Python', 'SQL', 'Tableau']"`) |
| `No_of_Skills` | `int64` | 0 | 0.0% | 21 | **SOURCE:** Integer count of extracted skills (0 to 20) |
| `Company` | `str` | 104 | 1.8% | 2,231 | **SOURCE:** Employer name |
| `No_of_Reviews` | `float64`| 962 | 16.8% | 754 | **SOURCE:** Total employee review count on Indeed |
| `No_of_Stars` | `float64`| 962 | 16.8% | 54 | **SOURCE:** Average star rating (1.3 to 5.0 scale) |
| `Date_Since_Posted` | `float64`| 104 | 1.8% | 30 | **SOURCE:** Relative age of posting in days (1.0 to 30.0 days; 2,954 are `30.0+` days) |
| `Description` | `str` | 302 | 5.3% | 4,802 | **SOURCE:** Full textual job description |
| `Location` | `str` | 252 | 4.4% | 51 | **SOURCE:** US State abbreviations (`CA`, `NY`, `VA`, `TX`, etc.) |
| `Company_Revenue` | `str` | 3,698 | 64.7% | 4 | **SOURCE:** Categorical revenue bracket (`More than $10B (USD)`, etc.) |
| `Company_Employees`| `str` | 2,516 | 44.0% | 2 | **SOURCE:** Size bracket: `10,000+` vs `Less than 10,000` |
| `Company_Industry` | `str` | 1,889 | 33.1% | 33 | **SOURCE:** Industry category |

### 4.3 Provenance Realities in Indeed
1. **Absence of Native Job ID:** Indeed has no native `job_id` column. The identifier is extracted from the URL query parameter `jk=`. In the MongoDB model, it is recorded as `source_job_id` with metadata documenting its URL provenance.
2. **Absence of Employment Contract Type:** The Indeed dataset has **no column** for employment contract type (Full-time, Part-time, Contract). The column `Job_Type` represents the queried role domain (`data_scientist`, `data_analyst`, `data_engineer`). We do NOT invent an employment type.
3. **Absence of Publication Date:** Indeed provides only relative days (`Date_Since_Posted`). It contains no native publication timestamp. Any calculated date is explicitly marked as DERIVED / ESTIMATED.

---

## 5. Data Quality, Integrity Principles & Provenance Rules

| Dimension | LinkedIn Dataset Reality | Indeed Dataset Reality | Provenance Tier & Architectural Rule |
| :--- | :--- | :--- | :--- |
| **Source Skill Granularity** | 35 broad functional categories (`IT`, `Analyst`, `Finance`, `Engineering`). | Granular technical software tools (`Python`, `SQL`, `Machine Learning`, `AWS`, `Spark`). | **SOURCE:** Preserve authentic source skills in `skills: [...]`. Do NOT assert false mappings (e.g., claiming LinkedIn `"IT"` equals Indeed `"Python"`). Any unified taxonomy is an analytical layer. |
| **Employment Type** | Stated contract type in `formatted_work_type` (`Full-time`, `Contract`, etc.). | **No employment contract type column exists.** (`Job_Type` is role domain). | **SOURCE vs NORMALIZED:** LinkedIn preserves `source_employment_type`. Indeed stores `null` for both source and normalized employment type; never silently invented. |
| **Role Category** | Broad industry titles (`Sales Manager`, `Nurse`, `Data Analyst`). | Query discipline in `Job_Type` (`data_scientist`, `data_analyst`, `data_engineer`). | **DERIVED / NORMALIZED:** `role_category` is strictly an application-level field created for cross-dataset analysis. Inferred from title (LinkedIn) or normalized from discipline (Indeed). NOT a native column. |
| **Publication Date** | Epoch milliseconds timestamp in `original_listed_time`. | Relative float in days (`Date_Since_Posted`). No native timestamp. | **SOURCE vs DERIVED / ESTIMATED:** LinkedIn stores native `posted_date`. Indeed stores `posted_date: null` and calculates an `estimated_posted_date`. No fake publication timestamps. |
| **Experience Level** | Explicit source column `formatted_experience_level` with 6 categories (23.7% null). | **No native experience-level column.** | **OBSERVED vs INFERRED:** LinkedIn marked `status: "OBSERVED"`. Indeed marked `status: "NOT_AVAILABLE"`. Inferred values are never converted into authoritative source data. |
| **Salary Range vs Exact Values** | Stated continuous salaries (min, max, pay period) and pre-calculated `normalized_salary` (annualized USD). 70.9% missing. | Stated in 6 discrete query bands (`<80000`, `80000-99999`, etc.). 0% missing in source query. | **Never convert range to exact:** An Indeed bucket (`100000-119999`) is NEVER stored as an exact salary. If a midpoint is calculated, store it in `salary.estimated_midpoint` as a DERIVED estimate. |
| **Missing Salary Handling** | 70.9% of postings lack salary fields. | N/A (all have `Queried_Salary`). | **Never default missing salary to 0:** Missing salaries must remain `null` to avoid distorting analytical averages and filters. |
| **Remote Work Status** | `remote_allowed` has `1.0` (confirmed remote) or `NaN`. | No dedicated remote boolean flag in source. | **Tri-state boolean:** Use `is_remote: true` (confirmed remote), `is_remote: false` (confirmed non-remote), and `is_remote: null` (unknown). Do NOT default unknown Indeed postings to `false`. |

---

## 6. Cross-Dataset Compatibility Matrix

| Business Concept | LinkedIn Source Field(s) | Indeed Source Field(s) | Compatibility Status | Provenance & Harmonization Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Job Title** | `title` | `Job_Title` | **Directly Compatible** | **SOURCE:** Preserved as clean text. |
| **Company Name** | `company_name` / `companies.name` | `Company` | **Directly Compatible** | **SOURCE:** 599 companies overlap directly. Clean legal entity suffixes (`Inc.`, `LLC`). |
| **Job Description** | `description` | `Description` | **Directly Compatible** | **SOURCE:** Preserved as clean text. |
| **Location (State)** | `location`, `companies.state` | `Location` | **Normalizable** | **NORMALIZED:** Standardized 2-letter uppercase US state code (`TX`, `CA`, `NY`). |
| **Remote Work** | `remote_allowed` (`1.0` or `NaN`) | *(None)* | **Tri-State Boolean** | **SOURCE / UNKNOWN:** Map `1.0` to `true`; map missing/unknown to `null` (never default to `false`). |
| **Employment Type** | `formatted_work_type` | *(None)* | **Incompatible** | **SOURCE vs NULL:** LinkedIn stores authentic work type; Indeed stores `null` (never invented). |
| **Role Category** | Inferred from `title` | Normalized from `Job_Type` | **Derived Common Field** | **DERIVED / NORMALIZED:** Application-level classification for cross-dataset analysis. |
| **Publication Date** | `original_listed_time` | `Date_Since_Posted` (relative) | **Incompatible** | **SOURCE vs ESTIMATED:** LinkedIn stores authentic `posted_date`; Indeed stores `estimated_posted_date`. |
| **Salary Bands** | Stated pay period & min/max; `normalized_salary` | `Queried_Salary` (discrete bands) | **Transformable** | **NORMALIZED / ESTIMATED:** Map both to `salary.salary_bucket`; store `estimated_midpoint` for Indeed. |
| **Skills** | `job_skills.csv` + `mappings/skills.csv` (Functional domains) | `Skill` + 10 binary flags (Specific software tools) | **Source-Preserved** | **SOURCE:** Preserve authentic source skills in `skills: [...]`. Do NOT assert false taxonomical equivalencies. |
| **Experience Level** | `formatted_experience_level` | *(None)* | **Distinguished** | **OBSERVED vs NOT AVAILABLE:** Tag LinkedIn as `"OBSERVED"`; tag Indeed as `"NOT_AVAILABLE"`. |
| **Application URL** | `job_posting_url`, `application_url` | `Link` | **Directly Compatible** | **SOURCE:** Map to unified `job_url` field. |

---

## 7. Conclusions for Data Modeling
1. **Provenance Integrity:** The MongoDB schema explicitly categorizes all data into SOURCE, NORMALIZED, and DERIVED / INFERRED tiers, preventing data pollution and false claims.
2. **Authentic Skills Preserved:** Broad functional categories from LinkedIn and granular technical tools from Indeed are preserved as genuine source data without false equivalencies.
3. **Optimized for MongoDB:** The relational graph of LinkedIn flattens into an embedded document model (`jobs` collection) with an Extended Reference snapshot to `companies`, eliminating runtime joins for search and analytics.
