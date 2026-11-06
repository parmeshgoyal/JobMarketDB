"""
JobMarketDB - Indeed Dataset Ingestion & Transformation

Extracts specialized Indeed postings, maps fields strictly according to
the Phase 2 schema, preserves authentic source semantics, and yields validated documents.
"""

import os
import zipfile
from typing import Any, Dict, Generator, List, Optional, Set

import pandas as pd

from ingestion.transformers import (
    calculate_estimated_midpoint,
    clean_text,
    estimate_posted_date_from_relative,
    extract_indeed_job_key,
    normalize_company_size,
    normalize_indeed_role_category,
    parse_indeed_skills,
    parse_job_location,
)
from ingestion.validators import validate_job_document


class IndeedExtractor:
    """
    Handles extraction and transformation of the Indeed job dataset.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = self._locate_dataset(data_path)
        self.is_zip = zipfile.is_zipfile(self.data_path) if os.path.isfile(self.data_path) else False
        self.zip_ref: Optional[zipfile.ZipFile] = None
        if self.is_zip:
            self.zip_ref = zipfile.ZipFile(self.data_path, "r")

        # Execution metrics
        self.metrics: Dict[str, int] = {
            "total_source_postings": 0,
            "transformed_postings": 0,
            "rejected_postings": 0,
            "duplicate_source_ids": 0,
            "missing_skills": 0,
            "missing_companies": 0,
            "missing_descriptions": 0,
        }

    def _locate_dataset(self, custom_path: Optional[str]) -> str:
        """Finds the Indeed CSV file or zip archive."""
        if custom_path and os.path.exists(custom_path):
            return custom_path

        candidates = [
            r"C:\ADBMS PROJECT\indeed_job_dataset.csv\indeed_job_dataset.csv",
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "indeed_job_dataset.csv", "indeed_job_dataset.csv")
            ),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datasets", "indeed_job_dataset.csv.zip")),
            r"C:\ADBMS PROJECT\JobMarketDB\datasets\indeed_job_dataset.csv.zip",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        raise FileNotFoundError("Could not locate Indeed dataset CSV or zip archive.")

    def _open_csv(self) -> Any:
        """Opens the CSV from either file path or zip archive."""
        if self.is_zip and self.zip_ref:
            return self.zip_ref.open("indeed_job_dataset.csv")
        return self.data_path

    def transform_posting(self, row: pd.Series, row_idx: int) -> Optional[Dict[str, Any]]:
        """
        Transforms a single Indeed record into the Phase 2 MongoDB job document.
        """
        # Job Identifier: authentic source key extracted from URL (not modified)
        link_url = clean_text(row.get("Link")) or ""
        source_job_id_str = extract_indeed_job_key(link_url, row_idx)

        # Title & Description
        title = clean_text(row.get("Job_Title"))
        if not title:
            return None
        description = clean_text(row.get("Description"))
        if not description:
            self.metrics["missing_descriptions"] += 1

        # Company Snapshot
        company_name = clean_text(row.get("Company"))
        if not company_name:
            self.metrics["missing_companies"] += 1

        company_size_str = normalize_company_size(row.get("Company_Employees"))
        company_industry_str = clean_text(row.get("Company_Industry"))

        company_snapshot = {
            "company_id": None,  # Indeed does not have numeric company IDs
            "name": company_name,
            "company_size": company_size_str,
            "industry": company_industry_str,
        }

        # Location Parsing (Tri-state remote: null for Indeed since unknown in source)
        location_doc = parse_job_location(
            raw_location=row.get("Location"),
            raw_zip_code=None,
            is_remote=None,  # Tri-state boolean: unknown in source -> null (never defaulted to False)
        )

        # Salary Subdocument (Range never converted to exact)
        queried_salary_bucket = clean_text(row.get("Queried_Salary"))
        estimated_mid = calculate_estimated_midpoint(queried_salary_bucket)

        salary_doc = {
            "min_salary": None,
            "max_salary": None,
            "med_salary": None,
            "pay_period": None,
            "currency": "USD",
            "compensation_type": "QUERY_BUCKET",
            "normalized_annual": None,  # Stated ranges are NEVER converted into fake exact salaries
            "salary_bucket": queried_salary_bucket,
            "estimated_midpoint": estimated_mid,  # Explicitly marked as a DERIVED estimate
        }

        # Authentic Source Skills
        skills_list = parse_indeed_skills(row.get("Skill"), row.to_dict())
        if not skills_list:
            self.metrics["missing_skills"] += 1

        # Industries
        industries_list: List[str] = []
        if company_industry_str:
            industries_list.append(company_industry_str)

        industry_flags = [
            "Consulting and Business Services",
            "Internet and Software",
            "Banks and Financial Services",
            "Health Care",
            "Insurance",
        ]
        for ind_col in industry_flags:
            if ind_col in row and row[ind_col] in (1, 1.0, "1", "1.0", True):
                if ind_col not in industries_list:
                    industries_list.append(ind_col)

        # Employment Type (Indeed has NO native employment type column)
        src_emp_type = None
        norm_emp_type = None

        # Experience Level (No native field in Indeed)
        experience_level_doc = {
            "value": None,
            "status": "NOT_AVAILABLE",
        }

        # Role Category (Normalized from source Job_Type discipline)
        role_category_doc = normalize_indeed_role_category(row.get("Job_Type"))

        # Publication Date (Native timestamp NOT AVAILABLE; estimated from relative days)
        date_since_posted = float(row.get("Date_Since_Posted")) if pd.notna(row.get("Date_Since_Posted")) else None
        estimated_posted_iso = estimate_posted_date_from_relative(date_since_posted)

        # Tool indicator flags
        tool_indicators = {}
        for tool_key in [
            "python",
            "sql",
            "machine learning",
            "r",
            "hadoop",
            "tableau",
            "sas",
            "spark",
            "java",
            "Others",
        ]:
            if tool_key in row:
                tool_indicators[tool_key.replace(" ", "_").lower()] = int(row[tool_key]) if pd.notna(row[tool_key]) else 0

        # Source-specific metadata container
        source_data_doc = {
            "indeed": {
                "row_index": row_idx,
                "source_job_id_extracted_from_url": True,
                "date_since_posted_days": date_since_posted,
                "company_revenue": clean_text(row.get("Company_Revenue")),
                "company_employees_category": clean_text(row.get("Company_Employees")),
                "company_reviews_count": float(row.get("No_of_Reviews")) if pd.notna(row.get("No_of_Reviews")) else None,
                "company_star_rating": float(row.get("No_of_Stars")) if pd.notna(row.get("No_of_Stars")) else None,
                "skill_count": int(row.get("No_of_Skills")) if pd.notna(row.get("No_of_Skills")) else len(skills_list),
                "tool_indicators": tool_indicators,
            }
        }

        doc = {
            "source": "indeed",
            "source_job_id": source_job_id_str,
            "title": title,
            "description": description,
            "company": company_snapshot,
            "location": location_doc,
            "salary": salary_doc,
            "skills": skills_list,
            "industries": industries_list,
            "benefits": [],  # Indeed has no benefits table
            "source_employment_type": src_emp_type,
            "normalized_employment_type": norm_emp_type,
            "experience_level": experience_level_doc,
            "role_category": role_category_doc,
            "job_url": link_url,
            "application_url": None,
            "application_type": "IndeedApply",
            "posted_date": None,  # Native publication date not available in source
            "estimated_posted_date": estimated_posted_iso,  # DERIVED / ESTIMATED
            "expiry_date": None,
            "views_count": None,
            "applies_count": None,
            "is_sponsored": False,
            "source_data": source_data_doc,
        }

        # Validate against schema
        is_valid, validation_errors = validate_job_document(doc)
        if not is_valid:
            self.metrics["rejected_postings"] += 1
            return None

        self.metrics["transformed_postings"] += 1
        return doc

    def extract_postings(self, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Reads and transforms indeed_job_dataset.csv.
        Enforces deduplication: preserves authentic source_job_id, skips duplicates,
        and records duplicate metrics.
        """
        csv_file = self._open_csv()
        df = pd.read_csv(csv_file, low_memory=False)
        self.metrics["total_source_postings"] = len(df)
        seen_job_ids: Set[str] = set()

        count = 0
        for idx, row in df.iterrows():
            doc = self.transform_posting(row, idx)
            if doc:
                job_key = doc["source_job_id"]
                if job_key in seen_job_ids:
                    self.metrics["duplicate_source_ids"] += 1
                    continue  # Skip subsequent duplicate, retain first occurrence without modifying ID
                seen_job_ids.add(job_key)
                yield doc
                count += 1
                if limit and count >= limit:
                    return
