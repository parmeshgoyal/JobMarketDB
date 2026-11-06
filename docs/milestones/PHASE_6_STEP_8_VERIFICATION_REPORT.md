# JobMarketDB — Phase 6 Step 8 Verification Report
## Cross-Platform Market Comparison (LinkedIn vs Indeed)

**Date:** 2026-11-03  
**Target Module:** `pages/5_Platform_Comparison.py` (Module 5)  
**Database Deployment:** Local MongoDB Community Server v9.0.4 exclusively (`mongodb://localhost:27017/jobmarketdb`)  
**Status:** **RECONCILED, AUDITED, REGRESSION-VERIFIED & AWAITING APPROVAL**  
**Stop Gate:** **Enforced — Step 9 (CRUD Demo) has NOT been started. Awaiting explicit user approval.**

---

## 1. Executive Summary

Phase 6 Step 8 delivers a rigorous, empirical, and publication-grade **Cross-Platform Market Comparison** dashboard, followed by a targeted audit and reconciliation of all data points against local MongoDB Community Server ground truth (`jobmarketdb`). The dashboard interfaces exclusively through the verified service and aggregation layer.

### Key Deliverables & Safeguards
1. **Salary Ground-Truth Reconciliation:** Established absolute database ground truth for compensation metrics on both platforms. Reconciled Indeed derived midpoint mean to **$116,501.31** (median **$110,000.00**, range **$70,000.00–$175,000.00**, $n=5,715$) and LinkedIn threshold-adjusted annualized mean to **$95,515.00** (median **$81,375.00**, range **$1.00–$960,000.00**, $n=36,021$ with 38 outliers $> \$1,000,000$). Stale draft figures in the initial Step 8 report were audited and corrected.
2. **Median Rank Mathematical Clarification:** Formally documented that with an odd population of 5,715 Indeed postings, the median is the **2,858th sorted observation in one-based ranking**, corresponding to **zero-based index 2,857**. Verified that rank 2,858 falls within the cumulative 1,742–3,135 rank interval of the $110,000 band, confirming the median of strictly **$110,000.00**.
3. **Indeed SQL Skill Count Reconciliation:** Verified through direct collection query, regex, and `$unwind` aggregations that exactly **3,104 Indeed postings contain the skill "SQL" (54.31%)**. The draft figure of 3,238 (56.66%) was an ungrounded prototype placeholder; both Step 5 and Step 8 use the verified count of 3,104.
4. **Platform Overview Visualization Fixed:** Root-caused the blank chart area in `06_1_platform_overview_kpis.png` to a browser automation capture-timing artifact where Playwright snapped the viewport before Streamlit's initial multi-collection aggregation finished. Implemented strict synchronization in `scripts/verify_step_8_browser.py`, restarted Streamlit cleanly, and verified the dual-bar posting volume chart (LinkedIn: 123,835; Indeed: 5,715) renders completely.
5. **Comprehensive Regression Battery (Steps 1–8 & Phase 5):** Successfully executed the full regression battery covering all implemented Phase 6 steps (Steps 1, 2, 3, 4, 5, 6, 7, 8) and Phase 5 verification: **143 unit/regression tests executed with 100% pass rate (0 failures)**, alongside all **20 executionStats query plan audits** and **52 input validation guardrails**.
6. **Platform Overview & Provenance Fidelity:** Accurately reports posting volume proportions: LinkedIn at **123,835 postings (95.59%)** and Indeed at **5,715 postings (4.41%)** across **129,550 total canonical jobs**.
7. **Comprehensive Field Completeness Audit:** Directly audits **14 schema attributes** across both platforms, documenting population counts, missing-value rates, and upstream scraper schema gaps.
8. **Workplace Modality (Tri-State Model):** Preserves the strict tri-state schema for `location.is_remote` (`True` = Explicitly Remote, `False` = Explicitly On-Site, `Null` = Unspecified/Non-Remote). Ground truth verifies 15,236 LinkedIn remote postings (12.30%) and zero boolean `False` records in the database, with Indeed at 100% `Null`.
9. **Mandatory Salary Separation:** Strictly separates continuous annualized compensation from discrete derived search-band midpoints. Prohibits merged distributions and direct continuous comparison, providing standardized 6-tier salary bucket comparison instead.
10. **Skills Taxonomy Boundary Isolation:** Enforces strict namespace separation between LinkedIn's **35 broad functional disciplines** (e.g., Information Technology: 20.39%) and Indeed's **464 granular technical tools** (e.g., Python: 58.18%, SQL: 54.31%). Prevents false category equivalence.
11. **Indeed Experience Level Disclosure:** Explicitly discloses that Indeed contains **0.00% experience annotations** (100% missing/null), preventing fabricated or imputed seniority metrics. Seniority analytics remain isolated to LinkedIn's 94,439 classified records (76.26%).
12. **Cross-Platform Employer Intelligence:** Discovers the exact intersection of **570 distinct shared employers** recruiting on both platforms (representing 25.55% of Indeed employers and 2.33% of LinkedIn employers), led by Capital One (550 total: 496 LinkedIn + 54 Indeed).

---

## 2. Salary and Skill Reconciliation & MongoDB Ground Truth

Direct read-only aggregations were executed against local MongoDB Community Server (`mongodb://localhost:27017/jobmarketdb`).

### 2.1 Indeed Salary Midpoint Reconciliation

| Metric | Step 7 Audit | Step 8 Initial Draft | MongoDB Ground Truth | Status / Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Midpoint** | $116,501.31 | $119,419.07 | **$116,501.31** | **Step 7 Confirmed Authentic.** Step 8 draft used mock scratch prototype. |
| **Median Midpoint** | $110,000.00 | $118,500.00 | **$110,000.00** | **Step 7 Confirmed Authentic.** Step 8 draft was inaccurate. |
| **Midpoint Range** | $70,000–$175,000 | $69,500–$169,500 | **$70,000.00–$175,000.00** | **Step 7 Confirmed Authentic.** Exact range is $70k to $175k. |
| **Non-Null Observations** | 5,715 | 5,715 | **5,715** (100.0%) | Matches 100% across all audits. |
| **Missing / Null Count** | 0 | 0 | **0** (0.0%) | Zero missing values in Indeed estimated midpoint. |
| **Discrete Query Bands** | 6 intervals | 6 intervals | **6 discrete midpoints** | $70k (788), $90k (953), $110k (1,394), $130k (1,292), $150k (873), $175k (415). |

#### Authoritative MongoDB Aggregation Pipeline
```javascript
db.jobs.aggregate([
  { $match: { source: "indeed", "salary.estimated_midpoint": { $ne: null } } },
  {
    $group: {
      _id: null,
      count: { $sum: 1 },
      avg_midpoint: { $avg: "$salary.estimated_midpoint" },
      min_midpoint: { $min: "$salary.estimated_midpoint" },
      max_midpoint: { $max: "$salary.estimated_midpoint" },
      sum_midpoint: { $sum: "$salary.estimated_midpoint" }
    }
  }
])
```
**Execution Output:**
- `count`: 5,715
- `avg_midpoint`: 116501.312335958 $\rightarrow$ **$116,501.31**
- `min_midpoint`: 70000.0 $\rightarrow$ **$70,000.00**
- `max_midpoint`: 175000.0 $\rightarrow$ **$175,000.00**
- `sum_midpoint`: 665,805,000.0 $\rightarrow$ **$665,805,000.00**

#### Exact Median Rank Verification
The Indeed midpoint population contains an odd count of $N = 5,715$ records. By standard statistical definition, the median is the value at:
$$\text{Rank}_{\text{1-based}} = \frac{N + 1}{2} = \frac{5,715 + 1}{2} = 2,858$$
$$\text{Index}_{\text{0-based}} = 5,715 // 2 = 2,857$$

Across the sorted discrete midpoints:
- **Band $70,000:** 788 records (1-based ranks 1 to 788; 0-based indices 0 to 787)
- **Band $90,000:** 953 records (1-based ranks 789 to 1,741; 0-based indices 788 to 1,740)
- **Band $110,000:** 1,394 records (1-based ranks 1,742 to 3,135; 0-based indices 1,741 to 3,134)
- **Band $130,000:** 1,292 records (1-based ranks 3,136 to 4,427; 0-based indices 3,135 to 4,426)
- **Band $150,000:** 873 records (1-based ranks 4,428 to 5,300; 0-based indices 4,427 to 5,299)
- **Band $175,000:** 415 records (1-based ranks 5,301 to 5,715; 0-based indices 5,300 to 5,714)

Rank 2,858 (zero-based index 2,857) falls squarely within the cumulative 1,742–3,135 rank interval of the $110,000 band ($1,742 \le 2,858 \le 3,135$). Sorted values at indices 2,857 and 2,858 in the database are both identically $110,000.00, establishing the authentic median as strictly **$110,000.00**.

---

### 2.2 LinkedIn Adjusted Compensation Mean & Range Reconciliation

| Metric | Step 7 Audit | Step 8 Initial Draft | MongoDB Ground Truth | Status / Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **Adjusted Mean** | $95,515.17 | $95,515.34 | **$95,515.00** | **Exact Mathematical Truth.** ($95,515.001451). |
| **Adjusted Median** | $81,375.00 | $81,375.00 | **$81,375.00** | Matches 100% across all audits. |
| **Total Non-Null Postings** | 36,059 | 36,059 | **36,059** (29.12%) | Matches 100% across all audits. |
| **Missing / Null Postings** | 87,776 | 87,776 | **87,776** (70.88%) | Matches 100% across all audits. |
| **Threshold Population** | 36,021 ($\le \$1M$) | 36,021 ($\le \$1M$) | **36,021** | Population meeting threshold $\le \$1,000,000$. |
| **Excluded Outliers** | 38 | 38 | **38** ($> \$1,000,000$) | Matches 100% across all audits. |
| **Adjusted Range** | $14,976–$1,000,000 (Draft) | $14,976–$1,000,000 (Draft) | **$1.00–$960,000.00** | Ground truth min is $1.00; max is $960,000.00 across all 36,021 adjusted records. |

#### Authoritative MongoDB Aggregation Pipeline
```javascript
db.jobs.aggregate([
  {
    $match: {
      source: "linkedin",
      "salary.normalized_annual": { $ne: null, $lte: 1000000 }
    }
  },
  {
    $group: {
      _id: null,
      count: { $sum: 1 },
      avg_adjusted: { $avg: "$salary.normalized_annual" },
      min_val: { $min: "$salary.normalized_annual" },
      max_val: { $max: "$salary.normalized_annual" }
    }
  }
])
```
**Execution Output:**
- `count`: 36,021
- `avg_adjusted`: 95515.00145123678 $\rightarrow$ **$95,515.00** (Decimal sum: 3,440,545,867.275 / 36,021 = 95515.001451...)
- `min_val`: 1.0 $\rightarrow$ **$1.00**
- `max_val`: 960000.0 $\rightarrow$ **$960,000.00**
- `median`: 81375.0 $\rightarrow$ **$81,375.00**

#### Investigation of Alternative Range ($14,976–$1,000,000)
Early prototype scratch files referenced an ungrounded range floor of $14,976 based on a theoretical minimum wage assumption ($7.20/hr $\times$ 2,080 annual hours = $14,976). However, an exhaustive audit of the actual MongoDB database revealed that **440 postings contain normalized annual compensation $< \$15,000** (including symbolic $1.00 and $1.50 listings and part-time hourly listings). Neither the service layer nor the dashboard applies any artificial minimum wage floor. The true database-grounded range across all 36,021 adjusted records ($\le \$1,000,000$) is strictly **$1.00 – $960,000.00**.

---

### 2.3 Indeed SQL Skill Count Reconciliation

| Metric | Step 5 Skills Audit | Step 8 Initial Draft | MongoDB Ground Truth | Status / Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **Indeed Postings with SQL** | 3,104 | 3,238 | **3,104** | **Step 5 Confirmed Ground Truth.** Step 8 draft was an ungrounded prototype placeholder. |
| **Demand Percentage** | 54.31% | 56.66% | **54.31%** | Evaluated against all 5,715 Indeed postings ($3,104 / 5,715 = 54.3132\%$). |
| **Counting Methodology** | Distinct Postings | Distinct Postings | **Distinct Postings** | Evaluated via exact match `skills: "SQL"`, case-insensitive regex `^sql$`, and `$unwind`. |

#### Authoritative MongoDB Query
```javascript
db.jobs.countDocuments({ source: "indeed", skills: "SQL" })
// Returns: 3,104
```
**Investigation Findings:**
- Both `db.jobs.countDocuments({ source: "indeed", skills: "SQL" })` and an `$unwind` on `skills` with `$match: { skills: "SQL" }` yield identically **3,104 postings**.
- Because each distinct skill token appears at most once per posting's `skills` array, the distinct posting count equals the unwound token count.
- Case-insensitive regex (`^sql$`) also returns exactly 3,104, confirming zero case-normalization variance.
- Related database tools (NoSQL: 607, Microsoft SQL Server: 476, PostgreSQL: 289, MySQL: 283, T-SQL: 80, PL/SQL: 64, SQLite: 2) exist as separate taxonomy entries in Indeed's 464 technical tools.
- The initial Step 8 draft figure of 3,238 postings (56.66%) was an ungrounded prototype estimate from early scratch scripts. Both the Skills Analytics page (Step 5) and the Platform Comparison dashboard (Step 8) use the exact verified MongoDB ground truth of **3,104 postings (54.31%)**.

---

## 3. Platform Overview Visualization Audit & Resolution

### 3.1 Problem Description
In the previously captured screenshot `06_1_platform_overview_kpis.png`, the overview visualization area appeared completely blank below the section header `1. Executive Platform Overview`.

### 3.2 Root-Cause Investigation
1. **Empty Aggregation Result Check:** Ruled out. Direct CLI execution of `service.compare_platforms()` and `create_platform_comparison_chart(data, metric="volume")` verified that the aggregation returned LinkedIn: 123,835 and Indeed: 5,715, generating a valid two-bar Plotly figure (`Figure.data` populated with 2 bars).
2. **Plotly Rendering Check:** Ruled out. The chart builder `create_platform_comparison_chart` correctly uses `THEME` tokens and standard Plotly bar traces.
3. **Capture Timing Identification:** **Confirmed Root Cause.** In `scripts/verify_step_8_browser.py`, `wait_for_streamlit()` used `page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden")` wrapped in a broad `try/except`. In modern Streamlit, this selector threw a silent timeout and fell back to `time.sleep(2.0)`. However, the initial page load executes multi-collection aggregations (`get_platform_field_completeness` across 129,550 documents), which takes ~3.5 seconds on a cold run. Playwright snapped `06_1` at $t=2.0\text{s}$ while Streamlit was still executing (evidenced by the "Stop" button in the upper right corner of the stale screenshot).

### 3.3 Resolution & Verification
1. **Automated Wait Enhancement:** Updated `wait_for_streamlit()` in `scripts/verify_step_8_browser.py` to explicitly wait for `text=Stop` to be detached (`state="detached"`) and for `.js-plotly-plot` to be visible before capturing screenshots.
2. **Scroll Offset Calibration:** Measured exact DOM bounding boxes for all 8 section headings (`h3`) and calibrated `scroll_to_element` offsets to eliminate vertical overlap.
3. **Clean Daemon Restart:** Killed the prior Streamlit server process and launched a clean daemon on port 8501.
4. **Visual Confirmation:** Recaptured `06_1_platform_overview_kpis.png`. The dual-bar chart titled "Posting Volume by Platform" visibly renders with complete styling, showing LinkedIn (123,835) and Indeed (5,715) alongside the 4 KPI cards and Platform Composition Ratio card.

---

## 4. Comprehensive Regression Test Summary

All regression test suites across Phase 6 (Steps 1 to 8) and Phase 5 verification were executed against the local database:

| Suite / Script Name | Target Module / Subsystem | Tests Run | Result | Duration | Notes / Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scripts/test_phase_6_step_1.py` | Step 1: Home Overview & Skeleton | 15 | **15 PASS, 0 FAIL** | 38.25s | Verified KPI cards, MongoDB connectivity, schema invariants. |
| `scripts/test_phase_6_step_2.py` | Step 2: Multi-Page Navigation | 12 | **12 PASS, 0 FAIL** | 1.01s | Verified all 6 page routes, sidebar styling, navigation links. |
| `scripts/test_phase_6_step_3.py` | Step 3: Shared UI & Design System | 6 | **6 PASS, 0 FAIL** | 1.89s | Verified CSS injection, card styling tokens, error boundaries. |
| `scripts/test_phase_6_step_4.py` | Step 4: Job Search & Filtering | 28 | **28 PASS, 0 FAIL** | 22.51s | Verified compound filters, pagination, index-backed search. |
| `scripts/test_phase_6_step_5.py` | Step 5: Skills Analytics | 21 | **21 PASS, 0 FAIL** | 17.83s | Verified skills rankings, role filtering, platform taxonomy. |
| `scripts/test_phase_6_step_6.py` | Step 6: Company & Geography | 21 | **21 PASS, 0 FAIL** | 13.54s | Verified employer rankings, Capital One counts, state maps. |
| `scripts/test_phase_6_step_7.py` | Step 7: Salary Analytics | 30 | **30 PASS, 0 FAIL** | 23.51s | Verified outlier audit, threshold adjustment, experience stats. |
| `scripts/test_phase_6_step_8.py` | Step 8: Platform Comparison | 10 | **10 PASS, 0 FAIL** | 18.92s | Verified completeness, modality, salary separation, overlap. |
| `scripts/verify_phase_5.py` | Phase 5: Operations & Query Plans | 20 plans, 52 guards | **ALL CHECKS PASSED** | 48.12s | Verified all 12 analytical operations, executionStats plans. |
| **Total Phase 6 Regression** | **All Phase 6 Modules** | **143 tests** | **143 PASS, 0 FAIL** | **137.46s** | **100% Pass Rate across all suites.** |

---

## 5. Baseline & Invariant Verification

Before and after the targeted audit and verification test execution, database invariants were confirmed against the local MongoDB Community Server instance:

| Collection / Target | Expected Invariant | Observed Pre-Audit | Observed Post-Audit | Status |
| :--- | :--- | :--- | :--- | :--- |
| `jobs` Collection Documents | 129,550 | 129,550 | 129,550 (Delta: 0) | **PASS** |
| `companies` Collection Documents | 24,472 | 24,472 | 24,472 (Delta: 0) | **PASS** |
| `jobs` Indexes | 11 | 11 | 11 | **PASS** |
| `companies` Indexes | 4 | 4 | 4 | **PASS** |
| Total Database Indexes | 15 | 15 | 15 | **PASS** |
| MongoDB Server Version | Local Community Server 9.0.4 | 9.0.4 | 9.0.4 | **PASS** |
| Active Database URI | `mongodb://localhost:27017/` | `mongodb://localhost:27017/` | `mongodb://localhost:27017/` | **PASS (Local Only)** |
| Remote Atlas / Cloud Network Traffic | 0 calls | 0 calls | 0 calls | **PASS** |

---

## 6. Audited Ground Truth Results & Exact Denominators

### 6.1 Platform Overview
- **Total Canonical Postings:** 129,550 (100.0%)
- **LinkedIn Volume:** 123,835 postings (95.59% of total repository)
- **Indeed Volume:** 5,715 postings (4.41% of total repository)

### 6.2 Field Completeness Audit (14 Attributes)
Evaluated against exact platform denominators: LinkedIn ($N_{LI} = 123,835$), Indeed ($N_{Ind} = 5,715$), Total ($N_{Total} = 129,550$).

| Field Name | Attribute Label | Category | LinkedIn Populated | LinkedIn % | Indeed Populated | Indeed % | Upstream Lineage & Provenance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `company.name` | Company Name | Identity & Metadata | 122,116 | 98.61% | 5,611 | 98.18% | Missing only for confidential/undisclosed postings. |
| `location.state` | State Code (USPS) | Geographic & Modality | 112,159 | 90.57% | 5,381 | 94.16% | Parsed 2-letter postal jurisdictions (51 jurisdictions). |
| `location.city` | City Name | Geographic & Modality | 108,855 | 87.90% | 0 | **0.00%** | Upstream Indeed scraper omitted city-level extraction. |
| `location.is_remote` | Remote Work (Explicit) | Geographic & Modality | 15,236 | 12.30% | 0 | **0.00%** | LinkedIn has 15,236 explicit True, 108,599 Null. Indeed is 100% Null. |
| `salary.normalized_annual` | Normalized Annual Salary | Compensation | 36,059 | 29.12% | 0 | **0.00%** | Continuous annualized pay is exclusive to LinkedIn. |
| `salary.estimated_midpoint` | Estimated Midpoint | Compensation | 0 | **0.00%** | 5,715 | 100.00% | Derived search query midpoint is exclusive to Indeed. |
| `salary.salary_bucket` | Standardized Salary Bucket | Compensation | 36,059 | 29.12% | 5,715 | 100.00% | Standardized 6-tier classification available on both. |
| `skills` | Extracted Skills | Skills & Taxonomy | 122,083 | 98.59% | 5,483 | 95.94% | LinkedIn has 35 disciplines; Indeed has 464 technical tools. |
| `experience_level` | Experience Level | Skills & Taxonomy | 94,439 | 76.26% | 0 | **0.00%** | Upstream Indeed scraper omitted seniority classification. |
| `normalized_employment_type` | Employment Type | Identity & Metadata | 123,835 | 100.00% | 0 | **0.00%** | LinkedIn 100% mapped; Indeed omitted upstream. |
| `role_category` | Role Category | Skills & Taxonomy | 123,835 | 100.00% | 5,715 | 100.00% | Indeed is 100% data science roles; LinkedIn is general. |
| `description` | Job Description | Content & Lineage | 123,828 | 99.99% | 5,413 | 94.72% | Raw textual posting body text. |
| `posted_date` | Date Posted | Content & Lineage | 123,835 | 100.00% | 0 | **0.00%** | LinkedIn 100% timestamped; Indeed omitted timestamp. |
| `job_url` | Original Job URL | Content & Lineage | 123,835 | 100.00% | 5,715 | 100.00% | Direct original web source posting URL. |

### 6.3 Workplace Modality Tri-State Model
- **LinkedIn ($N = 123,835$):**
  - Explicitly Remote (`location.is_remote: True`): **15,236** (12.30%)
  - Explicitly On-Site (`location.is_remote: False`): **0** (0.00%)
  - Unspecified / Non-Remote (`location.is_remote: Null`): **108,599** (87.70%)
- **Indeed ($N = 5,715$):**
  - Explicitly Remote (`location.is_remote: True`): **0** (0.00%)
  - Explicitly On-Site (`location.is_remote: False`): **0** (0.00%)
  - Unspecified (`location.is_remote: Null`): **5,715** (100.00%)

### 6.4 Role Category Specialization
- **Indeed ($N = 5,715$ — 100.0% Data Science Focus):**
  - Data Scientist: 2,543 (44.50%)
  - Data Analyst: 1,793 (31.37%)
  - Data Engineer: 1,379 (24.13%)
  - Non-Data Roles: 0 (0.00%)
- **LinkedIn ($N = 123,835$ — Broad Cross-Industry Focus):**
  - Other: 97,556 (78.78%)
  - Sales: 9,376 (7.57%)
  - Healthcare: 8,367 (6.76%)
  - Software Engineer: 3,948 (3.19%)
  - Data Analyst: 2,126 (1.72%)
  - Data Engineer: 1,237 (1.00%)
  - Data Scientist: 1,225 (0.99%)

### 6.5 Cross-Platform Shared Employers
- **Distinct LinkedIn Employers:** 24,415
- **Distinct Indeed Employers:** 2,231
- **Exact Shared Employer Intersection:** **570 employers**
  - Overlap % of Indeed Employers: **25.55%** (570 / 2,231)
  - Overlap % of LinkedIn Employers: **2.33%** (570 / 24,415)
- **Top Shared Employers by Volume:**
  1. **Capital One:** 550 total (LinkedIn: 496, Indeed: 54)
  2. **Ingersoll Rand:** 519 total (LinkedIn: 517, Indeed: 2)
  3. **Dice:** 421 total (LinkedIn: 415, Indeed: 6)
  4. **Wells Fargo:** 407 total (LinkedIn: 388, Indeed: 19)
  5. **Solomon Page:** 327 total (LinkedIn: 326, Indeed: 1)
  6. **Advance Auto Parts:** 306 total (LinkedIn: 303, Indeed: 3)
  7. **Verizon:** 270 total (LinkedIn: 256, Indeed: 14)
  8. **Trinity Health:** 249 total (LinkedIn: 242, Indeed: 7)
  9. **Booz Allen Hamilton:** 232 total (LinkedIn: 81, Indeed: 151)
  10. **Thermo Fisher Scientific:** 220 total (LinkedIn: 218, Indeed: 2)

### 6.6 Salary Separation & 6-Tier Buckets
- **LinkedIn Continuous Compensation (`salary.normalized_annual`):**
  - Postings with Annualized Compensation: **36,059** (29.12%)
  - Threshold-Adjusted Mean ($\le \$1,000,000$): **$95,515.00** ($n = 36,021$)
  - Median Compensation: **$81,375.00**
  - Observed Range: **$1.00 – $960,000.00**
  - Excluded Outliers ($> \$1,000,000$): **38 postings**
- **Indeed Derived Search-Band Midpoint (`salary.estimated_midpoint`):**
  - Postings with Search-Band Midpoint: **5,715** (100.00%)
  - Mean Midpoint: **$116,501.31** ($n = 5,715$)
  - Median Midpoint: **$110,000.00**
  - Search-Band Range: **$70,000.00 – $175,000.00**
  - Excluded Outliers: **0** (Naturally bounded by scrape query intervals)
- **6-Tier Salary Bucket Distribution:**
  - `<80000`: LinkedIn 17,440 (48.37% of salary / 14.08% total) | Indeed 788 (13.79% of salary / 13.79% total)
  - `80000-99999`: LinkedIn 4,606 (12.77% of salary / 3.72% total) | Indeed 953 (16.68% of salary / 16.68% total)
  - `100000-119999`: LinkedIn 4,092 (11.35% of salary / 3.30% total) | Indeed 1,394 (24.39% of salary / 24.39% total)
  - `120000-139999`: LinkedIn 3,184 (8.83% of salary / 2.57% total) | Indeed 1,292 (22.61% of salary / 22.61% total)
  - `140000-159999`: LinkedIn 2,326 (6.45% of salary / 1.88% total) | Indeed 873 (15.28% of salary / 15.28% total)
  - `>160000`: LinkedIn 4,411 (12.23% of salary / 3.56% total) | Indeed 415 (7.26% of salary / 7.26% total)

### 6.7 Skills Taxonomy Boundaries
- **LinkedIn (35 Broad Functional Disciplines, $N = 123,835$):**
  1. Information Technology: 25,252 (20.39%)
  2. Sales: 21,188 (17.11%)
  3. Management: 20,385 (16.46%)
  4. Manufacturing: 17,728 (14.32%)
  5. Health Care Provider: 16,674 (13.46%)
  6. Business Development: 13,302 (10.74%)
  7. Engineering: 12,526 (10.12%)
  8. Other: 12,312 (9.94%)
  9. Finance: 8,011 (6.47%)
  10. Marketing: 5,397 (4.36%)
- **Indeed (464 Granular Technical Tools, $N = 5,715$):**
  1. Python: 3,325 (58.18%)
  2. SQL: 3,104 (54.31%)
  3. Machine Learning: 2,297 (40.19%)
  4. R: 2,234 (39.09%)
  5. Hadoop: 1,714 (29.99%)
  6. Spark: 1,531 (26.79%)
  7. Java: 1,480 (25.90%)
  8. Tableau: 1,236 (21.63%)
  9. Data Mining: 1,059 (18.53%)
  10. Hive: 966 (16.90%)

---

## 7. Playwright Browser Automation & Visual Evidence

The application was verified in Google Chrome via Playwright automation (`scripts/verify_step_8_browser.py`).

### Browser Console & Network Audit
- **Critical Console Errors:** **0** (Only browser favicon 404s for `/favicon.ico`).
- **Remote Atlas / Cloud Network Traffic:** **0** (Confirmed strictly local MongoDB Community Server).
- **HTTP Response Codes:** All application pages returned **HTTP 200 OK**.

### Visual Evidence Artifacts

````carousel
![06_1 Executive Platform Overview](/C:/Users/Dell/.gemini/antigravity-ide/brain/0f81372d-5d57-442c-ae93-c948e56dcf88/06_1_platform_overview_kpis.png)
<!-- slide -->
![06_2 Data Coverage & Field Completeness Audit](/C:/Users/Dell/.gemini/antigravity-ide/brain/0f81372d-5d57-442c-ae93-c948e56dcf88/06_2_field_completeness_audit.png)
<!-- slide -->
![06_3 Job Characteristics & Workplace Modality](/C:/Users/Dell/.gemini/antigravity-ide/brain/0f81372d-5d57-442c-ae93-c948e56dcf88/06_3_job_characteristics.png)
<!-- slide -->
![06_3b Role Specialization Breakdown](/C:/Users/Dell/.gemini/antigravity-ide/brain/0f81372d-5d57-442c-ae93-c948e56dcf88/06_3b_role_specialization_tab.png)
<!-- slide -->
![06_4 Cross-Platform Shared Employers](/C:/Users/Dell/.gemini/antigravity-ide/brain/0f81372d-5d57-442c-ae93-c948e56dcf88/06_4_shared_employers.png)
<!-- slide -->
![06_5 Compensation & Salary Structure Comparison](/C:/Users/Dell/.gemini/antigravity-ide/brain/0f81372d-5d57-442c-ae93-c948e56dcf88/06_5_salary_separation_buckets.png)
<!-- slide -->
![06_6 Skills Taxonomy Boundaries](/C:/Users/Dell/.gemini/antigravity-ide/brain/0f81372d-5d57-442c-ae93-c948e56dcf88/06_6_skills_taxonomy_contrast.png)
<!-- slide -->
![06_7 Experience Level Coverage & Disclosure](/C:/Users/Dell/.gemini/antigravity-ide/brain/0f81372d-5d57-442c-ae93-c948e56dcf88/06_7_experience_disclosure.png)
<!-- slide -->
![06_8 Methodology, Provenance Lineage & Denominator Rules](/C:/Users/Dell/.gemini/antigravity-ide/brain/0f81372d-5d57-442c-ae93-c948e56dcf88/06_8_methodology_reference.png)
````

---

## 8. Known Limitations & Deferred Work

1. **City and Experience Omission on Indeed:** The upstream Indeed scraper completely omitted city names and experience-level annotations (both 0.0% populated). These missing values are disclosed as provenance limitations and are never fabricated or imputed.
2. **Phase 6 Step 9 (CRUD Demonstration):** Deferred. Under strict project governance and stop-gate protocol, `pages/6_CRUD_Demo.py` remains in its placeholder state established in Step 2. No CRUD mutations or page modifications have been performed.

---

## 9. Stop Gate Enforcement

Phase 6 Step 8 reconciliation, quality improvement, test verification, and documentation are complete.

**STOP GATE ACTIVE:** Antigravity has stopped and is waiting for your review and explicit approval of Phase 6 Step 8 before proceeding to Phase 6 Step 9 (CRUD Demonstration).
