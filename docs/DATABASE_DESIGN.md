# JobMarketDB — Database Design & Indexing Strategy

## 1. Document-Oriented Modeling Philosophy

Relational database models often struggle with job market datasets due to high structural heterogeneity:
- Postings from different platforms feature divergent schemas (e.g., LinkedIn includes continuous annualized salaries, while Indeed provides salary intervals and query midpoints).
- Skill sets are naturally multi-valued arrays rather than rigid tabular rows.
- Deep relational joins between massive job postings and employer dimension tables incur heavy query overhead during full-text and multi-facet filtering.

JobMarketDB adopts a **hybrid document-oriented schema design** in MongoDB:
1. **Embedded Subdocuments**: High-cardinality attributes frequently accessed alongside posting records (such as normalized compensation, geographic coordinates/modality, and employer names) are embedded directly within the job posting document.
2. **Normalized Reference Collections**: Detailed employer intelligence (headquarters, company size, industry descriptions) is stored in a dedicated `companies` collection to eliminate data redundancy across thousands of postings from the same employer.
3. **Array-Valued Skills**: Skills are stored as clean string arrays (`skills: ["Python", "SQL", "Docker"]`), allowing native multikey indexing, `$in` filtering, and `$unwind` aggregations without junction tables.

---

## 2. Collection Schemas

### 2.1. Canonical Collection: `jobs` (129,550 Documents)
The primary collection storing authentic tech job postings from LinkedIn (`123,835`) and Indeed (`5,715`).

```json
{
  "_id": {"$oid": "6720b0805c87e83d8a1e4a10"},
  "source": "linkedin",
  "source_job_id": "3708903045",
  "title": "Senior Distributed Systems Engineer",
  "company": {
    "company_id": 10667,
    "name": "Acme Technologies"
  },
  "location": {
    "city": "San Francisco",
    "state": "CA",
    "country": "US",
    "is_remote": true
  },
  "salary": {
    "normalized_annual": 165000.0,
    "estimated_midpoint": null,
    "interval": "yearly",
    "currency": "USD"
  },
  "experience_level": "Mid-Senior level",
  "role_category": "Software Engineering",
  "skills": ["Distributed Systems", "Go", "Kubernetes", "MongoDB"],
  "description": "We are seeking a seasoned backend systems engineer...",
  "posting_date": {"$date": "2023-11-15T00:00:00.000Z"}
}
```

#### Field Design Specifications:
- `source` (`string`): Provenance platform identifier (`"linkedin"` or `"indeed"`).
- `source_job_id` (`string`): Unique posting ID from upstream source platform.
- `title` (`string`): Official job title. Indexed for full-text search.
- `company.company_id` (`int` or `null`): Relational foreign key referencing `companies.company_id`.
- `company.name` (`string`): Denormalized employer name for rapid filtering and display.
- `location.city` (`string` or `null`): City name. (Note: 100% null in Indeed due to upstream scraper omission).
- `location.state` (`string` or `null`): Standard 2-letter US state abbreviation.
- `location.is_remote` (`bool` or `null`): Tri-state modality model (`True` = Explicitly Remote, `null` = Unspecified / On-site).
- `salary.normalized_annual` (`float` or `null`): Continuous annualized salary in USD. (Populated only on LinkedIn; 100% null on Indeed).
- `salary.estimated_midpoint` (`float` or `null`): Midpoint of search query interval. (Populated on 100% of Indeed records; null on LinkedIn).
- `skills` (`array` of `string`): Platform-specific skills list (35 LinkedIn disciplines vs. 464 Indeed technical tools).

---

### 2.2. Canonical Collection: `companies` (24,472 Documents)
Enriched employer profile records curated and joined from LinkedIn company datasets.

```json
{
  "_id": {"$oid": "6720b0505c87e83d8a1e2001"},
  "company_id": 10667,
  "name": "Acme Technologies",
  "description": "Acme is a global cloud infrastructure provider...",
  "company_size": 5,
  "country": "US",
  "state": "CA",
  "city": "San Francisco",
  "zip_code": "94105",
  "address": "500 Howard St",
  "url": "https://www.linkedin.com/company/acme-technologies"
}
```

---

### 2.3. Disposable Sandbox Collection: `demo_postings` (0 Documents Baseline)
An isolated collection configured with identical schema fields to `jobs`, used exclusively for safe educational CRUD demonstrations. Writes never affect canonical collections.

---

## 3. Production Index Inventory (15 Total Indexes)

To guarantee sub-second execution across 129,550 documents and 14 aggregation operations, JobMarketDB implements **15 specialized production indexes**:

### 3.1. `jobs` Collection Indexes (11 Indexes)

| # | Index Name | Key Specification | Usage & Query Target |
| :- | :--- | :--- | :--- |
| 1 | `_id_` | `{"_id": 1}` | MongoDB default unique document identifier. |
| 2 | `source_1_source_job_id_1_unique` | `{"source": 1, "source_job_id": 1}` (Unique) | Enforces idempotency across data ingestion runs. |
| 3 | `source_1_posting_date_-1` | `{"source": 1, "posting_date": -1}` | Powers chronological feeds filtered by source platform. |
| 4 | `company.name_1` | `{"company.name": 1}` | Accelerates employer name searches and leaderboard aggregations. |
| 5 | `location.state_1_location.city_1` | `{"location.state": 1, "location.city": 1}` | Powers geographic drill-down queries by state and city. |
| 6 | `location.state_1_location.is_remote_1` | `{"location.state": 1, "location.is_remote": 1}` | Covered index for remote vs. on-site geographic distribution. |
| 7 | `experience_level_1` | `{"experience_level": 1}` | Accelerates seniority-level filtering (Entry, Mid, Senior, Director). |
| 8 | `skills_1` | `{"skills": 1}` (Multikey) | Enables high-performance `ALL` / `ANY` skill array matching. |
| 9 | `salary.normalized_annual_1` | `{"salary.normalized_annual": 1}` | Powers continuous salary range filtering and percentile rankings. |
| 10 | `salary.estimated_midpoint_1` | `{"salary.estimated_midpoint": 1}` | Powers Indeed salary midpoint filtering and histogram calculations. |
| 11 | `title_text_description_text` | `{"title": "text", "description": "text"}` | Compound full-text index with linguistic tokenization. |

### 3.2. `companies` Collection Indexes (4 Indexes)

| # | Index Name | Key Specification | Usage & Query Target |
| :- | :--- | :--- | :--- |
| 1 | `_id_` | `{"_id": 1}` | MongoDB default unique document identifier. |
| 2 | `company_id_1_unique` | `{"company_id": 1}` (Unique) | Enforces unique relational employer foreign key lookup. |
| 3 | `name_1` | `{"name": 1}` | Powers alphabetical sorting and employer name search. |
| 4 | `state_1_city_1` | `{"state": 1, "city": 1}` | Powers employer headquarters location filtering. |

---

## 4. Query-Plan & Execution Audit Summary

A 20-case query execution plan audit validated that production indexes are actively leveraged:
- **Index-Backed Stages**:
  - `TEXT_INDEX`: Employed for multi-term keyword search on job titles and descriptions.
  - `IXSCAN`: Leveraged for filtered aggregations (e.g., salary ranges, state filters, source-specific skill unwinds).
  - `COVERED_IXSCAN`: Leveraged for queries satisfied entirely from index trees without loading BSON documents into RAM (e.g. state counts).
- **Legitimate Document Scans (`COLLSCAN`)**: Documented boundaries where full scans are mathematically required:
  - Arbitrary case-insensitive regex pattern matches on titles without leading anchors.
  - Unconstrained dataset-wide `$group` aggregations spanning 100% of documents.

