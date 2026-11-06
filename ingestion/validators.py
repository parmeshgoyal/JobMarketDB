"""
JobMarketDB - Document Schema Validation

Validates transformed job and company documents against the locked
Phase 2 MongoDB schema rules and data integrity constraints.
"""

from typing import Any, Dict, List, Tuple


def validate_job_document(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates a transformed job document against the Phase 2 schema.
    Returns (is_valid, list_of_error_messages).
    """
    errors: List[str] = []

    # 1. Required Root Keys
    required_keys = [
        "source",
        "source_job_id",
        "title",
        "description",
        "company",
        "location",
        "salary",
        "skills",
        "industries",
        "benefits",
        "source_employment_type",
        "normalized_employment_type",
        "experience_level",
        "role_category",
        "job_url",
        "application_url",
        "application_type",
        "posted_date",
        "estimated_posted_date",
        "expiry_date",
        "views_count",
        "applies_count",
        "is_sponsored",
        "source_data",
    ]
    for key in required_keys:
        if key not in doc:
            errors.append(f"Missing required root key: '{key}'")

    # 2. Source Identifier
    if doc.get("source") not in ("linkedin", "indeed"):
        errors.append(f"Invalid 'source': {doc.get('source')}. Expected 'linkedin' or 'indeed'.")

    source_job_id = doc.get("source_job_id")
    if not source_job_id or not isinstance(source_job_id, str):
        errors.append("Field 'source_job_id' must be a non-empty string.")

    # 3. Title
    title = doc.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        errors.append("Field 'title' must be a non-empty string.")

    # 4. Company Subdocument
    company = doc.get("company")
    if not isinstance(company, dict):
        errors.append("Field 'company' must be an embedded dictionary.")
    else:
        for c_key in ["company_id", "name", "company_size", "industry"]:
            if c_key not in company:
                errors.append(f"Missing key '{c_key}' in 'company' subdocument.")

    # 5. Location Subdocument & Tri-State Remote
    location = doc.get("location")
    if not isinstance(location, dict):
        errors.append("Field 'location' must be an embedded dictionary.")
    else:
        for l_key in ["raw", "city", "state", "country", "zip_code", "is_remote"]:
            if l_key not in location:
                errors.append(f"Missing key '{l_key}' in 'location' subdocument.")
        # Tri-state validation: must be True, False, or None
        is_remote = location.get("is_remote")
        if is_remote is not None and not isinstance(is_remote, bool):
            errors.append(f"'location.is_remote' must be a boolean or null; found {type(is_remote).__name__}.")

    # 6. Salary Subdocument & Missing Salary Integrity
    salary = doc.get("salary")
    if not isinstance(salary, dict):
        errors.append("Field 'salary' must be an embedded dictionary.")
    else:
        for s_key in [
            "min_salary",
            "max_salary",
            "med_salary",
            "pay_period",
            "currency",
            "compensation_type",
            "normalized_annual",
            "salary_bucket",
            "estimated_midpoint",
        ]:
            if s_key not in salary:
                errors.append(f"Missing key '{s_key}' in 'salary' subdocument.")

        # Data integrity rule: Missing salaries must be null, never 0
        norm_annual = salary.get("normalized_annual")
        if norm_annual is not None and norm_annual == 0:
            errors.append("Integrity Violation: 'normalized_annual' cannot be 0. Missing salaries must be null.")

        min_sal = salary.get("min_salary")
        if min_sal is not None and min_sal == 0:
            errors.append("Integrity Violation: 'min_salary' cannot be 0. Missing salaries must be null.")

    # 7. Array Structures
    for arr_field in ["skills", "industries", "benefits"]:
        val = doc.get(arr_field)
        if not isinstance(val, list):
            errors.append(f"Field '{arr_field}' must be a list; found {type(val).__name__}.")

    # 8. Experience Level Provenance
    exp = doc.get("experience_level")
    if not isinstance(exp, dict):
        errors.append("Field 'experience_level' must be a dictionary.")
    else:
        if "value" not in exp or "status" not in exp:
            errors.append("'experience_level' must contain 'value' and 'status'.")
        elif exp.get("status") not in ("OBSERVED", "INFERRED", "NOT_AVAILABLE"):
            errors.append(f"Invalid 'experience_level.status': {exp.get('status')}.")

    # 9. Role Category
    role = doc.get("role_category")
    if not isinstance(role, dict):
        errors.append("Field 'role_category' must be a dictionary.")
    else:
        if "value" not in role or "status" not in role or "derived_from" not in role:
            errors.append("'role_category' must contain 'value', 'status', and 'derived_from'.")

    # 10. Source Data Subdocument
    source_data = doc.get("source_data")
    if not isinstance(source_data, dict):
        errors.append("Field 'source_data' must be a dictionary.")

    return len(errors) == 0, errors


def validate_company_document(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates a transformed company document against the Phase 2 supporting schema.
    Returns (is_valid, list_of_error_messages).
    """
    errors: List[str] = []
    required_keys = [
        "company_id",
        "name",
        "description",
        "company_size",
        "headquarters",
        "url",
        "industries",
        "specialities",
        "metrics",
        "ratings",
        "total_active_postings",
    ]
    for key in required_keys:
        if key not in doc:
            errors.append(f"Missing required company key: '{key}'")

    if not isinstance(doc.get("company_id"), int):
        errors.append("Field 'company_id' must be an integer.")

    name = doc.get("name")
    if not name or not isinstance(name, str):
        errors.append("Field 'name' must be a non-empty string.")

    if not isinstance(doc.get("headquarters"), dict):
        errors.append("Field 'headquarters' must be a dictionary.")

    if not isinstance(doc.get("industries"), list):
        errors.append("Field 'industries' must be a list.")

    if not isinstance(doc.get("specialities"), list):
        errors.append("Field 'specialities' must be a list.")

    return len(errors) == 0, errors
