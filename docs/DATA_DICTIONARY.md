# JobMarketDB — Data Dictionary & Field Specifications

This document defines the schema, data types, nullability constraints, and platform availability for all canonical fields within JobMarketDB.

---

## 1. Canonical Collection: `jobs`

Total Document Count: **129,550**  
- LinkedIn Postings: **123,835** (`95.59%`)  
- Indeed Postings: **5,715** (`4.41%`)

| Field Name | BSON Type | Python Type | Nullable | Source Availability | Description & Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_id` | `ObjectId` | `bson.ObjectId` | No | All | Unique MongoDB primary document identifier. |
| `source` | `String` | `str` | No | All | Sourcing platform. Allowed values: `"linkedin"`, `"indeed"`. |
| `source_job_id` | `String` | `str` | No | All | Unique job identifier from upstream platform. Enforced by unique compound index `(source, source_job_id)`. |
| `title` | `String` | `str` | No | All | Full job posting title (e.g. `"Lead Data Engineer"`). |
| `company.company_id` | `Int32` | `int` | Yes | LinkedIn only | Numeric company ID referencing `companies.company_id`. Null for Indeed records and 1 unlisted LinkedIn posting. |
| `company.name` | `String` | `str` | Yes | All | Employer company name. Stripped of excess whitespace. Null for 1 unlisted posting (`3708903045`). |
| `location.city` | `String` | `str` | Yes | LinkedIn only | US municipality name. **100% null on Indeed** due to upstream scraper schema omission. |
| `location.state` | `String` | `str` | Yes | All | Two-letter US state postal code (e.g. `"CA"`, `"NY"`, `"TX"`). Populated in `112,159` LinkedIn and `5,381` Indeed records. |
| `location.country` | `String` | `str` | No | All | Country code. Standardized to `"US"`. |
| `location.is_remote` | `Boolean` | `bool` | Yes | LinkedIn only | Workplace modality. Tri-state semantics: `True` = Explicitly remote (`15,236` postings); `null` = Unspecified / On-site (`108,599` LinkedIn, `5,715` Indeed). **Never `False`**. |
| `salary.normalized_annual` | `Double` | `float` | Yes | LinkedIn only | Continuous annualized salary in USD. Populated in `36,059` LinkedIn postings. **100% null on Indeed**. |
| `salary.estimated_midpoint` | `Double` | `float` | Yes | Indeed only | Midpoint of scraped salary search interval in USD. Populated in `5,715` Indeed postings. **100% null on LinkedIn**. |
| `salary.interval` | `String` | `str` | Yes | All with salary | Compensation frequency. Allowed values: `"yearly"`, `"hourly"`, `"monthly"`, `"weekly"`. |
| `salary.currency` | `String` | `str` | Yes | All with salary | Standard 3-letter currency code (`"USD"`). |
| `experience_level` | `String` | `str` | Yes | LinkedIn only | Seniority level: `"Internship"`, `"Entry level"`, `"Associate"`, `"Mid-Senior level"`, `"Director"`, `"Executive"`. Null on Indeed. |
| `role_category` | `String` | `str` | Yes | All | Standardized functional domain category (e.g. `"Software Engineering"`, `"Data Science"`, `"Information Technology"`). |
| `skills` | `Array[String]` | `List[str]`| No | All | Array of distinct skills. LinkedIn contains 35 functional domains; Indeed contains 464 technical tools/libraries. Empty array if unlisted. |
| `description` | `String` | `str` | Yes | All | Full text of job description, requirements, and qualifications. Cleaned of unrendered HTML tags. |
| `posting_date` | `Date` | `datetime` | Yes | All | UTC timestamp when posting was published. Formatted as ISO 8601 string in API responses. |

---

## 2. Canonical Collection: `companies`

Total Document Count: **24,472**

| Field Name | BSON Type | Python Type | Nullable | Description & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `_id` | `ObjectId` | `bson.ObjectId` | No | Unique MongoDB primary document identifier. |
| `company_id` | `Int32` | `int` | No | Unique integer company identifier. Enforced by unique index `company_id_1_unique`. |
| `name` | `String` | `str` | No | Cleaned, normalized company name. |
| `description` | `String` | `str` | Yes | Company biography, business model, and mission summary. |
| `company_size` | `Int32` | `int` | Yes | Size category code (1 = 1-10 employees, 2 = 11-50, 3 = 51-200, 4 = 201-500, 5 = 501-1000, 6 = 1001-5000, 7 = 5001-10000, 8 = 10000+). |
| `country` | `String` | `str` | Yes | Headquarters country code (`"US"`). |
| `state` | `String` | `str` | Yes | Two-letter US state postal code for corporate headquarters. |
| `city` | `String` | `str` | Yes | Headquarters city name. |
| `zip_code` | `String` | `str` | Yes | US ZIP or postal code. |
| `address` | `String` | `str` | Yes | Physical street address of headquarters. |
| `url` | `String` | `str` | Yes | Official company website or LinkedIn corporate profile URL. |

---

## 3. Platform Schema Divergence & Data Completeness Matrix

The two upstream data sources exhibit distinct schema profiles:

| Schema Attribute | LinkedIn Postings (`123,835`) | Indeed Postings (`5,715`) | System Accommodation Strategy |
| :--- | :--- | :--- | :--- |
| **Salary Data Type** | Continuous Annualized (`salary.normalized_annual`) | Search-Band Midpoint (`salary.estimated_midpoint`) | Methodological separation: evaluated on separate metrics and tabs. |
| **Salary Coverage** | `36,059` postings (`29.12%`) | `5,715` postings (`100.00%`) | Explicit denominator disclosure per platform. |
| **City Information** | `108,855` populated (`87.90%`) | `0` populated (`0.00%` - Scraper Gap) | Displays `"Unspecified City"` or state-level groupings for Indeed. |
| **State Information** | `112,159` populated (`90.57%`) | `5,381` populated (`94.16%`) | Primary geographic grouping uses 2-letter state codes. |
| **Remote Modality** | `15,236` explicitly True (`12.30%`) | `0` explicitly True (`0.00%` - Scraper Gap) | Tri-state model: null indicates unspecified or on-site. |
| **Experience Level** | `91,894` populated (`74.21%`) | `0` populated (`0.00%` - Scraper Gap) | Filter provides `"All Experience"` default; disabled for Indeed-only. |
| **Skills Vocabulary** | `35` Functional Disciplines | `464` Granular Technical Tools | Isolated tabs and disclaimers; no direct mathematical equivalence. |

