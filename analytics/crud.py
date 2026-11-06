"""
JobMarketDB - Isolated CRUD Demonstration Operations (Phase 6 Step 9)

Provides secure, validated Create, Read, Update, and Delete operations strictly isolated
to the 'jobmarketdb.demo_postings' collection.

MANDATORY DATA SAFETY INVARIANTS:
1. Operates EXCLUSIVELY on 'demo_postings'.
2. Canonical collections 'jobs' and 'companies' are strictly immutable and protected.
3. Bulk deletion (delete_many), collection dropping, and database resets are prohibited.
4. All single-document deletions require verified ObjectId targeting 'demo_postings'.
"""

from datetime import datetime, timezone
import random
import string
from typing import Any, Dict, List, Optional, Tuple, Union
from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import PyMongoError

DEMO_COLLECTION = "demo_postings"
CANONICAL_COLLECTIONS = frozenset({"jobs", "companies", "system.indexes"})


def _generate_demo_id() -> str:
    """Generates a human-readable, unique demonstration posting identifier."""
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"DEMO-{now_str}-{random_suffix}"


def _assert_demo_collection(collection_name: str) -> None:
    """
    Strict safety guard ensuring operations can never target canonical or forbidden collections.
    Raises PermissionError immediately if a forbidden collection is targeted.
    """
    if collection_name in CANONICAL_COLLECTIONS or collection_name != DEMO_COLLECTION:
        raise PermissionError(
            f"Security Violation: Target collection '{collection_name}' is protected or unauthorized. "
            f"CRUD operations are strictly restricted to '{DEMO_COLLECTION}'."
        )


def create_demo_posting(
    db: Database,
    title: str,
    company_name: str,
    description: str,
    location_city: Optional[str] = None,
    location_state: Optional[str] = None,
    is_remote: bool = False,
    skills: Optional[List[str]] = None,
    source: str = "Demonstration Sandbox",
    experience_level: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    salary_currency: str = "USD",
    salary_period: str = "yearly",
) -> Dict[str, Any]:
    """
    Creates and inserts a new demonstration job posting exclusively into 'demo_postings'.
    Validates required fields, data types, and logical constraints.
    """
    _assert_demo_collection(DEMO_COLLECTION)

    # Required field validation
    clean_title = (title or "").strip()
    clean_company = (company_name or "").strip()
    clean_description = (description or "").strip()

    if not clean_title:
        raise ValueError("Job title is required and cannot be empty.")
    if len(clean_title) < 2 or len(clean_title) > 200:
        raise ValueError("Job title must be between 2 and 200 characters.")

    if not clean_company:
        raise ValueError("Company name is required and cannot be empty.")
    if len(clean_company) < 2 or len(clean_company) > 150:
        raise ValueError("Company name must be between 2 and 150 characters.")

    if not clean_description:
        raise ValueError("Job description is required and cannot be empty.")
    if len(clean_description) < 10:
        raise ValueError("Job description must contain at least 10 characters.")

    # Location normalization
    clean_city = (location_city or "").strip() or None
    clean_state = (location_state or "").strip().upper() or None
    if clean_state and len(clean_state) > 10:
        raise ValueError("State code or name is too long.")

    # Skills sanitization
    clean_skills: List[str] = []
    if skills:
        seen = set()
        for s in skills:
            norm_s = str(s).strip()
            if norm_s and norm_s.lower() not in seen:
                seen.add(norm_s.lower())
                clean_skills.append(norm_s)

    # Optional salary validation
    salary_doc: Optional[Dict[str, Any]] = None
    if salary_min is not None or salary_max is not None:
        min_val = float(salary_min) if salary_min is not None else None
        max_val = float(salary_max) if salary_max is not None else None

        if min_val is not None and min_val < 0:
            raise ValueError("Minimum salary cannot be negative.")
        if max_val is not None and max_val < 0:
            raise ValueError("Maximum salary cannot be negative.")
        if min_val is not None and max_val is not None and min_val > max_val:
            raise ValueError("Minimum salary cannot exceed maximum salary.")

        normalized_annual = None
        if min_val is not None and max_val is not None:
            mid = (min_val + max_val) / 2.0
            normalized_annual = mid if salary_period == "yearly" else mid * 2080.0
        elif max_val is not None:
            normalized_annual = max_val if salary_period == "yearly" else max_val * 2080.0
        elif min_val is not None:
            normalized_annual = min_val if salary_period == "yearly" else min_val * 2080.0

        salary_doc = {
            "min_amount": min_val,
            "max_amount": max_val,
            "currency": salary_currency.upper(),
            "period": salary_period.lower(),
            "normalized_annual": round(normalized_annual, 2) if normalized_annual else None,
        }

    now = datetime.now(timezone.utc)
    demo_id = _generate_demo_id()

    doc = {
        "demo_id": demo_id,
        "title": clean_title,
        "company": {"name": clean_company},
        "location": {
            "city": clean_city,
            "state": clean_state,
            "is_remote": bool(is_remote),
        },
        "description": clean_description,
        "skills": clean_skills,
        "source": (source or "Demonstration Sandbox").strip(),
        "experience_level": (experience_level or "").strip() or None,
        "salary": salary_doc,
        "is_demo": True,
        "created_at": now,
        "updated_at": now,
    }

    try:
        res = db[DEMO_COLLECTION].insert_one(doc)
        created_doc = get_demo_posting_by_id(db, res.inserted_id)
        return created_doc if created_doc is not None else doc
    except PyMongoError as err:
        raise RuntimeError(f"Database error creating demonstration posting: {err}") from err


def get_demo_postings(
    db: Database,
    search_query: Optional[str] = None,
    state: Optional[str] = None,
    is_remote: Optional[bool] = None,
    limit: int = 50,
    skip: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves demonstration job postings from 'demo_postings' with optional search and filters.
    Returns (list of postings, total matching count).
    """
    _assert_demo_collection(DEMO_COLLECTION)

    filter_dict: Dict[str, Any] = {}

    if search_query:
        clean_q = search_query.strip()
        if clean_q:
            # Case-insensitive substring match across title, company, skills, or description
            filter_dict["$or"] = [
                {"title": {"$regex": clean_q, "$options": "i"}},
                {"company.name": {"$regex": clean_q, "$options": "i"}},
                {"skills": {"$regex": clean_q, "$options": "i"}},
                {"description": {"$regex": clean_q, "$options": "i"}},
            ]

    if state and state.strip():
        filter_dict["location.state"] = state.strip().upper()

    if is_remote is not None:
        filter_dict["location.is_remote"] = bool(is_remote)

    try:
        col = db[DEMO_COLLECTION]
        total_count = col.count_documents(filter_dict)
        cursor = col.find(filter_dict).sort("created_at", -1).skip(skip).limit(limit)
        postings = list(cursor)
        return postings, total_count
    except PyMongoError as err:
        raise RuntimeError(f"Database error reading demonstration postings: {err}") from err


def get_demo_posting_by_id(db: Database, identifier: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
    """
    Fetches a single demonstration posting by its ObjectId or demo_id string.
    """
    _assert_demo_collection(DEMO_COLLECTION)

    col = db[DEMO_COLLECTION]
    if isinstance(identifier, ObjectId):
        query = {"_id": identifier}
    elif isinstance(identifier, str):
        clean_id = identifier.strip()
        if ObjectId.is_valid(clean_id):
            query = {"$or": [{"_id": ObjectId(clean_id)}, {"demo_id": clean_id}]}
        else:
            query = {"demo_id": clean_id}
    else:
        return None

    try:
        return col.find_one(query)
    except PyMongoError as err:
        raise RuntimeError(f"Database error retrieving demonstration posting: {err}") from err


def update_demo_posting(
    db: Database,
    doc_id: Union[str, ObjectId],
    title: Optional[str] = None,
    company_name: Optional[str] = None,
    description: Optional[str] = None,
    location_city: Optional[str] = None,
    location_state: Optional[str] = None,
    is_remote: Optional[bool] = None,
    skills: Optional[List[str]] = None,
    experience_level: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    salary_period: Optional[str] = None,
    remove_salary: bool = False,
) -> Dict[str, Any]:
    """
    Updates specific fields of an existing demonstration posting in 'demo_postings'.
    Validates inputs, supports targeted $unset for salary removal, and records updated_at timestamp.
    """
    _assert_demo_collection(DEMO_COLLECTION)

    target_oid = ObjectId(doc_id) if isinstance(doc_id, str) and ObjectId.is_valid(doc_id) else doc_id
    if not isinstance(target_oid, ObjectId):
        raise ValueError(f"Invalid demonstration posting ID: {doc_id}")

    # Verify existence
    existing = get_demo_posting_by_id(db, target_oid)
    if not existing:
        raise ValueError(f"Demonstration posting with ID '{doc_id}' not found.")

    update_fields: Dict[str, Any] = {}
    unset_fields: Dict[str, Any] = {}

    if title is not None:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Job title cannot be empty.")
        if len(clean_title) < 2 or len(clean_title) > 200:
            raise ValueError("Job title must be between 2 and 200 characters.")
        update_fields["title"] = clean_title

    if company_name is not None:
        clean_company = company_name.strip()
        if not clean_company:
            raise ValueError("Company name cannot be empty.")
        if len(clean_company) < 2 or len(clean_company) > 150:
            raise ValueError("Company name must be between 2 and 150 characters.")
        update_fields["company.name"] = clean_company

    if description is not None:
        clean_desc = description.strip()
        if not clean_desc:
            raise ValueError("Job description cannot be empty.")
        if len(clean_desc) < 10:
            raise ValueError("Job description must contain at least 10 characters.")
        update_fields["description"] = clean_desc

    if location_city is not None:
        update_fields["location.city"] = location_city.strip() or None

    if location_state is not None:
        update_fields["location.state"] = location_state.strip().upper() or None

    if is_remote is not None:
        update_fields["location.is_remote"] = bool(is_remote)

    if skills is not None:
        clean_skills: List[str] = []
        seen = set()
        for s in skills:
            norm_s = str(s).strip()
            if norm_s and norm_s.lower() not in seen:
                seen.add(norm_s.lower())
                clean_skills.append(norm_s)
        update_fields["skills"] = clean_skills

    if experience_level is not None:
        update_fields["experience_level"] = experience_level.strip() or None

    # Handle salary update or explicit removal
    if remove_salary:
        if salary_min is not None or salary_max is not None:
            raise ValueError("Cannot specify salary values when remove_salary is True.")
        unset_fields["salary"] = ""
    elif salary_min is not None or salary_max is not None or salary_period is not None:
        curr_sal = existing.get("salary") or {}
        min_val = float(salary_min) if salary_min is not None else curr_sal.get("min_amount")
        max_val = float(salary_max) if salary_max is not None else curr_sal.get("max_amount")
        period = (salary_period or curr_sal.get("period") or "yearly").lower()

        if min_val is not None and min_val < 0:
            raise ValueError("Minimum salary cannot be negative.")
        if max_val is not None and max_val < 0:
            raise ValueError("Maximum salary cannot be negative.")
        if min_val is not None and max_val is not None and min_val > max_val:
            raise ValueError("Minimum salary cannot exceed maximum salary.")

        normalized_annual = None
        if min_val is not None and max_val is not None:
            mid = (min_val + max_val) / 2.0
            normalized_annual = mid if period == "yearly" else mid * 2080.0
        elif max_val is not None:
            normalized_annual = max_val if period == "yearly" else max_val * 2080.0
        elif min_val is not None:
            normalized_annual = min_val if period == "yearly" else min_val * 2080.0

        update_fields["salary"] = {
            "min_amount": min_val,
            "max_amount": max_val,
            "currency": "USD",
            "period": period,
            "normalized_annual": round(normalized_annual, 2) if normalized_annual else None,
        }

    if not update_fields and not unset_fields:
        return existing

    update_fields["updated_at"] = datetime.now(timezone.utc)

    update_op: Dict[str, Any] = {"$set": update_fields}
    if unset_fields:
        update_op["$unset"] = unset_fields

    try:
        res = db[DEMO_COLLECTION].update_one({"_id": target_oid}, update_op)
        if res.matched_count == 0:
            raise ValueError(f"Document with ID '{doc_id}' not found for update.")
        return get_demo_posting_by_id(db, target_oid)
    except PyMongoError as err:
        raise RuntimeError(f"Database error updating demonstration posting: {err}") from err


def delete_demo_posting(db: Database, doc_id: Union[str, ObjectId]) -> bool:
    """
    Deletes exactly ONE demonstration posting from 'demo_postings'.
    Refuses any bulk or collection-level deletion.
    Returns True if document was successfully deleted.
    """
    _assert_demo_collection(DEMO_COLLECTION)

    target_oid = ObjectId(doc_id) if isinstance(doc_id, str) and ObjectId.is_valid(doc_id) else doc_id
    if not isinstance(target_oid, ObjectId):
        raise ValueError(f"Invalid demonstration posting ID for deletion: {doc_id}")

    try:
        res = db[DEMO_COLLECTION].delete_one({"_id": target_oid})
        if res.deleted_count == 0:
            raise ValueError(f"Demonstration posting with ID '{doc_id}' does not exist or was already deleted.")
        return True
    except PyMongoError as err:
        raise RuntimeError(f"Database error deleting demonstration posting: {err}") from err


def get_demo_collection_stats(db: Database) -> Dict[str, Any]:
    """
    Returns summary statistics for the isolated 'demo_postings' collection.
    """
    _assert_demo_collection(DEMO_COLLECTION)

    try:
        col = db[DEMO_COLLECTION]
        total_docs = col.count_documents({})
        remote_docs = col.count_documents({"location.is_remote": True})
        with_salary_docs = col.count_documents({"salary.normalized_annual": {"$ne": None}})
        companies = len(col.distinct("company.name"))
        return {
            "total_demo_postings": total_docs,
            "remote_postings": remote_docs,
            "with_salary_postings": with_salary_docs,
            "distinct_companies": companies,
        }
    except PyMongoError as err:
        raise RuntimeError(f"Database error reading demo collection stats: {err}") from err


def get_canonical_counts(db: Database) -> Dict[str, int]:
    """
    Returns exact read-only document counts for canonical collections ('jobs' and 'companies').
    Strictly read-only; never mutates data.
    """
    try:
        return {
            "jobs": int(db["jobs"].count_documents({})),
            "companies": int(db["companies"].count_documents({})),
        }
    except PyMongoError as err:
        raise RuntimeError(f"Database error reading canonical collection counts: {err}") from err
