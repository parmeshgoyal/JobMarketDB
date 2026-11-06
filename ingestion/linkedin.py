"""
JobMarketDB - LinkedIn Dataset Ingestion & Transformation

Extracts relational LinkedIn tables, joins foreign-key relationships,
applies Phase 2 schema transformations, and yields validated MongoDB-ready documents.
"""

import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

import pandas as pd

from ingestion.transformers import (
    clean_text,
    derive_role_category_from_title,
    normalize_company_size,
    normalize_salary_bucket,
    parse_epoch_to_iso,
    parse_job_location,
    parse_remote_status,
)
from ingestion.validators import validate_company_document, validate_job_document


class LinkedInExtractor:
    """
    Handles extraction, relational joining, and transformation of the LinkedIn dataset.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = self._locate_dataset(data_path)
        self.is_zip = zipfile.is_zipfile(self.data_path) if os.path.isfile(self.data_path) else False
        self.zip_ref: Optional[zipfile.ZipFile] = None
        if self.is_zip:
            self.zip_ref = zipfile.ZipFile(self.data_path, "r")

        # In-memory relational mapping stores
        self.skills_map: Dict[str, str] = {}
        self.industries_map: Dict[int, str] = {}
        self.job_skills: Dict[int, List[str]] = {}
        self.job_industries: Dict[int, List[str]] = {}
        self.job_benefits: Dict[int, List[str]] = {}
        self.companies_data: Dict[int, Dict[str, Any]] = {}
        self.company_industries: Dict[int, List[str]] = {}
        self.company_specialities: Dict[int, List[str]] = {}
        self.latest_employee_counts: Dict[int, Dict[str, Any]] = {}
        self.company_posting_counts: Dict[int, int] = {}

        # Execution metrics
        self.metrics: Dict[str, int] = {
            "total_source_postings": 0,
            "transformed_postings": 0,
            "rejected_postings": 0,
            "duplicate_source_ids": 0,
            "missing_company_links": 0,
            "unstated_salaries": 0,
            "unstated_skills": 0,
            "unstated_industries": 0,
            "unstated_benefits": 0,
            "total_companies_transformed": 0,
        }

    def _locate_dataset(self, custom_path: Optional[str]) -> str:
        """Finds the LinkedIn archive either as directory or zip file."""
        if custom_path and os.path.exists(custom_path):
            return custom_path

        candidates = [
            r"C:\ADBMS PROJECT\archive",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "archive")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datasets", "archive.zip")),
            r"C:\ADBMS PROJECT\JobMarketDB\datasets\archive.zip",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        raise FileNotFoundError("Could not locate LinkedIn dataset archive or uncompressed folder.")

    def _open_csv(self, relative_path: str) -> Any:
        """Opens a CSV from either the uncompressed folder or the zip archive."""
        if self.is_zip and self.zip_ref:
            zip_name = relative_path.replace("\\", "/")
            return self.zip_ref.open(zip_name)
        else:
            full_path = os.path.join(self.data_path, relative_path)
            return full_path

    def load_relational_lookups(self) -> None:
        """
        Loads all relational bridge and lookup tables into in-memory dictionaries
        for high-performance joining during streaming.
        """
        print("[LinkedIn ETL] Loading relational lookups and mappings...")

        # 1. Skills Mapping (abr -> descriptive name)
        df_sm = pd.read_csv(self._open_csv(os.path.join("mappings", "skills.csv")))
        self.skills_map = dict(zip(df_sm["skill_abr"], df_sm["skill_name"]))

        # 2. Industries Mapping (id -> descriptive name)
        df_im = pd.read_csv(self._open_csv(os.path.join("mappings", "industries.csv"))).dropna(subset=["industry_name"])
        self.industries_map = dict(zip(df_im["industry_id"].astype(int), df_im["industry_name"]))

        # 3. Job Skills Bridge
        df_js = pd.read_csv(self._open_csv(os.path.join("jobs", "job_skills.csv")))
        df_js["skill_name"] = df_js["skill_abr"].map(self.skills_map)
        self.job_skills = df_js.dropna(subset=["skill_name"]).groupby("job_id")["skill_name"].apply(list).to_dict()

        # 4. Job Industries Bridge
        df_ji = pd.read_csv(self._open_csv(os.path.join("jobs", "job_industries.csv")))
        df_ji["ind_name"] = df_ji["industry_id"].map(self.industries_map)
        self.job_industries = df_ji.dropna(subset=["ind_name"]).groupby("job_id")["ind_name"].apply(list).to_dict()

        # 5. Benefits Table
        df_ben = pd.read_csv(self._open_csv(os.path.join("jobs", "benefits.csv")))
        self.job_benefits = df_ben.groupby("job_id")["type"].apply(lambda x: list(dict.fromkeys(x))).to_dict()

        # 6. Company Master Profiles
        df_comp = pd.read_csv(self._open_csv(os.path.join("companies", "companies.csv")))
        self.companies_data = df_comp.set_index("company_id").to_dict("index")

        # 7. Company Industries
        df_ci = pd.read_csv(self._open_csv(os.path.join("companies", "company_industries.csv")))
        self.company_industries = df_ci.groupby("company_id")["industry"].apply(list).to_dict()

        # 8. Company Specialities
        df_cs = pd.read_csv(self._open_csv(os.path.join("companies", "company_specialities.csv")))
        self.company_specialities = df_cs.groupby("company_id")["speciality"].apply(list).to_dict()

        # 9. Latest Employee and Follower Counts
        df_emp = pd.read_csv(self._open_csv(os.path.join("companies", "employee_counts.csv")))
        df_emp_sorted = df_emp.sort_values("time_recorded")
        self.latest_employee_counts = df_emp_sorted.groupby("company_id").last().to_dict("index")

        print(
            f"[LinkedIn ETL] Preloaded: {len(self.job_skills):,} skill sets, "
            f"{len(self.job_industries):,} industry sets, "
            f"{len(self.job_benefits):,} benefit sets, "
            f"{len(self.companies_data):,} company profiles."
        )

    def transform_posting(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Transforms a single LinkedIn posting record into the Phase 2 MongoDB job document.
        """
        raw_job_id = row.get("job_id")
        if pd.isna(raw_job_id):
            return None
        job_id_int = int(raw_job_id)
        source_job_id_str = str(job_id_int)

        # Title & Description
        title = clean_text(row.get("title"))
        if not title:
            return None
        description = clean_text(row.get("description"))

        # Company Reference & Snapshot
        company_id_val = row.get("company_id")
        company_id_int = int(company_id_val) if pd.notna(company_id_val) else None
        company_profile = self.companies_data.get(company_id_int, {}) if company_id_int else {}

        if company_id_int and not company_profile:
            self.metrics["missing_company_links"] += 1

        company_name = clean_text(row.get("company_name")) or clean_text(company_profile.get("name"))
        company_size_str = normalize_company_size(company_profile.get("company_size"))

        # Company Industry: from company profile industries
        comp_inds = self.company_industries.get(company_id_int, []) if company_id_int else []
        primary_company_industry = comp_inds[0] if comp_inds else None

        company_snapshot = {
            "company_id": company_id_int,
            "name": company_name,
            "company_size": company_size_str,
            "industry": primary_company_industry,
        }

        # Track active postings per company for supporting collection
        if company_id_int:
            self.company_posting_counts[company_id_int] = self.company_posting_counts.get(company_id_int, 0) + 1

        # Remote status: proper tri-state handling (1.0 -> True, 0.0 -> False, NaN -> None)
        is_remote_val = parse_remote_status(row.get("remote_allowed"))

        # Job Location Parsing: Strictly from job posting source fields without company fallback
        location_doc = parse_job_location(
            raw_location=row.get("location"),
            raw_zip_code=row.get("zip_code"),
            is_remote=is_remote_val,
        )

        # Salary Parsing (Missing salaries remain None, never 0)
        norm_sal = float(row.get("normalized_salary")) if pd.notna(row.get("normalized_salary")) else None
        min_sal = float(row.get("min_salary")) if pd.notna(row.get("min_salary")) else None
        max_sal = float(row.get("max_salary")) if pd.notna(row.get("max_salary")) else None
        med_sal = float(row.get("med_salary")) if pd.notna(row.get("med_salary")) else None

        if norm_sal is None and min_sal is None and max_sal is None:
            self.metrics["unstated_salaries"] += 1
            salary_bucket = None
        else:
            salary_bucket = normalize_salary_bucket(norm_sal or max_sal or min_sal)

        salary_doc = {
            "min_salary": min_sal,
            "max_salary": max_sal,
            "med_salary": med_sal,
            "pay_period": clean_text(row.get("pay_period")),
            "currency": clean_text(row.get("currency")) or "USD",
            "compensation_type": clean_text(row.get("compensation_type")) or "BASE_SALARY",
            "normalized_annual": norm_sal,
            "salary_bucket": salary_bucket,
            "estimated_midpoint": None,  # Not estimated; LinkedIn has exact stated numbers
        }

        # Skills & Industries (Preserving authentic source categories)
        skills_list = self.job_skills.get(job_id_int, [])
        if not skills_list:
            self.metrics["unstated_skills"] += 1

        industries_list = self.job_industries.get(job_id_int, [])
        if not industries_list:
            if primary_company_industry:
                industries_list = [primary_company_industry]
            else:
                self.metrics["unstated_industries"] += 1

        # Benefits (LinkedIn source)
        benefits_list = self.job_benefits.get(job_id_int, [])
        if not benefits_list:
            self.metrics["unstated_benefits"] += 1

        # Employment Type (Source vs Normalized)
        src_emp_type = clean_text(row.get("formatted_work_type"))
        norm_emp_type = src_emp_type  # Standardized directly from LinkedIn source categories

        # Experience Level (Observed provenance)
        exp_raw = clean_text(row.get("formatted_experience_level"))
        if exp_raw:
            experience_level_doc = {
                "value": exp_raw,
                "status": "OBSERVED",
            }
        else:
            experience_level_doc = {
                "value": None,
                "status": "NOT_AVAILABLE",
            }

        # Role Category (Derived/Inferred from title)
        role_category_doc = derive_role_category_from_title(title)

        # Dates & Metrics
        posted_date_iso = parse_epoch_to_iso(row.get("original_listed_time") or row.get("listed_time"))
        expiry_date_iso = parse_epoch_to_iso(row.get("expiry"))

        views = int(row.get("views")) if pd.notna(row.get("views")) else None
        applies = int(row.get("applies")) if pd.notna(row.get("applies")) else None
        is_sponsored = bool(row.get("sponsored") == 1)

        # Source-specific metadata container
        source_data_doc = {
            "linkedin": {
                "fips": float(row.get("fips")) if pd.notna(row.get("fips")) else None,
                "posting_domain": clean_text(row.get("posting_domain")),
                "closed_time": parse_epoch_to_iso(row.get("closed_time")),
                "skills_desc": clean_text(row.get("skills_desc")),
            }
        }

        doc = {
            "source": "linkedin",
            "source_job_id": source_job_id_str,
            "title": title,
            "description": description,
            "company": company_snapshot,
            "location": location_doc,
            "salary": salary_doc,
            "skills": skills_list,
            "industries": industries_list,
            "benefits": benefits_list,
            "source_employment_type": src_emp_type,
            "normalized_employment_type": norm_emp_type,
            "experience_level": experience_level_doc,
            "role_category": role_category_doc,
            "job_url": clean_text(row.get("job_posting_url")) or f"https://www.linkedin.com/jobs/view/{job_id_int}",
            "application_url": clean_text(row.get("application_url")),
            "application_type": clean_text(row.get("application_type")),
            "posted_date": posted_date_iso,
            "estimated_posted_date": None,
            "expiry_date": expiry_date_iso,
            "views_count": views,
            "applies_count": applies,
            "is_sponsored": is_sponsored,
            "source_data": source_data_doc,
        }

        # Validate against schema
        is_valid, validation_errors = validate_job_document(doc)
        if not is_valid:
            self.metrics["rejected_postings"] += 1
            return None

        self.metrics["transformed_postings"] += 1
        return doc

    def extract_postings(
        self, chunk_size: int = 15000, limit: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams and transforms postings.csv in chunks to prevent memory bloat.
        Enforces deduplication: preserves authentic source_job_id, skips duplicates,
        and records duplicate metrics.
        """
        postings_csv = self._open_csv("postings.csv")
        seen_job_ids: Set[str] = set()
        count = 0

        for chunk in pd.read_csv(postings_csv, chunksize=chunk_size, low_memory=False):
            self.metrics["total_source_postings"] += len(chunk)
            for _, row in chunk.iterrows():
                doc = self.transform_posting(row)
                if doc:
                    job_key = doc["source_job_id"]
                    if job_key in seen_job_ids:
                        self.metrics["duplicate_source_ids"] += 1
                        continue  # Skip subsequent duplicate, retain first occurrence
                    seen_job_ids.add(job_key)
                    yield doc
                    count += 1
                    if limit and count >= limit:
                        return

    def extract_companies(self) -> Generator[Dict[str, Any], None, None]:
        """
        Transforms company master profiles into the supporting 'companies' collection format.
        """
        for comp_id, comp_row in self.companies_data.items():
            name = clean_text(comp_row.get("name"))
            if not name:
                continue

            emp_data = self.latest_employee_counts.get(comp_id, {})
            emp_count = int(emp_data.get("employee_count")) if pd.notna(emp_data.get("employee_count")) else None
            foll_count = int(emp_data.get("follower_count")) if pd.notna(emp_data.get("follower_count")) else None
            last_recorded = parse_epoch_to_iso(emp_data.get("time_recorded") * 1000) if pd.notna(emp_data.get("time_recorded")) else None

            headquarters = {
                "city": clean_text(comp_row.get("city")),
                "state": clean_text(comp_row.get("state")),
                "country": clean_text(comp_row.get("country")) or "US",
                "zip_code": clean_text(str(comp_row.get("zip_code")) if pd.notna(comp_row.get("zip_code")) else None),
                "address": clean_text(comp_row.get("address")),
            }

            company_doc = {
                "company_id": int(comp_id),
                "name": name,
                "description": clean_text(comp_row.get("description")),
                "company_size": normalize_company_size(comp_row.get("company_size")),
                "headquarters": headquarters,
                "url": clean_text(comp_row.get("url")),
                "industries": self.company_industries.get(comp_id, []),
                "specialities": self.company_specialities.get(comp_id, []),
                "metrics": {
                    "latest_employee_count": emp_count,
                    "latest_follower_count": foll_count,
                    "last_recorded_at": last_recorded,
                },
                "ratings": {
                    "stars": None,
                    "reviews_count": None,
                },
                "total_active_postings": self.company_posting_counts.get(comp_id, 0),
            }

            is_valid, errors = validate_company_document(company_doc)
            if is_valid:
                self.metrics["total_companies_transformed"] += 1
                yield company_doc
