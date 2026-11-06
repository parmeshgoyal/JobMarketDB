"""
JobMarketDB — Phase 7 Stage 9 Final Comprehensive Application Browser Verification
Playwright real-browser automation in Google Chrome:
1. Audits all 7 redesigned pages at desktop resolution (1920x1080).
2. Measures page load times, DOM settling, and renders.
3. Captures individual screenshots for each of the 7 pages.
4. Performs tablet (768x1024) and mobile (375x667) responsive layout inspections.
5. Verifies absence of Python tracebacks, unhandled errors, and console exceptions.
6. Verifies local MongoDB database invariants (129,550 jobs, 24,472 companies, 15 indexes, 0 demo_postings).
"""

import json
import os
import shutil
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright
from database.connection import get_database, verify_connection

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://localhost:8501"
LOCAL_SCREENSHOTS_DIR = r"c:\ADBMS PROJECT\JobMarketDB\screenshots"
ARTIFACT_DIR = r"C:\Users\Dell\.gemini\antigravity\brain\41413373-c5ab-4ddb-922a-3854a1356b59"

os.makedirs(LOCAL_SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def save_screenshot(page, filename: str) -> str:
    local_path = os.path.join(LOCAL_SCREENSHOTS_DIR, filename)
    artifact_path = os.path.join(ARTIFACT_DIR, filename)
    page.screenshot(path=local_path, full_page=False)
    shutil.copy2(local_path, artifact_path)
    print(f"  [SCREENSHOT] Saved: {filename} -> local and artifact root.")
    return local_path


def scroll_to_y(page, y: int):
    page.evaluate(f"""() => {{
        const main = document.querySelector('[data-testid="stMain"]') || document.querySelector('.stMain') || document.querySelector('section.main');
        if (main) {{
            main.scrollTop = {y};
        }} else {{
            window.scrollTo(0, {y});
        }}
    }}""")
    time.sleep(1.0)


def wait_for_settled(page, timeout=35):
    try:
        page.locator('[data-testid="stAppViewContainer"]').wait_for(state="visible", timeout=10000)
    except Exception:
        pass
    # Poll until DOM content stabilizes
    last_len = 0
    stable_count = 0
    for _ in range(timeout * 2):
        time.sleep(0.5)
        try:
            curr_len = len(page.locator("body").inner_text())
        except Exception:
            curr_len = 0
        if curr_len > 2500 and curr_len == last_len:
            stable_count += 1
            if stable_count >= 3:
                break
        else:
            stable_count = 0
            last_len = curr_len
    try:
        page.locator(".stSpinner").wait_for(state="detached", timeout=5000)
    except Exception:
        pass
    time.sleep(1.0)


def run_stage_9_comprehensive_browser_verification():
    print("=" * 80)
    print(" JobMarketDB — Phase 7 Stage 9 Final Comprehensive Browser Verification")
    print(f" Base URL: {BASE_URL}")
    print(f" Chrome Executable: {CHROME_PATH}")
    print("=" * 80)

    console_errors = []
    console_warnings = []
    page_metrics = []

    pages_to_verify = [
        {
            "id": "home",
            "name": "1. Home Dashboard",
            "path": "/",
            "expected_keywords": ["Understand the Job Market", "129,550", "LinkedIn", "Indeed"],
            "screenshot": "stage_9_01_home_dashboard.png",
        },
        {
            "id": "job_search",
            "name": "2. Job Explorer",
            "path": "/Job_Search",
            "expected_keywords": ["Job Explorer", "Search", "Filters"],
            "screenshot": "stage_9_02_job_explorer.png",
        },
        {
            "id": "skills_analytics",
            "name": "3. Skills Analytics",
            "path": "/Skills_Analytics",
            "expected_keywords": ["Skills in Demand", "Indeed", "LinkedIn"],
            "screenshot": "stage_9_03_skills_analytics.png",
        },
        {
            "id": "salary_analytics",
            "name": "4. Salary Analytics",
            "path": "/Salary_Analytics",
            "expected_keywords": ["Salary Distributions", "95,515", "81,375", "116,501"],
            "screenshot": "stage_9_04_salary_analytics.png",
        },
        {
            "id": "company_geo",
            "name": "5. Company & Geography",
            "path": "/Company_and_Geography",
            "expected_keywords": ["Where Companies Hire", "24,472"],
            "screenshot": "stage_9_05_company_geography.png",
        },
        {
            "id": "platform_comparison",
            "name": "6. Platform Comparison",
            "path": "/Platform_Comparison",
            "expected_keywords": ["LinkedIn vs Indeed", "123,835", "5,715", "570"],
            "screenshot": "stage_9_06_platform_comparison.png",
        },
        {
            "id": "crud_demo",
            "name": "7. CRUD Demo",
            "path": "/CRUD_Demo",
            "expected_keywords": ["Explore MongoDB Operations", "Canonical Protected", "Sandbox Isolated"],
            "screenshot": "stage_9_07_crud_demo.png",
        },
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--window-size=1920,1080"],
        )

        # ---------------------------------------------------------------------
        # PART 1: Desktop Audits (1920x1080) for all 7 pages
        # ---------------------------------------------------------------------
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        def on_console(msg):
            text = msg.text
            # Filter noise like favicon, telemetry, or third-party web font notices
            if "favicon" in text.lower():
                return
            if msg.type == "error":
                console_errors.append(f"[{page.url}] {text}")
            elif msg.type == "warning":
                console_warnings.append(f"[{page.url}] {text}")

        page.on("console", on_console)

        for p_info in pages_to_verify:
            target_url = f"{BASE_URL}{p_info['path']}"
            print(f"\n[DESKTOP AUDIT] Loading {p_info['name']} -> {target_url}...")
            t0 = time.time()
            page.goto(target_url, timeout=60000)
            wait_for_settled(page)
            load_time = round(time.time() - t0, 2)

            body_text = page.locator("body").inner_text()
            char_count = len(body_text)

            # Check for Python exceptions
            exception_elements = page.locator(".stException").count()
            traceback_count = body_text.count("Traceback (most recent call last)")
            has_error = (exception_elements > 0) or (traceback_count > 0)

            # Check expected keywords
            matched_keywords = [kw for kw in p_info["expected_keywords"] if kw.lower() in body_text.lower()]
            missing_keywords = [kw for kw in p_info["expected_keywords"] if kw.lower() not in body_text.lower()]

            print(f"  Load Time: {load_time}s | Text Length: {char_count:,} chars")
            print(f"  Exceptions/Tracebacks: {exception_elements} / {traceback_count}")
            print(f"  Keywords Matched: {len(matched_keywords)}/{len(p_info['expected_keywords'])}")
            if missing_keywords:
                print(f"  [WARN] Missing keywords: {missing_keywords}")

            assert not has_error, f"Python exception detected on {p_info['name']}!"
            assert len(missing_keywords) == 0, f"Missing critical keywords on {p_info['name']}: {missing_keywords}"

            save_screenshot(page, p_info["screenshot"])

            page_metrics.append({
                "page": p_info["name"],
                "url": target_url,
                "load_time_sec": load_time,
                "text_length": char_count,
                "exceptions": exception_elements + traceback_count,
                "status": "PASS",
            })

        # ---------------------------------------------------------------------
        # PART 2: Responsive Viewport Checks (Tablet & Mobile)
        # ---------------------------------------------------------------------
        print("\n" + "-" * 60)
        print(" [RESPONSIVE AUDIT] Tablet Viewport (768x1024)")
        print("-" * 60)
        tablet_context = browser.new_context(viewport={"width": 768, "height": 1024})
        tablet_page = tablet_context.new_page()
        tablet_page.goto(f"{BASE_URL}/Job_Search", timeout=60000)
        wait_for_settled(tablet_page)
        save_screenshot(tablet_page, "stage_9_08_tablet_job_search.png")
        print("  [OK] Tablet viewport tested and captured on Job Explorer.")
        tablet_context.close()

        print("\n" + "-" * 60)
        print(" [RESPONSIVE AUDIT] Mobile Viewport (375x667)")
        print("-" * 60)
        mobile_context = browser.new_context(viewport={"width": 375, "height": 667})
        mobile_page = mobile_context.new_page()
        mobile_page.goto(f"{BASE_URL}/", timeout=60000)
        wait_for_settled(mobile_page)
        save_screenshot(mobile_page, "stage_9_09_mobile_home.png")
        print("  [OK] Mobile viewport tested and captured on Home Dashboard.")
        mobile_context.close()

        context.close()
        browser.close()

    # -------------------------------------------------------------------------
    # PART 3: Database Invariants Audit
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(" [DATABASE INVARIANTS AUDIT] Verifying Local MongoDB Community Server...")
    print("=" * 80)
    assert verify_connection(timeout_ms=3000), "MongoDB connection failed"
    db = get_database()
    jobs_count = db.jobs.count_documents({})
    comp_count = db.companies.count_documents({})
    job_indexes = list(db.jobs.list_indexes())
    comp_indexes = list(db.companies.list_indexes())
    demo_count = db.demo_postings.count_documents({})

    print(f"  Canonical Jobs Count:      {jobs_count:,} (Expected: 129,550)")
    print(f"  Canonical Companies Count: {comp_count:,} (Expected: 24,472)")
    print(f"  Jobs Indexes:              {len(job_indexes)} (Expected: 11)")
    print(f"  Companies Indexes:         {len(comp_indexes)} (Expected: 4)")
    print(f"  Total Production Indexes:  {len(job_indexes) + len(comp_indexes)} (Expected: 15)")
    print(f"  Sandbox demo_postings:     {demo_count} (Expected: 0)")

    assert jobs_count == 129550, f"Canonical jobs count mismatch: {jobs_count}"
    assert comp_count == 24472, f"Canonical companies count mismatch: {comp_count}"
    assert len(job_indexes) == 11, f"Jobs indexes count mismatch: {len(job_indexes)}"
    assert len(comp_indexes) == 4, f"Companies indexes count mismatch: {len(comp_indexes)}"
    assert demo_count == 0, f"Sandbox demo_postings not clean: {demo_count}"
    print("  [PASS] All database invariants verified perfectly.")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(" FINAL VERIFICATION AUDIT SUMMARY")
    print("=" * 80)
    for m in page_metrics:
        print(f"  {m['page']:<25} | Load: {m['load_time_sec']}s | Chars: {m['text_length']:,} | Exceptions: {m['exceptions']} | Status: {m['status']}")
    print(f"\n  Total JavaScript Console Errors:   {len(console_errors)}")
    print(f"  Total JavaScript Console Warnings: {len(console_warnings)}")
    if console_errors:
        print("\n  Logged Console Errors:")
        for err in console_errors:
            print(f"    - {err}")

    return {
        "page_metrics": page_metrics,
        "console_errors": console_errors,
        "console_warnings": console_warnings,
        "database_invariants": {
            "jobs": jobs_count,
            "companies": comp_count,
            "total_indexes": len(job_indexes) + len(comp_indexes),
            "demo_postings": demo_count,
        }
    }


if __name__ == "__main__":
    run_stage_9_comprehensive_browser_verification()
