"""
JobMarketDB - Ingestion & Data Transformation Utilities

Provides robust parsing, cleaning, normalization, and provenance-compliant
transformation functions for LinkedIn and Indeed datasets.
"""

import ast
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Comprehensive US 50 States + DC + Territories Mapping
US_STATE_MAP = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "puerto rico": "PR",
    "guam": "GU",
    "virgin islands": "VI",
}

VALID_US_POSTAL_CODES = set(US_STATE_MAP.values())

# Prominent US Metropolitan Area string mappings to (City, State)
METRO_MAP = {
    "new york city metropolitan area": ("New York", "NY"),
    "san francisco bay area": ("San Francisco", "CA"),
    "greater phoenix area": ("Phoenix", "AZ"),
    "dallas-fort worth metroplex": ("Dallas", "TX"),
    "greater boston area": ("Boston", "MA"),
    "greater chicago area": ("Chicago", "IL"),
    "greater seattle area": ("Seattle", "WA"),
    "greater philadelphia area": ("Philadelphia", "PA"),
    "greater houston": ("Houston", "TX"),
    "greater los angeles area": ("Los Angeles", "CA"),
    "washington dc-baltimore area": ("Washington", "DC"),
    "greater atlanta area": ("Atlanta", "GA"),
    "greater minneapolis-st. paul area": ("Minneapolis", "MN"),
    "tampa bay area": ("Tampa", "FL"),
    "greater orlando area": ("Orlando", "FL"),
    "greater austin": ("Austin", "TX"),
    "greater st. louis": ("St Louis", "MO"),
}


def clean_text(text: Any) -> Optional[str]:
    """
    Strips raw HTML tags, collapses extraneous whitespace, and trims strings.
    Returns None for null, NaN, 'nan', 'none', or empty inputs.
    """
    if text is None:
        return None
    if isinstance(text, float) and text != text:
        return None
    s = str(text).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    cleaned = re.sub(r"<[^>]+>", " ", s)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned and cleaned.lower() not in ("nan", "none", "null") else None


def normalize_us_state(val: Any) -> Optional[str]:
    """
    Explicit normalization function for US states.
    - If already a valid 2-letter postal code (e.g., 'OH', 'NJ', 'CA'), preserves it.
    - If a full state name (e.g., 'Ohio', 'New Jersey', 'California'), maps to postal code.
    - If unresolvable or non-US, returns None.
    - Never leaves arbitrary full state names or country strings in location.state.
    """
    if val is None or (isinstance(val, float) and val != val):
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", ""):
        return None

    s_upper = s.upper()
    if s_upper in VALID_US_POSTAL_CODES:
        return s_upper

    s_lower = s.lower()
    if s_lower in US_STATE_MAP:
        return US_STATE_MAP[s_lower]

    if s_lower in ("dc", "d.c.", "district of columbia"):
        return "DC"

    return None


def parse_job_location(
    raw_location: Any,
    raw_zip_code: Any = None,
    is_remote: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Parses a job posting's OWN location fields strictly without fallback to company HQ.
    - If job location is unavailable, city, state, and zip_code remain None.
    - Location.state consistently contains a normalized 2-letter US postal code or None.
    - Location.zip_code comes solely from the job record's zip_code.
    """
    raw_str = clean_text(raw_location)
    zip_clean = clean_text(raw_zip_code)
    if zip_clean and zip_clean.endswith(".0"):
        zip_clean = zip_clean[:-2]

    if not raw_str:
        return {
            "raw": None,
            "city": None,
            "state": None,
            "country": "United States",
            "zip_code": zip_clean,
            "is_remote": is_remote,
        }

    raw_lower = raw_str.lower()
    city: Optional[str] = None
    state: Optional[str] = None

    # Check known metropolitan area definitions first
    matched_metro = False
    for metro_key, (m_city, m_state) in METRO_MAP.items():
        if metro_key in raw_lower:
            city = m_city
            state = m_state
            matched_metro = True
            break

    if not matched_metro:
        if "," in raw_str:
            parts = [p.strip() for p in raw_str.split(",")]
            p0 = clean_text(parts[0])
            p1 = clean_text(parts[1]) if len(parts) > 1 else None

            if p1:
                st_from_p1 = normalize_us_state(p1)
                if st_from_p1:
                    state = st_from_p1
                    city = p0
                elif p1.lower() in ("united states", "us", "usa"):
                    # e.g., 'California, United States' or 'New York, United States'
                    if p0:
                        st_from_p0 = normalize_us_state(p0)
                        if st_from_p0:
                            state = st_from_p0
                            city = p0 if p0.lower() == "new york" else None
                        else:
                            city = p0
                else:
                    # Check for 2-letter state code pattern in p1
                    match = re.search(r"\b([A-Z]{2})\b", p1)
                    if match:
                        st_match = normalize_us_state(match.group(1))
                        if st_match:
                            state = st_match
                            city = p0
        else:
            # Single term without comma: check if it is a state name or code
            st_direct = normalize_us_state(raw_str)
            if st_direct:
                state = st_direct
                city = None

    return {
        "raw": raw_str,
        "city": city,
        "state": state,
        "country": "United States",
        "zip_code": zip_clean,
        "is_remote": is_remote,
    }


def parse_remote_status(val: Any) -> Optional[bool]:
    """
    Strict tri-state remote boolean parser:
    - 1 / 1.0 / True -> True (explicitly confirmed remote)
    - 0 / 0.0 / False -> False (explicitly confirmed on-site)
    - NaN / None / missing -> None (unknown / unstated)
    Missing is NEVER treated as False.
    """
    if val is None or (isinstance(val, float) and val != val):
        return None
    try:
        f = float(val)
        if f == 1.0:
            return True
        elif f == 0.0:
            return False
    except (ValueError, TypeError):
        pass
    s = str(val).strip().lower()
    if s in ("1", "1.0", "true"):
        return True
    elif s in ("0", "0.0", "false"):
        return False
    return None


def parse_epoch_to_iso(epoch_ms: Any) -> Optional[str]:
    """
    Converts epoch milliseconds to an ISO 8601 UTC timestamp string.
    Returns None if missing, NaN, or non-positive.
    """
    if epoch_ms is None:
        return None
    try:
        val = float(epoch_ms)
        if val <= 0 or val != val:
            return None
        dt = datetime.fromtimestamp(val / 1000.0, tz=timezone.utc)
        return dt.isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def estimate_posted_date_from_relative(
    days_ago: Any,
    reference_date: Optional[datetime] = None,
) -> Optional[str]:
    """
    Calculates an estimated posting date from relative days elapsed.
    Derived estimate based on dataset reference collection date (April 2024).
    """
    if days_ago is None:
        return None
    try:
        days = float(days_ago)
        if days != days and days < 0:
            return None
        if reference_date is None:
            reference_date = datetime(2024, 4, 1, tzinfo=timezone.utc)
        from datetime import timedelta

        estimated_dt = reference_date - timedelta(days=days)
        return estimated_dt.isoformat()
    except (ValueError, OverflowError):
        return None


def normalize_salary_bucket(annual_amount: Optional[float]) -> Optional[str]:
    """
    Categorizes a continuous annual salary figure into the 6 standardized query bands.
    Returns None if salary is missing or non-positive.
    """
    if annual_amount is None:
        return None
    try:
        val = float(annual_amount)
        if val <= 0 or val != val:
            return None
        if val < 80000.0:
            return "<80000"
        elif val < 100000.0:
            return "80000-99999"
        elif val < 120000.0:
            return "100000-119999"
        elif val < 140000.0:
            return "120000-139999"
        elif val < 160000.0:
            return "140000-159999"
        else:
            return ">160000"
    except (ValueError, TypeError):
        return None


def calculate_estimated_midpoint(bucket_str: Optional[str]) -> Optional[float]:
    """
    Calculates an estimated midpoint for a discrete salary range.
    Documented explicitly as a DERIVED / INFERRED estimate for analytical convenience.
    """
    if not bucket_str or not isinstance(bucket_str, str):
        return None
    cleaned = bucket_str.strip()
    midpoint_map = {
        "<80000": 70000.0,
        "80000-99999": 90000.0,
        "100000-119999": 110000.0,
        "120000-139999": 130000.0,
        "140000-159999": 150000.0,
        ">160000": 175000.0,
    }
    return midpoint_map.get(cleaned)


def normalize_company_size(size_val: Any) -> Optional[str]:
    """
    Standardizes company size representations into uniform headcount brackets.
    Handles LinkedIn 1.0-7.0 scale and Indeed string buckets.
    """
    if size_val is None or (isinstance(size_val, float) and size_val != size_val):
        return None
    s = str(size_val).strip()
    if s.lower() in ("nan", "none", "null", ""):
        return None

    numeric_map = {
        "1.0": "1-10",
        "1": "1-10",
        "2.0": "11-50",
        "2": "11-50",
        "3.0": "51-200",
        "3": "51-200",
        "4.0": "201-500",
        "4": "201-500",
        "5.0": "501-1000",
        "5": "501-1000",
        "6.0": "1001-5000",
        "6": "1001-5000",
        "7.0": "5001-10000",
        "7": "5001-10000",
    }
    if s in numeric_map:
        return numeric_map[s]

    if "10,000+" in s or ">10,000" in s:
        return "10,000+"
    if "Less than 10,000" in s or "<10,000" in s:
        return "Less than 10,000"
    return s if s else None


def derive_role_category_from_title(title: Optional[str]) -> Dict[str, str]:
    """
    Application-level derived/inferred field for cross-dataset analytics.
    Classifies job title keywords into standard role categories.
    """
    if not title:
        return {
            "value": "Other",
            "status": "DERIVED / INFERRED",
            "derived_from": "title",
        }
    t = title.lower()
    if "data scientist" in t or "data science" in t:
        cat = "Data Scientist"
    elif "data analyst" in t or "business intelligence" in t or "bi analyst" in t or "analytics" in t:
        cat = "Data Analyst"
    elif "data engineer" in t or "big data" in t or "etl" in t:
        cat = "Data Engineer"
    elif "machine learning" in t or "ml engineer" in t or "ai engineer" in t or "deep learning" in t:
        cat = "Machine Learning Engineer"
    elif "software engineer" in t or "developer" in t or "programmer" in t:
        cat = "Software Engineer"
    elif "product manager" in t or "project manager" in t:
        cat = "Management"
    elif "sales" in t or "account executive" in t:
        cat = "Sales"
    elif "nurse" in t or "medical" in t or "health" in t:
        cat = "Healthcare"
    else:
        cat = "Other"

    return {
        "value": cat,
        "status": "DERIVED / INFERRED",
        "derived_from": "title",
    }


def normalize_indeed_role_category(job_type_str: Optional[str]) -> Dict[str, str]:
    """
    Normalizes Indeed's source Job_Type discipline into the standard role category.
    """
    if not job_type_str:
        return {
            "value": "Other",
            "status": "NORMALIZED",
            "derived_from": "Job_Type",
        }
    val = str(job_type_str).lower().strip()
    mapping = {
        "data_scientist": "Data Scientist",
        "data_analyst": "Data Analyst",
        "data_engineer": "Data Engineer",
    }
    return {
        "value": mapping.get(val, "Other"),
        "status": "NORMALIZED",
        "derived_from": "Job_Type",
    }


def parse_indeed_skills(skill_text: Any, row_dict: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Parses authentic source skills from Indeed's Skill stringified list and binary flags.
    Preserves exact source tool names without artificial cross-mapping.
    """
    skills: List[str] = []
    seen: set = set()

    if skill_text and isinstance(skill_text, str) and skill_text.strip():
        s = skill_text.strip()
        try:
            if s.startswith("[") and s.endswith("]"):
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    for item in parsed:
                        item_clean = clean_text(item)
                        if item_clean and item_clean.lower() not in seen:
                            seen.add(item_clean.lower())
                            skills.append(item_clean)
            else:
                for item in s.split(","):
                    item_clean = clean_text(item)
                    if item_clean and item_clean.lower() not in seen:
                        seen.add(item_clean.lower())
                        skills.append(item_clean)
        except (ValueError, SyntaxError):
            pass

    if row_dict:
        flag_tools = [
            ("python", "Python"),
            ("sql", "SQL"),
            ("machine learning", "Machine Learning"),
            ("r", "R"),
            ("hadoop", "Hadoop"),
            ("tableau", "Tableau"),
            ("sas", "SAS"),
            ("spark", "Spark"),
            ("java", "Java"),
        ]
        for col_name, tool_name in flag_tools:
            if col_name in row_dict:
                flag_val = row_dict[col_name]
                if flag_val in (1, 1.0, "1", "1.0", True):
                    if tool_name.lower() not in seen:
                        seen.add(tool_name.lower())
                        skills.append(tool_name)

    return skills


def extract_indeed_job_key(link: Any, row_idx: int) -> str:
    """
    Extracts Indeed's authentic job key (jk) query parameter from the URL.
    Documented: Indeed has no native job_id column; this is extracted from the URL.
    """
    if link and isinstance(link, str):
        match = re.search(r"jk=([a-zA-Z0-9]+)", link)
        if match:
            return match.group(1)
    return f"IND_{row_idx}"
