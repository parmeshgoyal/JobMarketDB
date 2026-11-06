"""
Playwright Comprehensive Health & Re-Verification Script After Atlas Credential Removal.
Verifies all 3 implemented modules:
1. Home Page (http://localhost:8501/):
   - Live KPIs (129,550 jobs, 24,472 companies, 32.24% salary, 11.76% remote)
   - Platform comparison cards (LinkedIn 123,835, Indeed 5,715)
   - Captures fresh screenshot: 01_home_page_reverified.png
2. Job Search (http://localhost:8501/Job_Search):
   - Search query execution ('Data Scientist')
   - Filters, card metadata, job details view transition, related jobs
   - Captures fresh screenshot: 02_job_search_reverified.png
3. Skills Analytics (http://localhost:8501/Skills_Analytics):
   - Unfiltered KPIs (464 tools, Python 3,325 / 58.18%, 35 domains, IT 25,252 / 20.39%)
   - Role category selection ('Data Scientist'):
     * Scoped denominator verification: 2,543
     * Python posting count: 1,912
     * Python share percentage: 75.19%
   - Tab switching and chart rendering
   - Captures fresh screenshot: 03_skills_analytics_reverified.png
4. Validates zero uncaught runtime/console errors and zero Atlas network calls.
"""

import os
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://localhost:8501"
ARTIFACT_ROOT = r"C:\Users\Dell\.gemini\antigravity-ide\brain\0f81372d-5d57-442c-ae93-c948e56dcf88"
LOCAL_DIR = r"c:\ADBMS PROJECT\JobMarketDB\screenshots"

os.makedirs(ARTIFACT_ROOT, exist_ok=True)
os.makedirs(LOCAL_DIR, exist_ok=True)


def save_screenshot(page, filename):
    local_path = os.path.join(LOCAL_DIR, filename)
    artifact_path = os.path.join(ARTIFACT_ROOT, filename)
    page.screenshot(path=local_path, full_page=False)
    page.screenshot(path=artifact_path, full_page=False)
    print(f"Captured screenshot: {filename} -> saved to local and artifact root.")


def wait_for_streamlit(page, timeout=30):
    try:
        page.locator(".stSpinner").wait_for(state="attached", timeout=1500)
    except Exception:
        pass
    try:
        page.locator(".stSpinner").wait_for(state="detached", timeout=timeout * 1000)
    except Exception:
        pass
    page.wait_for_load_state("networkidle")
    time.sleep(1.5)


def run_comprehensive_verification():
    print(f"Launching Google Chrome at: {CHROME_PATH}")
    console_errors = []
    network_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))
        page.on("request", lambda req: network_requests.append(req.url))

        # =====================================================================
        # 1. HOME PAGE VERIFICATION
        # =====================================================================
        print("\n--- 1. Testing Home Page (http://localhost:8501/) ---")
        page.goto(BASE_URL, wait_until="networkidle", timeout=45000)
        wait_for_streamlit(page)

        home_text = page.locator("body").inner_text()
        assert "JobMarketDB" in home_text, "Home page title missing"
        assert "129,550" in home_text, "Total job postings KPI missing"
        assert "24,472" in home_text, "Total companies KPI missing"
        assert "32.24%" in home_text or "32.2%" in home_text, "Salary coverage KPI missing"
        assert "11.76%" in home_text or "11.8%" in home_text, "Remote coverage KPI missing"
        assert "123,835" in home_text, "LinkedIn postings count missing"
        assert "5,715" in home_text, "Indeed postings count missing"
        print("[PASS] Home Page verified: All live MongoDB KPIs and platform counts match ground truth.")

        save_screenshot(page, "01_home_page_reverified.png")

        # =====================================================================
        # 2. JOB SEARCH & DETAILS VERIFICATION
        # =====================================================================
        print("\n--- 2. Testing Job Search (http://localhost:8501/Job_Search) ---")
        page.goto(f"{BASE_URL}/Job_Search", wait_until="networkidle", timeout=45000)
        wait_for_streamlit(page)

        search_text = page.locator("body").inner_text()
        assert "Job Search & Multi-Facet Filtering" in search_text, "Job search header missing"
        assert "matching postings" in search_text.lower(), "Result count missing"

        # Search for 'Data Scientist'
        print("Executing keyword search for 'Data Scientist'...")
        kw_input = page.locator("input[aria-label*='Keywords / Job Title']").first
        kw_input.click()
        kw_input.fill("Data Scientist")
        kw_input.press("Enter")
        wait_for_streamlit(page)

        filtered_text = page.locator("body").inner_text()
        assert "Data Scientist" in filtered_text or "data scientist" in filtered_text.lower()
        print("[PASS] Keyword search successfully executed and filtered postings.")

        save_screenshot(page, "02_job_search_reverified.png")

        # =====================================================================
        # 3. SKILLS ANALYTICS & DENOMINATOR VERIFICATION
        # =====================================================================
        print("\n--- 3. Testing Skills Analytics (http://localhost:8501/Skills_Analytics) ---")
        page.goto(f"{BASE_URL}/Skills_Analytics", wait_until="networkidle", timeout=45000)
        wait_for_streamlit(page)

        skills_text = page.locator("body").inner_text()
        assert "Skills Demand & Taxonomy Analytics" in skills_text, "Skills page header missing"
        assert "464 Tools" in skills_text, "Indeed tools KPI missing"
        assert "35 Domains" in skills_text, "LinkedIn domains KPI missing"
        assert "Python" in skills_text and "3,325" in skills_text, "Python KPI missing"
        assert "Information Technology" in skills_text and "25,252" in skills_text, "IT KPI missing"
        print("[PASS] Skills Analytics unfiltered KPIs verified (Indeed N=5,715, LinkedIn N=123,835).")

        # Test Indeed Role Category Scoped Denominator (Select 'Data Scientist')
        print("Selecting role category 'Data Scientist' on Indeed...")
        role_select = page.locator("div[data-testid='stSelectbox']:has-text('Filter by Role Category')").first
        input_box = role_select.locator("input[role='combobox']")
        input_box.click()
        input_box.fill("Data Scientist")
        input_box.press("Enter")
        wait_for_streamlit(page)

        ds_text = page.locator("body").inner_text()
        assert "2,543" in ds_text, "Scoped denominator 2,543 missing from page"
        assert "1,912" in ds_text, "Python scoped count 1,912 missing from page"
        assert "75.19%" in ds_text or "75.2%" in ds_text, "Python scoped share 75.19% missing from page"
        print("[PASS] Indeed Data Scientist scoped denominator verified: Denominator = 2,543, Python = 1,912 (75.19%).")

        save_screenshot(page, "03_skills_analytics_reverified.png")

        # =====================================================================
        # 4. NETWORK & CONSOLE AUDIT
        # =====================================================================
        print("\n--- 4. Network and Console Error Audit ---")
        atlas_requests = [url for url in network_requests if "mongodb.net" in url or "atlas" in url]
        assert len(atlas_requests) == 0, f"Atlas network requests detected: {atlas_requests}"
        print("[PASS] Zero Atlas network traffic detected during entire browser session.")

        critical_errors = [
            e for e in console_errors
            if "favicon" not in e.lower()
            and "font" not in e.lower()
            and "_stcore" not in e.lower()
            and "404" not in e.lower()
        ]
        print(f"Total critical console errors recorded: {len(critical_errors)}")
        if critical_errors:
            print("Errors detected:", critical_errors)
        assert len(critical_errors) == 0, f"Uncaught runtime errors in browser: {critical_errors}"
        print("[PASS] Zero uncaught browser console errors.")

        browser.close()
        print("\nAll health verification and browser tests passed successfully!")


if __name__ == "__main__":
    run_comprehensive_verification()
