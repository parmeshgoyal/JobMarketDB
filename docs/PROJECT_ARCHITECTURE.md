# JobMarketDB — System Architecture & Component Design

## 1. Architectural Overview
JobMarketDB follows a clean, decoupled 4-tier architecture designed for high-throughput analytical query processing, strict database safety, and modular maintainability.

```mermaid
flowchart TD
    subgraph Sourcing ["Tier 1: Ingestion & Transformation"]
        A1["LinkedIn Raw CSVs (Postings, Companies, Skills)"] --> B1["LinkedInExtractor (Streaming ETL)"]
        A2["Indeed Tech Dataset CSV"] --> B2["IndeedExtractor (Streaming ETL)"]
        B1 --> C1["jobs_transformed.jsonl (678 MB)"]
        B1 --> C2["companies_transformed.jsonl (37 MB)"]
        B2 --> C1
    end

    subgraph Database ["Tier 2: Local MongoDB Community Server (v9.0.4)"]
        C1 --> D1[("jobs Collection (129,550 docs, 11 Indexes)")]
        C2 --> D2[("companies Collection (24,472 docs, 4 Indexes)")]
        D3[("demo_postings Collection (Sandbox R/W)")]
        E1["Connection Guard (database/connection.py)"] -.->|Strict Localhost Loopback| D1
        E1 -.->|Strict Localhost Loopback| D2
        E1 -.->|Strict Localhost Loopback| D3
    end

    subgraph Service ["Tier 3: Query & Analytics Service Layer"]
        F1["Operational Queries (analytics/queries.py)"]
        F2["Analytical Aggregations (analytics/aggregations.py)"]
        F3["Sandbox CRUD Engine (analytics/crud.py)"]
        F4["Unified Service Facade (JobMarketAnalyticsService)"]
        D1 & D2 --> F1 & F2
        D3 <--> F3
        F1 & F2 & F3 --> F4
    end

    subgraph Frontend ["Tier 4: Editorial SaaS Streamlit UI"]
        F4 --> G1["app.py (Executive Macro Overview)"]
        F4 --> G2["pages/1_Job_Search.py (Flagship Job Explorer)"]
        F4 --> G3["pages/2_Skills_Analytics.py (Skills Intelligence)"]
        F4 --> G4["pages/3_Salary_Analytics.py (Compensation & Outliers)"]
        F4 --> G5["pages/4_Company_and_Geography.py (Employer & Geography)"]
        F4 --> G6["pages/5_Platform_Comparison.py (LinkedIn vs Indeed)"]
        F4 --> G7["pages/6_CRUD_Demo.py (MongoDB Operations Lab)"]
        H1["Shared Design System (utils/style.css, ui_components.py, plots.py)"] --> G1 & G2 & G3 & G4 & G5 & G6 & G7
    end
```

---

## 2. Multi-Tier Decomposition

### Tier 1: Data Sourcing & ETL Pipeline
- **Modules**: [`ingestion/linkedin.py`](../ingestion/linkedin.py), [`ingestion/indeed.py`](../ingestion/indeed.py), [`ingestion/transformers.py`](../ingestion/transformers.py), [`ingestion/validators.py`](../ingestion/validators.py), [`scripts/run_etl.py`](../scripts/run_etl.py).
- **Functionality**:
  - Streams source CSV records chunk-by-chunk to prevent out-of-memory errors on large tabular datasets.
  - Normalizes location, employer names, salary intervals, and skill arrays.
  - Emits pre-validated, newline-delimited JSON (`.jsonl`) files ready for MongoDB bulk insertion.
  - Enforces schema validation against Phase 2 formal data models before writing output records.

### Tier 2: Local Database Engine & Connection Guards
- **Modules**: [`database/connection.py`](../database/connection.py).
- **Functionality**:
  - **Local Loopback Enforcement**: Strictly restricts connections to `localhost:27017` or `127.0.0.1:27017`.
  - **Prohibited Endpoints**: Actively parses URIs in-memory to block MongoDB Atlas (`mongodb+srv://`), remote IP addresses, and replica sets.
  - **Direct Connection Hard-Lock**: Sets `directConnection=True` to prevent automatic replica-set member discovery.
  - **Credential Masking**: Automatically strips user credentials from logs, stack traces, and exception objects.
  - **Connection Pooling**: Manages reusable thread-safe `MongoClient` singletons with fast health-check ping validation.

### Tier 3: Query & Analytics Service Layer
- **Modules**: 
  - [`analytics/queries.py`](../analytics/queries.py): Implements 8 operational query functions (full-text search, regex title search, multi-facet filtering, sorting, pagination).
  - [`analytics/aggregations.py`](../analytics/aggregations.py): Implements complex MongoDB aggregation pipelines (top skills, employer leaderboards, 6-tier salary distributions, cross-platform field completeness, shared employers).
  - [`analytics/crud.py`](../analytics/crud.py): Provides safe CRUD primitives targeting the disposable `demo_postings` collection.
  - [`analytics/service.py`](../analytics/service.py): Unified facade class (`JobMarketAnalyticsService`) providing clean access to operational and analytical methods.
- **Architectural Rules**:
  - No writes to canonical collections (`jobs` and `companies` are strictly read-only).
  - Strict input validation on all pagination parameters (`limit > 0`, `skip >= 0`).
  - Zero hardcoded fallback metrics; every figure is derived from the underlying database.

### Tier 4: Editorial Streamlit UI & Design System
- **Modules**: [`app.py`](../app.py), [`pages/`](../pages/), [`utils/`](../utils/).
- **Design Tokens**:
  - **Canvas Surface**: Warm Ivory (`#FAF8F5`)
  - **Card Surface**: Pure White (`#FFFFFF`)
  - **Secondary Surface**: Soft Warm Tint (`#F5F2EB`)
  - **Primary Typography**: Deep Charcoal (`#1C1F1D`)
  - **Brand & Accents**: Deep Olive (`#2E3A2D`), Sage Green (`#6E856C`), Muted Sage (`#E8EDE7`)
  - **Subtle Borders**: Soft Sand (`#E2DDD5`)
- **Shared Utilities**:
  - [`utils/style.css`](../utils/style.css): Custom CSS tokens, card layouts, sidebar branding, form styles.
  - [`utils/ui_components.py`](../utils/ui_components.py): Reusable UI widgets (`render_editorial_header`, `render_editorial_stat_card`, `render_editorial_callout`, `render_empty_state`, `render_error_state`).
  - [`utils/plots.py`](../utils/plots.py): Plotly chart factory enforcing custom Sage & Ivory palette, transparent backgrounds, and responsive layouts.

---

## 3. Caching & State Management

To achieve instant user interaction while querying a 129,550-document database, the application implements an in-memory caching architecture:

```mermaid
sequenceDiagram
    participant User as Browser Client
    participant UI as Streamlit Page
    participant Cache as Streamlit Memory Cache (@st.cache_data)
    participant Service as Analytics Service
    participant Mongo as Local MongoDB (localhost:27017)

    User->>UI: Request Page (e.g., Salary Analytics)
    UI->>Cache: Call get_salary_distributions()
    alt Cache Hit (Key exists & TTL < 600s)
        Cache-->>UI: Return Cached Aggregation Result (< 5ms)
    else Cache Miss (Initial load or TTL expired)
        Cache->>Service: Execute get_salary_distributions()
        Service->>Mongo: Run Optimized Pipeline via IXSCAN
        Mongo-->>Service: Return BSON Documents
        Service-->>Cache: Format & Store JSON Result
        Cache-->>UI: Return Aggregation Result (200ms - 2s)
    end
    UI->>User: Render Editorial Dashboard & Plotly Figures
```

- **TTL Strategy**: Analytical aggregations (e.g. macro platform KPIs, shared employer overlap, choropleth coordinates) are cached with `ttl=600` (10 minutes).
- **Dynamic Queries**: Search queries with user-specified keywords, pagination offsets, and active filter combinations bypass static caching to return real-time database results.
- **Form Encapsulation**: Interactive mutations in the CRUD Demo are wrapped in `st.form()` to isolate state updates and prevent unwanted script reruns on intermediate widget changes.
