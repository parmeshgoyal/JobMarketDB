"""
JobMarketDB - Operational Query & Search Layer (Phase 5)

Implements the operational queries (Operations 1 to 7) defined in PHASE_2_MONGODB_SCHEMA.md:
1. Job Search by Title (Text index or regex filter)
2. Location Filtering (Compound index: location.state + location.is_remote)
3. Salary Range & Bucket Filtering (Compound index: salary.salary_bucket + salary.normalized_annual)
4. Skill-Demand Filtering (Multi-key index: skills)
5. Company Filtering (Index: company.name)
6. Experience-Level Filtering (Index: experience_level.value)
7. Source Filtering (Index: source)
+ Multi-Facet Composite Search
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to convert MongoDB ObjectId to string for JSON serialization."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def _validate_limit(limit: int) -> None:
    """Validates that limit parameter is a positive integer (> 0)."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError(f"limit must be a positive integer (> 0), got {limit!r}")


def _validate_pagination(limit: int, skip: int) -> None:
    """Validates that pagination parameters are positive limit (> 0) and non-negative skip (>= 0)."""
    _validate_limit(limit)
    if not isinstance(skip, int) or isinstance(skip, bool) or skip < 0:
        raise ValueError(f"skip cannot be negative, got {skip!r}")


def _validate_salary_range(min_annual: Optional[float], max_annual: Optional[float]) -> None:
    """Validates that min_annual does not exceed max_annual."""
    if min_annual is not None and max_annual is not None:
        if float(min_annual) > float(max_annual):
            raise ValueError(
                f"Invalid salary range: min_annual ({min_annual}) cannot exceed max_annual ({max_annual})."
            )


ALLOWED_SORT_FIELDS = {None, "relevance", "salary", "posted_date", "title"}


def _validate_sort_parameters(
    sort_by: Optional[str] = None,
    sort_order: Union[int, str] = -1,
) -> Tuple[Optional[str], int]:
    """
    Validates sort_by against allowlist and normalizes sort_order to 1 (asc) or -1 (desc).
    
    Allowed sort_by: None, 'relevance', 'salary', 'posted_date', 'title'.
    Allowed sort_order: 1, -1, 'asc', 'desc'.
    """
    if sort_by is not None:
        if not isinstance(sort_by, str) or sort_by.strip().lower() not in {"relevance", "salary", "posted_date", "title"}:
            raise ValueError(
                f"Invalid sort_by: {sort_by!r}. Allowed values: None, 'relevance', 'salary', 'posted_date', 'title'."
            )
        clean_sort_by = sort_by.strip().lower()
    else:
        clean_sort_by = None

    if isinstance(sort_order, str):
        so_lower = sort_order.strip().lower()
        if so_lower in ("asc", "ascending", "1"):
            clean_sort_order = 1
        elif so_lower in ("desc", "descending", "-1"):
            clean_sort_order = -1
        else:
            raise ValueError(
                f"Invalid sort_order: {sort_order!r}. Allowed values: 1, -1, 'asc', 'desc'."
            )
    elif isinstance(sort_order, int) and not isinstance(sort_order, bool):
        if sort_order in (1, -1):
            clean_sort_order = sort_order
        else:
            raise ValueError(
                f"Invalid sort_order: {sort_order!r}. Allowed values: 1, -1, 'asc', 'desc'."
            )
    else:
        raise ValueError(
            f"Invalid sort_order type/value: {sort_order!r}. Allowed values: 1, -1, 'asc', 'desc'."
        )

    return clean_sort_by, clean_sort_order


def _parse_is_remote_filter(is_remote: Optional[Union[bool, str]]) -> Tuple[bool, Optional[bool]]:
    """
    Parses and validates is_remote parameter into a (should_filter, expected_value) tuple.
    Returns:
      (False, None) if 'any' (no filtering)
      (True, True) if remote (True, or documented remote strings: 'true', '1', 'remote')
      (True, False) if on-site (False, or documented on-site strings: 'false', '0', 'onsite', 'on-site')
      (True, None) if unknown / unstated (is_remote is None, or strings: 'unknown', 'null', 'none')
    
    Raises:
      ValueError on invalid strings, unrecognized values, or arbitrary integers (e.g. 2).
    """
    if is_remote is None:
        return True, None
    if isinstance(is_remote, bool):
        return True, is_remote
    if isinstance(is_remote, str):
        cleaned = is_remote.strip().lower()
        if cleaned == "any":
            return False, None
        elif cleaned in ("true", "1", "remote"):
            return True, True
        elif cleaned in ("false", "0", "onsite", "on-site"):
            return True, False
        elif cleaned in ("unknown", "null", "none"):
            return True, None
        else:
            raise ValueError(
                f"Invalid is_remote value: {is_remote!r}. Allowed: True, False, None, 'unknown', or 'any'."
            )
    raise ValueError(
        f"Invalid is_remote value/type: {is_remote!r} ({type(is_remote).__name__}). "
        "Allowed: bool (True/False), None, or documented strings ('any', 'unknown', 'remote', 'onsite')."
    )


def search_jobs_by_title(
    db: Database,
    query_text: str,
    search_mode: str = "text",
    limit: int = 20,
    skip: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Operation 1: Job Search by Title.
    Supports full-text search leveraging 'title_text_description_text' index (search_mode='text')
    or case-insensitive title regex matching (search_mode='regex').
    
    Index Utilization:
    - search_mode='text': Uses TEXT index (TEXT_MATCH / IXSCAN).
    - search_mode='regex': Performs collection scan (COLLSCAN) across jobs as unanchored regex
      cannot leverage a B-tree index on title.

    Raises:
    - ValueError if search_mode is not 'text' or 'regex'.
    - ValueError if limit or skip is negative.

    Returns: (list_of_job_docs, total_match_count)
    """
    _validate_pagination(limit, skip)
    if not search_mode or not isinstance(search_mode, str):
        raise ValueError(f"Invalid search_mode: {search_mode!r}. Must be 'text' or 'regex'.")

    clean_mode = search_mode.strip().lower()
    if clean_mode not in ("text", "regex"):
        raise ValueError(f"Invalid search_mode: {search_mode!r}. Must be 'text' or 'regex'.")

    col: Collection = db["jobs"]
    if not query_text or not query_text.strip():
        return [], 0

    clean_query = query_text.strip()
    if clean_mode == "text":
        filter_dict = {"$text": {"$search": clean_query}}
        cursor = (
            col.find(filter_dict, {"score": {"$meta": "textScore"}})
            .sort([("score", {"$meta": "textScore"})])
            .skip(skip)
            .limit(limit)
        )
    else:  # regex search specifically on title
        filter_dict = {"title": {"$regex": clean_query, "$options": "i"}}
        cursor = col.find(filter_dict).sort([("posted_date", -1)]).skip(skip).limit(limit)

    total_count = col.count_documents(filter_dict)
    results = [_serialize_doc(d) for d in cursor]
    return results, total_count



def filter_jobs_by_location(
    db: Database,
    state: Optional[str] = None,
    is_remote: Optional[Union[bool, str]] = "any",
    limit: int = 20,
    skip: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Operation 2: Location Filtering.
    Leverages compound index 'location.state_1_location.is_remote_1'.

    Strict Tri-State Remote Semantics:
    - is_remote=True: matches explicit remote postings (location.is_remote == True)
    - is_remote=False: matches explicit on-site postings (location.is_remote == False)
    - is_remote=None or 'unknown': matches postings with unknown remote status (location.is_remote == None)
    - is_remote='any': does not filter on remote status

    Raises:
    - ValueError if limit or skip is negative.
    - ValueError if is_remote is an invalid value.
    """
    _validate_pagination(limit, skip)
    col: Collection = db["jobs"]
    filter_dict: Dict[str, Any] = {}

    if state and state.strip():
        filter_dict["location.state"] = state.strip().upper()

    should_filter, remote_val = _parse_is_remote_filter(is_remote)
    if should_filter:
        filter_dict["location.is_remote"] = remote_val

    total_count = col.count_documents(filter_dict)
    cursor = col.find(filter_dict).skip(skip).limit(limit)
    results = [_serialize_doc(d) for d in cursor]
    return results, total_count


def filter_jobs_by_salary(
    db: Database,
    salary_bucket: Optional[str] = None,
    min_annual: Optional[float] = None,
    max_annual: Optional[float] = None,
    limit: int = 20,
    skip: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Operation 3: Salary Range & Bucket Filtering.
    Leverages compound index 'salary.salary_bucket_1_salary.normalized_annual_1'.

    Index Utilization:
    - Discrete bucket alone: Uses compound index prefix (IXSCAN).
    - Discrete bucket + continuous bounds: Uses compound index (IXSCAN).
    - Continuous bounds ALONE (without bucket prefix): Performs collection scan (COLLSCAN)
      because normalized_annual is the suffix field in the compound index.

    Provenance Semantics:
    - Discrete bucket matches both LinkedIn and Indeed on 'salary.salary_bucket'.
    - Continuous bounds (min_annual / max_annual) match on 'salary.normalized_annual'
      (applies to LinkedIn postings where continuous pay is source-supported).
    - Indeed normalized_annual is strictly null and will not match continuous bounds.
    - Stated salaries are never treated as zero.

    Raises:
    - ValueError if limit or skip is negative.
    - ValueError if min_annual > max_annual.
    """
    _validate_pagination(limit, skip)
    _validate_salary_range(min_annual, max_annual)
    col: Collection = db["jobs"]
    filter_dict: Dict[str, Any] = {}

    if salary_bucket and salary_bucket.strip():
        filter_dict["salary.salary_bucket"] = salary_bucket.strip()

    if min_annual is not None or max_annual is not None:
        annual_cond: Dict[str, Any] = {}
        if min_annual is not None:
            annual_cond["$gte"] = float(min_annual)
        if max_annual is not None:
            annual_cond["$lte"] = float(max_annual)
        filter_dict["salary.normalized_annual"] = annual_cond

    total_count = col.count_documents(filter_dict)
    cursor = col.find(filter_dict).skip(skip).limit(limit)
    results = [_serialize_doc(d) for d in cursor]
    return results, total_count


def filter_jobs_by_skills(
    db: Database,
    skills: Union[str, List[str]],
    match_all: bool = True,
    limit: int = 20,
    skip: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Operation 4: Skill Demand Filtering.
    Leverages multi-key index 'skills_1'.

    Preserves authentic source skills without false equivalencies.
    - match_all=True uses '$all' (job must possess all requested skills).
    - match_all=False uses '$in' (job must possess at least one requested skill).

    Raises:
    - ValueError if limit or skip is negative.
    """
    _validate_pagination(limit, skip)
    col: Collection = db["jobs"]
    if isinstance(skills, str):
        skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    else:
        skill_list = [s.strip() for s in skills if s and s.strip()]

    if not skill_list:
        return [], 0

    if match_all:
        filter_dict = {"skills": {"$all": skill_list}}
    else:
        filter_dict = {"skills": {"$in": skill_list}}

    total_count = col.count_documents(filter_dict)
    cursor = col.find(filter_dict).skip(skip).limit(limit)
    results = [_serialize_doc(d) for d in cursor]
    return results, total_count


def filter_jobs_by_company(
    db: Database,
    company_name: Optional[str] = None,
    company_id: Optional[int] = None,
    limit: int = 20,
    skip: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Operation 5: Company Filtering.
    
    Index Utilization:
    - company_name lookup leverages 'company.name_1' index (IXSCAN).
    - company_id lookup on 'jobs' performs a collection scan (COLLSCAN) because
      the unique company index ('company_id_1_unique') resides on the 'companies' collection,
      not on the 'jobs' collection.
    
    Gracefully handles postings with null company name (e.g. orphan company_id 23729571).

    Raises:
    - ValueError if limit or skip is negative.
    """
    _validate_pagination(limit, skip)
    col: Collection = db["jobs"]
    filter_dict: Dict[str, Any] = {}

    if company_id is not None:
        filter_dict["company.company_id"] = int(company_id)
    elif company_name and company_name.strip():
        filter_dict["company.name"] = company_name.strip()
    else:
        return [], 0

    total_count = col.count_documents(filter_dict)
    cursor = col.find(filter_dict).skip(skip).limit(limit)
    results = [_serialize_doc(d) for d in cursor]
    return results, total_count


def filter_jobs_by_experience(
    db: Database,
    experience_level: str,
    limit: int = 20,
    skip: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Operation 6: Experience Level Filtering.
    Leverages index 'experience_level.value_1'.

    LinkedIn postings have observed source experience levels (e.g., 'Mid-Senior level').
    Indeed postings record value: null, status: 'NOT_AVAILABLE' and will not falsely match.

    Raises:
    - ValueError if limit or skip is negative.
    """
    _validate_pagination(limit, skip)
    col: Collection = db["jobs"]
    if not experience_level or not experience_level.strip():
        return [], 0

    clean_level = experience_level.strip()
    filter_dict = {"experience_level.value": clean_level}

    total_count = col.count_documents(filter_dict)
    cursor = col.find(filter_dict).skip(skip).limit(limit)
    results = [_serialize_doc(d) for d in cursor]
    return results, total_count


def filter_jobs_by_source(
    db: Database,
    source: str,
    limit: int = 20,
    skip: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Operation 7: Source Platform Filtering.
    Leverages index 'source_1'.

    Accepts 'linkedin' (123,835 records) or 'indeed' (5,715 records).

    Raises:
    - ValueError if limit or skip is negative.
    """
    _validate_pagination(limit, skip)
    col: Collection = db["jobs"]
    clean_source = source.strip().lower() if source else ""
    if clean_source not in ("linkedin", "indeed"):
        return [], 0

    filter_dict = {"source": clean_source}
    total_count = col.count_documents(filter_dict)
    cursor = col.find(filter_dict).skip(skip).limit(limit)
    results = [_serialize_doc(d) for d in cursor]
    return results, total_count


def search_and_filter_jobs(
    db: Database,
    query_text: Optional[str] = None,
    search_mode: str = "text",
    state: Optional[str] = None,
    is_remote: Optional[Union[bool, str]] = "any",
    salary_bucket: Optional[str] = None,
    min_annual: Optional[float] = None,
    max_annual: Optional[float] = None,
    skills: Optional[Union[str, List[str]]] = None,
    skills_match_all: bool = True,
    company_name: Optional[str] = None,
    experience_level: Optional[str] = None,
    role_category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    sort_by: Optional[str] = None,
    sort_order: Union[int, str] = -1,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Multi-Facet Compound Search & Filter with Allowlisted Sorting.
    Combines operations 1 through 7 into a single unified query interface.
    Routes through available Phase 2 indexes according to query predicates.

    Search Mode:
    - search_mode='text' (default): Full-text compound search on 'title_text_description_text'
      covering 'title' (weight 1) and 'description' (weight 1).
    - search_mode='regex': Case-insensitive regex matching on job 'title'.

    Skills Matching:
    - Queries the dedicated multikey index 'skills_1' (not part of text index).
    - skills_match_all=True (default): Requires all specified skills ($all).
    - skills_match_all=False: Requires any of the specified skills ($in).


    Sorting Capabilities & Semantics:
    - sort_by=None (default): If full-text query is present, defaults to text relevance ('textScore');
      otherwise maintains natural database order.
    - sort_by='relevance': Sorts by full-text relevance score ('textScore') when full-text query is present;
      defaults to natural order if absent or if regex search is used.
    - sort_by='salary': Sorts on 'salary.normalized_annual' using sort_order.
      * Missing Salary Handling: Documents with unstated salary are never silently excluded.
        They sort lowest (at the end for desc, at the beginning for asc).
    - sort_by='posted_date': Sorts on 'posted_date' using sort_order.
      * LinkedIn dated postings sort newest-to-oldest in desc, followed by Indeed postings (null).
    - sort_by='title': Sorts alphabetically on 'title'.

    Raises:
    - ValueError if limit or skip is negative.
    - ValueError if min_annual > max_annual.
    - ValueError if is_remote is an invalid value.
    - ValueError if sort_by or sort_order is not in the allowlist.
    """
    _validate_pagination(limit, skip)
    _validate_salary_range(min_annual, max_annual)
    clean_sort_by, clean_sort_order = _validate_sort_parameters(sort_by, sort_order)

    if not search_mode or not isinstance(search_mode, str):
        raise ValueError(f"Invalid search_mode: {search_mode!r}. Must be 'text' or 'regex'.")
    clean_search_mode = search_mode.strip().lower()
    if clean_search_mode not in ("text", "regex"):
        raise ValueError(f"Invalid search_mode: {search_mode!r}. Must be 'text' or 'regex'.")

    if not isinstance(skills_match_all, bool):
        raise ValueError(f"Invalid skills_match_all: {skills_match_all!r}. Must be a boolean (True or False).")

    col: Collection = db["jobs"]
    filter_dict: Dict[str, Any] = {}

    # 1. Title/Description Text vs Title Regex
    if query_text and query_text.strip():
        clean_query = query_text.strip()
        if clean_search_mode == "regex":
            filter_dict["title"] = {"$regex": clean_query, "$options": "i"}
        else:
            filter_dict["$text"] = {"$search": clean_query}


    # 2. Location & Remote
    if state and state.strip():
        filter_dict["location.state"] = state.strip().upper()

    should_filter, remote_val = _parse_is_remote_filter(is_remote)
    if should_filter:
        filter_dict["location.is_remote"] = remote_val

    # 3. Salary
    if salary_bucket and salary_bucket.strip():
        filter_dict["salary.salary_bucket"] = salary_bucket.strip()

    if min_annual is not None or max_annual is not None:
        annual_cond: Dict[str, Any] = {}
        if min_annual is not None:
            annual_cond["$gte"] = float(min_annual)
        if max_annual is not None:
            annual_cond["$lte"] = float(max_annual)
        filter_dict["salary.normalized_annual"] = annual_cond

    # 4. Skills
    if skills:
        if isinstance(skills, str):
            skill_list = [s.strip() for s in skills.split(",") if s.strip()]
        else:
            skill_list = [s.strip() for s in skills if s and s.strip()]
        if skill_list:
            if skills_match_all:
                filter_dict["skills"] = {"$all": skill_list}
            else:
                filter_dict["skills"] = {"$in": skill_list}

    # 5. Company
    if company_name and company_name.strip():
        filter_dict["company.name"] = company_name.strip()

    # 6. Experience
    if experience_level and experience_level.strip():
        filter_dict["experience_level.value"] = experience_level.strip()

    # 7. Role Category (Leverages role_category.value_1 index)
    if role_category and role_category.strip():
        filter_dict["role_category.value"] = role_category.strip()

    # 8. Source
    if source and source.strip():
        filter_dict["source"] = source.strip().lower()

    total_count = col.count_documents(filter_dict)

    # Determine projection and sort specification
    sort_spec = None
    projection = None

    if clean_sort_by == "relevance" or (clean_sort_by is None and "$text" in filter_dict):
        if "$text" in filter_dict:
            projection = {"score": {"$meta": "textScore"}}
            sort_spec = [("score", {"$meta": "textScore"})]
        else:
            # "relevance" requested without full-text query -> preserve natural order
            sort_spec = None
    elif clean_sort_by == "salary":
        sort_spec = [("salary.normalized_annual", clean_sort_order)]
    elif clean_sort_by == "posted_date":
        sort_spec = [("posted_date", clean_sort_order)]
    elif clean_sort_by == "title":
        sort_spec = [("title", clean_sort_order)]

    # Build cursor
    if projection:
        cursor = col.find(filter_dict, projection)
    else:
        cursor = col.find(filter_dict)

    if sort_spec:
        cursor = cursor.sort(sort_spec)

    cursor = cursor.skip(skip).limit(limit)
    results = [_serialize_doc(d) for d in cursor]
    return results, total_count


def get_job_by_id(
    db: Database,
    job_id: Union[str, int, ObjectId],
) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single job posting by MongoDB ObjectId or authentic source_job_id.

    Lookup Resolution:
    1. If job_id is an ObjectId instance, queries {'_id': job_id}.
    2. If job_id is a 24-character hexadecimal string, queries {'_id': ObjectId(job_id)}.
    3. If not found by ObjectId (or not valid hex), queries authentic source_job_id (string or integer).

    Raises:
    - ValueError if job_id is None, empty string, or invalid type.

    Returns:
    - Serialized dictionary with '_id' converted to string, or None if not found.
    """
    if job_id is None:
        raise ValueError("job_id cannot be None")

    col: Collection = db["jobs"]
    doc = None

    if job_id is None:
        return None

    if isinstance(job_id, ObjectId):
        doc = col.find_one({"_id": job_id})
    elif isinstance(job_id, str):
        cleaned_id = job_id.strip()
        if not cleaned_id:
            return None
        if ObjectId.is_valid(cleaned_id):
            try:
                doc = col.find_one({"_id": ObjectId(cleaned_id)})
            except Exception:
                doc = None

        if doc is None:
            doc = col.find_one({"source_job_id": cleaned_id})

        if doc is None and cleaned_id.isdigit():
            doc = col.find_one({"source_job_id": int(cleaned_id)})
    elif isinstance(job_id, int) and not isinstance(job_id, bool):
        doc = col.find_one({"source_job_id": str(job_id)})
        if doc is None:
            doc = col.find_one({"source_job_id": job_id})
    else:
        raise ValueError(
            f"Invalid job_id type: {type(job_id).__name__}. Must be str, int, or ObjectId."
        )

    return _serialize_doc(doc) if doc else None


def get_related_jobs(
    db: Database,
    job_id: Union[str, int, ObjectId],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Finds related job postings for a given job using transparent, rule-based matching.

    Methodological Safeguards (Priority 2 Taxonomy Fidelity):
    1. Same-Platform Matching: Strictly restricts candidate jobs to the target job's source
       platform ('linkedin' or 'indeed'). This guarantees LinkedIn's 35 broad functional
       domains (e.g. 'Information Technology', 'Management') are NEVER conflated with Indeed's
       464 granular technical tools (e.g. 'Python', 'SQL').
    2. Exclusion of Original Job: The target posting is strictly excluded via '_id': {'$ne': ...}
       and 'source_job_id': {'$ne': ...}.
    3. Hierarchical Missing-Field Fallback:
       - Primary: Matches on both shared role_category.value and overlapping skills.
       - Fallback 1 (Skills Only): If role_category is missing or yields < limit.
       - Fallback 2 (Role Only): If skills array is empty.
       - Fallback 3 (State / Platform): If both role and skills are unpopulated.
    4. Deduplication & Ranking:
       - Guarantees zero duplicate postings in recommendations.
       - Ranked deterministically by match score:
         (shared_skills_count * 3) + (5 if same_role else 0) + (1 if same_state else 0).
       - Returns transparent match explanation metadata with every recommended job.

    Raises:
    - ValueError if limit <= 0.

    Returns:
    - List of serialized job dictionaries (up to limit) with embedded 'match_explanation'.
    """
    _validate_limit(limit)
    target_job = get_job_by_id(db, job_id)
    if not target_job:
        return []

    col: Collection = db["jobs"]
    target_obj_id = ObjectId(target_job["_id"]) if isinstance(target_job["_id"], str) and ObjectId.is_valid(target_job["_id"]) else target_job["_id"]
    target_source = target_job.get("source")
    target_source_id = str(target_job.get("source_job_id", ""))
    target_role = (target_job.get("role_category") or {}).get("value")
    target_skills = [s.strip() for s in (target_job.get("skills") or []) if isinstance(s, str) and s.strip()]
    target_state = (target_job.get("location") or {}).get("state")

    # Base filter strictly enforces same platform and excludes the target posting
    base_filter: Dict[str, Any] = {
        "source": target_source,
        "_id": {"$ne": target_obj_id},
    }
    if target_source_id:
        base_filter["source_job_id"] = {"$ne": target_source_id}

    candidate_docs: List[Dict[str, Any]] = []
    seen_ids = set()

    # Strategy 1: Shared Role Category + Overlapping Skills
    if target_role and target_skills:
        q1 = {
            **base_filter,
            "role_category.value": target_role,
            "skills": {"$in": target_skills},
        }
        for d in col.find(q1).limit(50):
            if d["_id"] not in seen_ids:
                seen_ids.add(d["_id"])
                candidate_docs.append(d)

    # Strategy 2: Overlapping Skills (if pool is small or role is unpopulated)
    if len(candidate_docs) < limit * 3 and target_skills:
        q2 = {
            **base_filter,
            "skills": {"$in": target_skills},
        }
        for d in col.find(q2).limit(50):
            if d["_id"] not in seen_ids:
                seen_ids.add(d["_id"])
                candidate_docs.append(d)

    # Strategy 3: Shared Role Category (if skills array is empty or pool is small)
    if len(candidate_docs) < limit * 3 and target_role:
        q3 = {
            **base_filter,
            "role_category.value": target_role,
        }
        for d in col.find(q3).limit(50):
            if d["_id"] not in seen_ids:
                seen_ids.add(d["_id"])
                candidate_docs.append(d)

    # Strategy 4: Fallback to same state & source (if both role and skills are missing)
    if len(candidate_docs) < limit and target_state:
        q4 = {
            **base_filter,
            "location.state": target_state,
        }
        for d in col.find(q4).limit(30):
            if d["_id"] not in seen_ids:
                seen_ids.add(d["_id"])
                candidate_docs.append(d)

    # Final fallback: general recent postings from same platform
    if len(candidate_docs) < limit:
        for d in col.find(base_filter).limit(30):
            if d["_id"] not in seen_ids:
                seen_ids.add(d["_id"])
                candidate_docs.append(d)

    # Score, explain, and rank candidates
    scored_candidates = []
    for cand in candidate_docs:
        cand_skills = [s.strip() for s in (cand.get("skills") or []) if isinstance(s, str) and s.strip()]
        shared_skills = sorted(list(set(target_skills).intersection(set(cand_skills))))
        has_same_role = bool(target_role and (cand.get("role_category") or {}).get("value") == target_role)
        has_same_state = bool(target_state and (cand.get("location") or {}).get("state") == target_state)

        match_score = (len(shared_skills) * 3) + (5 if has_same_role else 0) + (1 if has_same_state else 0)

        cand_date = cand.get("posted_date")
        date_sort_key = ""
        if isinstance(cand_date, str):
            date_sort_key = cand_date
        elif hasattr(cand_date, "isoformat"):
            date_sort_key = cand_date.isoformat()

        cand_serialized = _serialize_doc(cand)
        cand_serialized["match_explanation"] = {
            "source_platform": target_source,
            "shared_skills": shared_skills,
            "shared_skills_count": len(shared_skills),
            "same_role_category": has_same_role,
            "same_state": has_same_state,
            "match_score": match_score,
            "target_role": target_role,
            "matched_role": (cand.get("role_category") or {}).get("value"),
        }
        scored_candidates.append((match_score, date_sort_key, cand_serialized))

    # Sort descending by match_score, then date_sort_key
    scored_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [c[2] for c in scored_candidates[:limit]]

