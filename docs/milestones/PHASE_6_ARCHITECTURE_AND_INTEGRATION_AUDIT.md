# JobMarketDB — Phase 6 Architecture Clarification & Frontend-to-Backend Integration Audit Report

**Date:** October 30, 2026  
**Project:** JobMarketDB — Advanced Database Management System (ADBMS)  
**Database Technology:** **MongoDB Community Server 9.0.4** (Local `mongodb://localhost:27017/`)  
**Active Database:** `jobmarketdb`  
**Relational Database Status:** **None (No MySQL, No PostgreSQL; 100% MongoDB-based)**  
**Cloud Status:** Local Development Environment (MongoDB Atlas is not active)  
**Canonical Datasets:** Authentic LinkedIn (123,835 postings) & Indeed (5,715 postings) imported in Phase 4  
**Current Milestone:** Step 2 Complete — Reconciliation Audit Verified — Pending Step 3 Authorization  

---

## 1. Executive Summary

This revised audit report resolves all architectural questions and discrepancies identified during review of Phase 6:
1. **Company Count Reconciliation:** Reconciled the distinction between the standalone `companies` collection (**24,472** normalized employer profile documents) and the unique employer names embedded in the `jobs` collection (**26,076** case-sensitive, or **26,037** normalized case-insensitive).
2. **Backend Service Method Inventory:** Reconciled and formalized the exact public method names on `JobMarketAnalyticsService` (e.g., `get_top_skills`, `get_salary_distribution`, `compare_platforms`) versus the underlying module functions in `analytics/aggregations.py`.
3. **CRUD Sandbox Lifecycle:** Confirmed that `demo_postings` does not currently exist and will be lazily created upon the first user transaction in Step 6, protected by hardcoded collection validation and canonical invariant checks.
4. **KPI Definitions & Calculations:** Formally documented the numerators, denominators, and tri-state handling for Salary Coverage (32.24% total salary information; 27.83% continuous salary) and Remote Work Rates (11.76% overall remote; 0% explicit on-site; 88.24% unstated).

---

## 2. Item 1: Company Count Reconciliation & Verification Evidence

### 2.1 The Two Distinct Metrics Explained
A discrepancy arose because prior documentation conflated two completely different MongoDB objects:
1. **The `companies` Collection:** A standalone dimension collection containing normalized company profile records imported in Phase 4 from `data/processed/companies_transformed.jsonl`.
2. **The `company.name` Field in the `jobs` Collection:** An embedded string attribute on each job posting recording the employer name as written on LinkedIn or Indeed.

### 2.2 Concrete Query Evidence
Executed directly against the active database:
```python
from database.connection import get_database

db = get_database()

# 1. Standalone companies collection count
companies_collection_count = db["companies"].count_documents({})

# 2. Distinct employer names in jobs collection
li_names = {
    n.strip()
    for n in db["jobs"].distinct("company.name", {"source": "linkedin"})
    if n
}
in_names = {
    n.strip()
    for n in db["jobs"].distinct("company.name", {"source": "indeed"})
    if n
}

# Exact case-sensitive set operations
exact_shared = li_names.intersection(in_names)
exact_union = li_names.union(in_names)

# Case-insensitive normalized set operations
li_lower = {n.lower() for n in li_names}
in_lower = {n.lower() for n in in_names}
norm_shared = li_lower.intersection(in_lower)
norm_union = li_lower.union(in_lower)
```

**Actual Execution Output:**
```text
companies Collection Count:                       24,472 documents
Distinct Employer Names in LinkedIn Postings:     24,415
Distinct Employer Names in Indeed Postings:        2,231
Exact Shared Employers (Case-Sensitive Match):       570
Normalized Shared Employers (Case-Insensitive):      599
Total Unique Employer Names in Jobs (Exact Union):  26,076
Total Unique Employer Names in Jobs (Norm Union):   26,037
```

### 2.3 Mathematical Reconciliation Formula
$$\text{Unique LinkedIn Employers} + \text{Unique Indeed Employers} - \text{Shared Employers} = \text{Total Unique Employers in Postings}$$
- **Exact String Matching:**
  $$24,415 + 2,231 - 570 = \mathbf{26,076}$$
- **Normalized (Case-Insensitive) Matching:**
  $$24,405 + 2,231 - 599 = \mathbf{26,037}$$

**Conclusion:** The figure **24,472** is the document count of the standalone `companies` collection. It does not equal, and was never derived from, the set union of company strings inside the `jobs` collection (**26,076**). Both numbers are verified, factual database records.

---

## 3. Item 2: Backend Service Method Inventory & Integration Mapping

### 3.1 Public Method Inventory on `JobMarketAnalyticsService`
Inspection of [`analytics/service.py`](file:///c:/ADBMS%20PROJECT/JobMarketDB/analytics/service.py) confirms the exact public methods that exist on the service instance. The table below maps each service method to the underlying pipeline function in `analytics/queries.py` or `analytics/aggregations.py`:

| Service Method (`JobMarketAnalyticsService`) | Exact Method Signature | Underlying Module Function Delegated To |
| :--- | :--- | :--- |
| `search_jobs` | `(query_text: str, search_mode: str = 'text', limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]` | `analytics.queries.search_jobs_by_title` |
| `filter_by_location` | `(state: Optional[str] = None, is_remote: Union[bool, str, None] = 'any', limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]` | `analytics.queries.filter_jobs_by_location` |
| `filter_by_salary` | `(salary_bucket: Optional[str] = None, min_annual: Optional[float] = None, max_annual: Optional[float] = None, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]` | `analytics.queries.filter_jobs_by_salary` |
| `filter_by_skills` | `(skills: Union[str, List[str]], match_all: bool = True, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]` | `analytics.queries.filter_jobs_by_skills` |
| `filter_by_company` | `(company_name: Optional[str] = None, company_id: Optional[int] = None, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]` | `analytics.queries.filter_jobs_by_company` |
| `filter_by_experience` | `(experience_level: str, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]` | `analytics.queries.filter_jobs_by_experience` |
| `filter_by_source` | `(source: str, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]` | `analytics.queries.filter_jobs_by_source` |
| `search_and_filter` | `(query_text=None, state=None, is_remote='any', salary_bucket=None, min_annual=None, max_annual=None, skills=None, company_name=None, experience_level=None, role_category=None, source=None, sort_by=None, sort_order=-1, limit=20, skip=0) -> Tuple[List[Dict[str, Any]], int]` | `analytics.queries.search_and_filter_jobs` |
| `get_job_by_id` | `(job_id: Union[str, int, ObjectId]) -> Optional[Dict[str, Any]]` | `analytics.queries.get_job_by_id` |
| `get_related_jobs` | `(job_id: Union[str, int, ObjectId], limit: int = 5) -> List[Dict[str, Any]]` | `analytics.queries.get_related_jobs` |
| `get_top_skills` | `(limit: int = 10, source: Optional[str] = None, role_category: Optional[str] = None) -> Dict[str, Any]` | `analytics.aggregations.get_top_demanded_skills` |
| `get_skills_by_platform` | `(limit: int = 10, role_category: Optional[str] = None) -> Dict[str, Any]` | `analytics.aggregations.get_skills_by_platform` |
| `get_top_companies` | `(limit: int = 10, source: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]` | `analytics.aggregations.get_top_hiring_companies` |
| `get_top_locations` | `(limit: int = 10, source: Optional[str] = None, is_remote: Union[bool, str, None] = 'any') -> Dict[str, Any]` | `analytics.aggregations.get_top_job_locations` |
| `get_salary_distribution` | `(source: Optional[str] = None, role_category: Optional[str] = None) -> Dict[str, Any]` | `analytics.aggregations.get_salary_distributions` |
| `compare_platforms` | `() -> Dict[str, Any]` | `analytics.aggregations.compare_sources` |

### 3.2 Formal Integration Mapping by Page
The table below specifies the **exact service methods** that each Streamlit page imports and executes:

| UI Page | Target Phase | Exact Service Method(s) Executed | Plotly Builder Function |
| :--- | :---: | :--- | :--- |
| **`app.py`** (Home) | Step 3 | • `service.compare_platforms()`<br>• `db['jobs'].estimated_document_count()`<br>• `db['companies'].estimated_document_count()`<br>• `db['jobs'].index_information()` | None (KPI Metric Cards & Summary) |
| **`pages/1_Job_Search.py`** | Step 4 | • `service.search_and_filter(...)`<br>• `service.get_job_by_id(...)`<br>• `service.get_related_jobs(...)` | `utils.ui_components.render_pagination_controls()` |
| **`pages/2_Skills_Analytics.py`** | Step 5 | • `service.get_skills_by_platform(...)`<br>• `service.get_top_skills(...)` | `utils.plots.create_skills_demand_chart()` |
| **`pages/3_Salary_Analytics.py`** | Step 5 | • `service.get_salary_distribution(...)`<br>• Reads `data/processed/phase_5_salary_outlier_audit.json` | `utils.plots.create_salary_distribution_chart()` |
| **`pages/4_Company_and_Geography.py`** | Step 5 | • `service.get_top_companies(...)`<br>• `service.get_top_locations(...)` | • `create_horizontal_ranking_chart()`<br>• `create_geographic_comparison_chart()`<br>• `create_us_choropleth_map()` |
| **`pages/5_Platform_Comparison.py`** | Step 5 | • `service.compare_platforms()` | `utils.plots.create_platform_comparison_chart()` |
| **`pages/6_CRUD_Demo.py`** | Step 6 | • Direct CRUD operations strictly against `db['demo_postings']` | None (Interactive Create, Read, Update, Delete forms) |

---

## 4. Item 3: CRUD Sandbox Collection (`demo_postings`) Lifecycle & Safeguards

### 4.1 Current Existence Verification
Running `db.list_collection_names()` against `jobmarketdb` currently outputs:
```text
['jobs', 'companies']
```
The collection `demo_postings` does **not** currently exist in the database.

### 4.2 Lifecycle & Creation Policy
1. **Lazy Initialization:** In MongoDB, collections do not need explicit DDL pre-creation. `demo_postings` will be created automatically upon the first document insert during Step 6.
2. **Strict Isolation Barrier:** All CRUD forms and handlers in `pages/6_CRUD_Demo.py` are hardcoded to reference `db["demo_postings"]`. No variable or dynamic argument can re-target writes to `jobs` or `companies`.
3. **Write Barrier Assertion:** Any method performing an insert, update, or delete checks:
   ```python
   if target_collection != "demo_postings":
       raise PermissionError("Write operations against canonical collections are prohibited.")
   ```
4. **Non-Destructive Reset:** Resetting the sandbox will execute:
   ```python
   db["demo_postings"].delete_many({})
   ```
   It will **never** call `db.drop_collection()`, and will never touch other collections.
5. **Invariant Auditing:** Pre- and post-transaction assertions verify:
   - `db['jobs'].count_documents({}) == 129550` (Delta = 0)
   - `db['companies'].count_documents({}) == 24472` (Delta = 0)
   - Complete index definitions on `jobs` (11) and `companies` (4) remain identical.

---

## 5. Item 4: KPI Definitions, Denominators & Actual Values

The proposed Step 3 Home page KPIs are computed directly from actual database records.

### 5.1 Exact Salary Coverage Calculations

| Metric Name | Numerator Query | Denominator Query | Exact Count | Percentage |
| :--- | :--- | :--- | :---: | :---: |
| **Total Salary Availability**<br>*(Continuous OR Discrete Bucket)* | `{'salary.salary_bucket': {'$ne': None}}` | All jobs (`{}`) | $\frac{41,774}{129,550}$ | **32.24%** |
| **LinkedIn Salary Availability** | `{'source': 'linkedin', 'salary.normalized_annual': {'$ne': None}}` | LinkedIn jobs (`{'source': 'linkedin'}`) | $\frac{36,059}{123,835}$ | **29.12%** |
| **Indeed Salary Availability** | `{'source': 'indeed', 'salary.salary_bucket': {'$ne': None}}` | Indeed jobs (`{'source': 'indeed'}`) | $\frac{5,715}{5,715}$ | **100.00%** |
| **Market-Wide Continuous Salary**<br>*(Stated numerical annual pay)* | `{'salary.normalized_annual': {'$ne': None}}` | All jobs (`{}`) | $\frac{36,059}{129,550}$ | **27.83%** |

**Methodology Distinction:**
- **LinkedIn:** 29.12% of postings include continuous salary values (`normalized_annual`), while 70.88% are unstated (`null`).
- **Indeed:** 100.00% of postings have discrete query compensation buckets (`salary_bucket`), but 0.00% have continuous base compensation (`normalized_annual == None`).
- **Overall Metric Displayed:** 32.24% reflects postings with actionable compensation data (continuous or discrete bucket).

---

### 5.2 Exact Remote Work Adoption Calculations (Strict Tri-State Model)

In accordance with Phase 2 schema requirements, remote work is modeled strictly as a tri-state field:
- `True`: Explicitly stated as remote.
- `False`: Explicitly stated as on-site only.
- `None` (Null): Unspecified / unstated (never silently merged into `False`).

| Metric Name | State Evaluated | MongoDB Query Filter | Exact Document Count | Percentage of Source |
| :--- | :---: | :--- | :---: | :---: |
| **Overall Remote Rate** | `True` | `{'location.is_remote': True}` | **15,236** | **11.76%** (of 129,550) |
| **Overall Explicit On-Site** | `False` | `{'location.is_remote': False}` | **0** | **0.00%** (of 129,550) |
| **Overall Unspecified** | `None` | `{'location.is_remote': None}` | **114,314** | **88.24%** (of 129,550) |
| **LinkedIn Remote Rate** | `True` | `{'source': 'linkedin', 'location.is_remote': True}` | **15,236** | **12.30%** (of 123,835) |
| **LinkedIn Unspecified** | `None` | `{'source': 'linkedin', 'location.is_remote': None}` | **108,599** | **87.70%** (of 123,835) |
| **Indeed Remote Rate** | `True` | `{'source': 'indeed', 'location.is_remote': True}` | **0** | **0.00%** (of 5,715) |
| **Indeed Unspecified** | `None` | `{'source': 'indeed', 'location.is_remote': None}` | **5,715** | **100.00%** (of 5,715) |

**Conclusion for Home Page KPI Cards:**
- Total Postings: **129,550**
- Total Companies: **24,472** (companies collection) / **26,076** (unique posting employers)
- Overall Salary Coverage: **32.24%** (41,774 postings with salary data)
- Remote Work Rate: **11.76%** (15,236 explicitly remote postings)

---

## 6. Item 5: Verifiable Execution Evidence

### 6.1 Database Verification Script Execution
Command executed in PowerShell using the active project virtual environment:
```powershell
.\venv\Scripts\python.exe -c "
from database.connection import get_database
from analytics.service import JobMarketAnalyticsService
import inspect

db = get_database()
service = JobMarketAnalyticsService(db)

print('=== 1. COLLECTIONS ===')
print('Collections:', db.list_collection_names())

print('\n=== 2. DOCUMENT COUNTS ===')
jobs_count = db['jobs'].count_documents({})
companies_count = db['companies'].count_documents({})
print(f'Jobs: {jobs_count:,} | Companies: {companies_count:,}')

print('\n=== 3. SERVICE METHOD INVENTORY ===')
public_methods = [m for m in dir(service) if not m.startswith('_')]
for m in sorted(public_methods):
    sig = inspect.signature(getattr(service, m))
    print(f'service.{m}{sig}')

print('\n=== 4. KPI METRICS ===')
comp = service.compare_platforms()
li = comp['platforms']['linkedin']
ind = comp['platforms']['indeed']
print('LinkedIn Volume:', f\"{li['total_postings']:,}\")
print('LinkedIn Salary Coverage:', f\"{li['salary_coverage']['coverage_percentage']}%\")
print('LinkedIn Remote Rate:', f\"{li['remote_work_breakdown']['remote_percentage']}%\")
print('Indeed Volume:', f\"{ind['total_postings']:,}\")
print('Indeed Salary Coverage:', f\"{ind['salary_coverage']['coverage_percentage']}%\")
print('Indeed Remote Rate:', f\"{ind['remote_work_breakdown']['remote_percentage']}%\")
"
```

### 6.2 Actual Verbatim Output
```text
=== 1. COLLECTIONS ===
Collections: ['jobs', 'companies']

=== 2. DOCUMENT COUNTS ===
Jobs: 129,550 | Companies: 24,472

=== 3. SERVICE METHOD INVENTORY ===
service.compare_platforms() -> Dict[str, Any]
service.filter_by_company(company_name: Optional[str] = None, company_id: Optional[int] = None, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]
service.filter_by_experience(experience_level: str, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]
service.filter_by_location(state: Optional[str] = None, is_remote: Union[bool, str, NoneType] = 'any', limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]
service.filter_by_salary(salary_bucket: Optional[str] = None, min_annual: Optional[float] = None, max_annual: Optional[float] = None, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]
service.filter_by_skills(skills: Union[str, List[str]], match_all: bool = True, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]
service.filter_by_source(source: str, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]
service.get_job_by_id(job_id: Union[str, int, bson.objectid.ObjectId]) -> Optional[Dict[str, Any]]
service.get_related_jobs(job_id: Union[str, int, bson.objectid.ObjectId], limit: int = 5) -> List[Dict[str, Any]]
service.get_salary_distribution(source: Optional[str] = None, role_category: Optional[str] = None) -> Dict[str, Any]
service.get_skills_by_platform(limit: int = 10, role_category: Optional[str] = None) -> Dict[str, Any]
service.get_top_companies(limit: int = 10, source: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]
service.get_top_locations(limit: int = 10, source: Optional[str] = None, is_remote: Union[bool, str, NoneType] = 'any') -> Dict[str, Any]
service.get_top_skills(limit: int = 10, source: Optional[str] = None, role_category: Optional[str] = None) -> Dict[str, Any]
service.search_and_filter(query_text: Optional[str] = None, state: Optional[str] = None, is_remote: Union[bool, str, NoneType] = 'any', salary_bucket: Optional[str] = None, min_annual: Optional[float] = None, max_annual: Optional[float] = None, skills: Union[str, List[str], NoneType] = None, company_name: Optional[str] = None, experience_level: Optional[str] = None, role_category: Optional[str] = None, source: Optional[str] = None, sort_by: Optional[str] = None, sort_order: Union[int, str] = -1, limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]
service.search_jobs(query_text: str, search_mode: str = 'text', limit: int = 20, skip: int = 0) -> Tuple[List[Dict[str, Any]], int]

=== 4. KPI METRICS ===
LinkedIn Volume: 123,835
LinkedIn Salary Coverage: 29.12%
LinkedIn Remote Rate: 12.3%
Indeed Volume: 5,715
Indeed Salary Coverage: 100.0%
Indeed Remote Rate: 0.0%
```

---

## 7. Mandatory Stopping Gate

All discrepancies identified by the user have been investigated, mathematically reconciled, and confirmed through direct queries against MongoDB. 

- **No MySQL database exists or will be created.**
- **No Atlas database will be used.**
- **No synthetic data has been introduced.**
- **No backend service code was rewritten.**
- **Step 3 has not been started.**

I am stopped and awaiting your explicit review and approval before beginning **Phase 6 Step 3: Home & Architecture Overview (`app.py`)**.
