# JobMarketDB — Project Overview

## 1. Executive Summary
**JobMarketDB** is an enterprise-grade labor market intelligence and job discovery platform engineered on a document-oriented **MongoDB** architecture and powered by an editorial **Streamlit** user interface. 

The system unifies two major employment datasets spanning authentic United States tech hiring records:
1. **LinkedIn Job Postings (2023–2024)**: Comprehensive posting stream enriched with employer company records, structured skills mapping, and continuous annualized compensation.
2. **Indeed Tech Job Dataset (Data Science, Analytics & Software Engineering)**: Granular postings capturing specific technical programming tools, library requirements, and search-band salary ranges.

Rather than forcibly merging incompatible fields, JobMarketDB enforces strict **provenance-preserving schemas**, rigorous **taxonomical isolation**, and **methodological compensation separation**, providing genuine labor intelligence across **129,550 authentic job postings** and **24,472 curated company profiles**.

---

## 2. Problem Statement
Modern online job market data is characterized by fragmentation, high schema variability, and conflicting data collection methodologies:
- **Taxonomy Mismatch**: Different job boards classify skills at fundamentally divergent levels of abstraction. Aggregating broad functional domains (e.g., "Information Technology") with granular libraries (e.g., "PyTorch") produces misleading demand metrics.
- **Compensation Heterogeneity**: Some platforms capture actual continuous base salaries (e.g., $120,000/year), while others record broad search query filter bands (e.g., $100,000–$120,000). Treating interval midpoints as observed wages distorts statistical distributions and standard errors.
- **Data Quality & Outliers**: Scraping artifacts, hourly-to-annual normalization multiplication errors, and missing schema attributes (e.g., unparsed cities or omitted remote flags) require transparent auditing rather than silent mutation.
- **Database Safety & Scale**: Storing over 129,000 enriched, nested documents (~680 MB BSON) requires query-driven compound indexing and read-only protections to maintain sub-second query performance without risking canonical corruption.

JobMarketDB was built to solve these challenges through a unified NoSQL analytics engine that honors data provenance while delivering intuitive search, employer intelligence, and macroeconomic visualization.

---

## 3. Core Objectives & Scope

```
+-------------------------------------------------------------------------------------------------+
|                                 JobMarketDB Core System Objectives                              |
+-------------------------------------------------------------------------------------------------+
|  1. Document Modeling     | Schema design leveraging MongoDB embedding & references.           |
|  2. High-Performance ETL  | Streaming pipeline processing 129,550 postings without memory bloat.|
|  3. Analytical Engine     | 12 public service operations delivering sub-second aggregations.   |
|  4. Strict Data Safety    | Canonical collections (jobs, companies) are 100% immutable.        |
|  5. Editorial SaaS UI     | Premium Sage & Ivory interface across 7 interconnected modules.    |
|  6. Educational Sandbox   | Safe CRUD laboratory isolating writes to disposable collections.   |
+-------------------------------------------------------------------------------------------------+
```

### In-Scope Capabilities
- **Multi-Facet Discovery**: Full-text and regex keyword search, allowlisted sorting, experience-level filtering, state/city geographical filtering, and strict `ALL`/`ANY` skill matching.
- **Cross-Platform Analytics**: Empirical comparisons of volume, schema completeness across 14 attributes, workplace modality, and employer hiring overlaps.
- **Skills Taxonomy Separation**: Independent ranking of 464 technical tools (Indeed) and 35 functional disciplines (LinkedIn).
- **Salary Reconciliation**: Isolated continuous pay analysis ($95,515 adjusted mean, $81,375 median) from derived search-band midpoints ($116,501.31 mean, $110,000 median) with 38-record outlier audit.
- **Geographic Choropleth**: 51-jurisdiction interactive map of tech posting density across all 50 states + Washington D.C.
- **Single-Document CRUD Demonstration**: Interactive document creation, inspection, `$set` updates, `$unset` field removal, and single-document deletion with confirmation guards.

### Explicit Out-of-Scope Constraints
- No cloud database migration (MongoDB Atlas is intentionally rejected; deployment is strictly local MongoDB Community Server).
- No production database writes (canonical `jobs` and `companies` collections cannot be modified from the UI).
- No synthetic or mock data fabrication (unmatched relational keys preserve `null` provenance).

---

## 4. Key Metrics & Authoritative Benchmarks

All analytical figures displayed throughout JobMarketDB are dynamically queried from local MongoDB ground truth:

| Analytical Dimension | Verified Authoritative Metric | Provenance / Methodology Note |
| :--- | :--- | :--- |
| **Total Valid Postings** | `129,550` | `jobs` collection total count |
| **LinkedIn Volume** | `123,835` (`95.59%`) | Source platform identifier: `linkedin` |
| **Indeed Volume** | `5,715` (`4.41%`) | Source platform identifier: `indeed` |
| **Curated Company Catalog** | `24,472` profiles | `companies` collection total count |
| **Market Salary Coverage** | `32.24%` (`41,774` records) | `36,059` LinkedIn continuous + `5,715` Indeed midpoints |
| **LinkedIn Adjusted Salary Mean** | **`$95,515.00`** | Continuous USD compensation ($\le \$1,000,000$) |
| **LinkedIn Adjusted Salary Median** | **`$81,375.00`** | Robust central tendency across `36,021` records |
| **LinkedIn Outliers (> $1M)** | `38` records | Preserved unmodified; analyzed via transparent audit |
| **Indeed Midpoint Salary Mean** | **`$116,501.31`** | Derived midpoint from search query intervals |
| **Indeed Midpoint Salary Median** | **`$110,000.00`** | Derived midpoint median across `5,715` records |
| **Indeed Continuous Salary** | `0` (`0.00%`) | Indeed provides 0 continuous salary records |
| **Shared Multi-Platform Employers** | `570` employers | Active on both LinkedIn and Indeed |
| **LinkedIn Skill Scope** | `35` functional domains | High-level discipline classification |
| **Indeed Skill Scope** | `464` technical tools | Granular programming languages and frameworks |
| **Explicit Remote Postings** | `15,236` (`12.30%`) | Tri-state: True = Remote, Null = Unspecified |
| **Geographic Coverage** | `51` jurisdictions | All 50 US States + District of Columbia |
| **Production MongoDB Indexes** | `15` indexes | `11` on `jobs`, `4` on `companies` |

