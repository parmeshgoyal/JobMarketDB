"""
JobMarketDB - Phase 6 Step 6 Playwright Browser Automation Verification
Navigates to http://localhost:8501/Company_and_Geography in Google Chrome,
interacts with tabs, filters, and captures screenshots.
"""

import os
import shutil
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


def save_screenshot(page, filename: str):
    os.makedirs(LOCAL_DIR, exist_ok=True)
    local_path = os.path.join(LOCAL_DIR, filename)
    artifact_path = os.path.join(ARTIFACT_ROOT, filename)

    page.screenshot(path=local_path, full_page=False)
    shutil.copy2(local_path, artifact_path)
    print(f"Captured screenshot: {filename} -> saved to local and artifact root.")


def wait_for_streamlit(page):
    try:
        page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=30000)
    except Exception:
        pass
    page.wait_for_load_state("networkidle")
    time.sleep(1.5)


def scroll_element(page, y_offset: int):
    page.evaluate(f"""() => {{
        const main = document.querySelector('section.main') || document.querySelector('[data-testid="stMain"]') || document.documentElement;
        if (main) main.scrollTop = {y_offset};
        window.scrollTo(0, {y_offset});
    }}""")
    time.sleep(1.2)


def run_browser_verification():
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
        page.on("request", lambda req: network_requests.append(req.url))

        # =====================================================================
        # 1. Open Company & Geography Page
        # =====================================================================
        print("\n--- 1. Navigating to http://localhost:8501/Company_and_Geography ---")
        page.goto(f"{BASE_URL}/Company_and_Geography", wait_until="networkidle", timeout=45000)
        wait_for_streamlit(page)

        body_text = page.locator("body").inner_text()
        assert "Company & US Geography Analytics" in body_text, "Page header missing"
        assert "24,472" in body_text, "Curated companies KPI missing"
        assert "26,077" in body_text, "Distinct employers KPI missing"
        assert "51 Jurisdictions" in body_text, "Geocoded US states KPI missing"
        assert "90.7%" in body_text, "State geocoding rate missing"
        print("[PASS] Company & Geography page loaded successfully with ground-truth KPI values.")

        # Capture Tab 1: Company Analytics Leaderboard
        save_screenshot(page, "04_1_company_analytics.png")

        # Scroll to Deep-Dive section
        scroll_element(page, 750)
        deep_dive_text = page.locator("body").inner_text()
        assert "Capital One" in deep_dive_text, "Default deep-dive company Capital One missing"
        assert "Verified Profile Matched" in deep_dive_text, "Capital One profile match status missing"
        assert "550" in deep_dive_text, "Capital One total postings missing"
        print("[PASS] Employer profile deep-dive verified with verified profile match and metrics.")
        save_screenshot(page, "04_1b_company_deep_dive.png")

        # =====================================================================
        # 2. Tab 2: Geography Analytics
        # =====================================================================
        print("\n--- 2. Navigating to Tab 2: Geography Analytics ---")
        scroll_element(page, 0)
        tabs = page.locator("[role='tab']").all()
        assert len(tabs) >= 3, f"Expected 3 tabs, found {len(tabs)}"
        tabs[1].click()
        wait_for_streamlit(page)

        geo_text = page.locator("body").inner_text()
        assert "US Geographic Job Demand & State Heatmap" in geo_text, "Geography section header missing"
        assert "Interactive US Job Demand Heatmap" in geo_text, "Choropleth header missing"
        print("[PASS] Geography Analytics tab loaded with interactive Plotly US choropleth.")

        save_screenshot(page, "04_2_geography_analytics.png")

        # Scroll to Top Cities section
        scroll_element(page, 950)
        cities_text = page.locator("body").inner_text()
        assert "Top Hiring Metropolitan Cities" in cities_text, "Cities header missing"
        assert "New York" in cities_text, "New York city missing"
        assert "Chicago" in cities_text, "Chicago city missing"
        print("[PASS] Top Hiring Cities section verified with valid metropolitan hubs.")
        save_screenshot(page, "04_2b_geography_cities.png")

        # =====================================================================
        # 3. Tab 3: Data Provenance & Performance
        # =====================================================================
        print("\n--- 3. Navigating to Tab 3: Data Provenance & Performance ---")
        tabs[2].click()
        wait_for_streamlit(page)

        prov_text = page.locator("body").inner_text()
        assert "Data Provenance & Methodology Disclosures" in prov_text, "Provenance header missing"
        assert "Curated Companies vs Raw Postings Strings" in prov_text, "Identity architecture missing"
        assert "COVERED_IXSCAN" in prov_text or "Covered Index Scan" in prov_text, "Covered index scan explanation missing"
        print("[PASS] Data Provenance tab verified with transparent identity and performance notes.")
        save_screenshot(page, "04_3_company_geo_provenance.png")

        # =====================================================================
        # 4. Network and Console Error Audit
        # =====================================================================
        print("\n--- 4. Network and Console Error Audit ---")
        atlas_requests = [url for url in network_requests if "mongodb.net" in url or "atlas" in url]
        assert len(atlas_requests) == 0, f"Atlas network requests detected: {atlas_requests}"
        print("[PASS] Zero Atlas network traffic detected during browser session.")

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
        print("\nAll browser verification steps passed successfully!")


if __name__ == "__main__":
    run_browser_verification()
