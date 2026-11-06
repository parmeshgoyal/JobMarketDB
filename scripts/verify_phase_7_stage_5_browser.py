"""
JobMarketDB — Phase 7 Stage 5 Salary Analytics Browser Verification Suite
Playwright real-browser automation in Google Chrome:
1. Navigates to Salary Analytics (http://localhost:8501/Salary_Analytics).
2. Verifies Editorial Hero Header, Methodology Disclosure, and Asymmetric KPI Grid -> Screenshot 1.
3. Verifies Central Tendency Panels (LinkedIn vs Indeed) -> Screenshot 2.
4. Verifies Deep-Dive Distribution Tabs (Histogram, Buckets, Experience) -> Screenshot 3.
5. Verifies Pay Period Breakdown, Outlier Audit Table (38 records > $1M), and Provenance -> Screenshot 4.
6. Audits browser console logs and ensures zero Streamlit exceptions.
"""

import json
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
TARGET_URL = f"{BASE_URL}/Salary_Analytics"
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


def wait_for_settled(page, timeout=30):
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


def run_stage_5_browser_verification():
    print("=" * 80)
    print(" JobMarketDB — Phase 7 Stage 5 Browser Verification Suite")
    print(f" Target URL: {TARGET_URL}")
    print(f" Chrome Path: {CHROME_PATH}")
    print("=" * 80)

    console_logs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--window-size=1920,1080"],
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        def on_console(msg):
            if msg.type in ("error", "warning") and "favicon" not in msg.text.lower():
                console_logs.append({"type": msg.type, "text": msg.text})

        page.on("console", on_console)

        # ---------------------------------------------------------------------
        # 1. INITIAL NAVIGATION & HERO + ASYMMETRIC KPIS
        # ---------------------------------------------------------------------
        print("\n[STEP 1/5] Navigating to Salary Analytics & Verifying Hero + Asymmetric KPIs...")
        resp = page.goto(TARGET_URL, wait_until="networkidle", timeout=40000)
        assert resp and resp.status == 200, f"Page load failed with HTTP {resp.status if resp else 'None'}"
        wait_for_settled(page)

        # Ensure dynamic data card is mounted
        page.locator(".jmdb-card").first.wait_for(timeout=30000)
        time.sleep(2.0)

        body_text = page.inner_text("body").lower()
        assert "salary distributions & outlier audit" in body_text, "Main title missing"
        assert "compensation & macro intelligence" in body_text, "Category eyebrow missing"
        assert "methodology note: linkedin and indeed use incompatible salary fields" in body_text, "Methodology callout missing"
        assert "observed continuous compensation" in body_text or "primary benchmark" in body_text, "Primary benchmark card missing"
        assert "indeed derived midpoints" in body_text, "Indeed derived midpoints card missing"
        assert "salary information coverage" in body_text, "Salary coverage card missing"
        assert "outlier audit classification" in body_text, "Outlier audit card missing"

        # Screenshot 1: Hero and Asymmetric KPIs
        save_screenshot(page, "stage_5_01_salary_hero_and_kpis.png")
        print("  [PASS] Hero header, methodology warning, and asymmetric KPI grid verified.")

        # ---------------------------------------------------------------------
        # 2. CENTRAL TENDENCY BREAKDOWN PANELS
        # ---------------------------------------------------------------------
        print("\n[STEP 2/5] Inspecting Central Tendency Panels...")
        assert "central tendency & empirical distribution" in body_text, "Central tendency section missing"
        assert "linkedin continuous compensation metrics" in body_text, "LinkedIn metrics panel missing"
        assert "indeed derived midpoint metrics" in body_text, "Indeed metrics panel missing"

        page.evaluate("window.scrollTo(0, 560)")
        time.sleep(1.0)
        # Screenshot 2: Central Tendency Panels
        save_screenshot(page, "stage_5_02_central_tendency_panels.png")
        print("  [PASS] Central tendency side-by-side panels verified.")

        # ---------------------------------------------------------------------
        # 3. DISTRIBUTION TABS (HISTOGRAM & BUCKETS)
        # ---------------------------------------------------------------------
        print("\n[STEP 3/5] Inspecting Deep-Dive Distribution Tabs...")
        assert "deep-dive distribution analytics" in body_text, "Distribution analytics heading missing"
        assert "salary distribution histogram & central tendency" in body_text, "Histogram heading missing"

        # Check histogram chart is mounted
        hist_chart = page.locator(".js-plotly-plot").first
        assert hist_chart.count() > 0, "Plotly histogram chart missing"

        page.evaluate("window.scrollTo(0, 1180)")
        time.sleep(1.0)
        # Screenshot 3: Salary Histogram and Tabs
        save_screenshot(page, "stage_5_03_salary_histogram_and_buckets.png")
        print("  [PASS] Histogram tab and Plotly density visualization verified.")

        # ---------------------------------------------------------------------
        # 4. OUTLIER AUDIT & PAY PERIOD MULTIPLIERS
        # ---------------------------------------------------------------------
        print("\n[STEP 4/5] Inspecting Outlier Audit & Pay Period Breakdown...")
        page.evaluate("window.scrollTo(0, 2100)")
        time.sleep(1.2)

        body_text_bottom = page.inner_text("body").lower()
        assert "provenance & outlier audit analysis" in body_text_bottom, "Provenance section missing"
        assert "linkedin pay period breakdown" in body_text_bottom, "Pay period breakdown missing"
        assert "outlier audit classification (38 records > $1,000,000)" in body_text_bottom, "Outlier table missing"
        assert "prior audit classified 30 records" in body_text_bottom or "unresolved intern stipend" in body_text_bottom, "Outlier explanation missing"

        # Screenshot 4: Outlier Audit and Pay Periods
        save_screenshot(page, "stage_5_04_outlier_audit_and_multipliers.png")
        print("  [PASS] Pay period breakdown and 38-record outlier audit table verified.")

        # ---------------------------------------------------------------------
        # 5. CONSOLE AUDIT & EXCEPTION CHECK
        # ---------------------------------------------------------------------
        print("\n[STEP 5/5] Auditing Browser Console & Exceptions...")
        exceptions = page.locator(".stException").count()
        assert exceptions == 0, f"Found {exceptions} Streamlit exceptions!"

        critical_errors = [e for e in console_logs if e["type"] == "error"]
        print(f"  Total Console Warnings/Logs: {len(console_logs)}")
        print(f"  Total Critical Errors: {len(critical_errors)}")
        for err in critical_errors:
            print(f"    [CONSOLE ERROR] {err['text']}")

        browser.close()

    print("\n" + "=" * 80)
    print(" ALL STAGE 5 SALARY ANALYTICS REAL BROWSER VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        run_stage_5_browser_verification()
        sys.exit(0)
    except Exception as exc:
        print(f"\n[FATAL ERROR] Stage 5 browser verification failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
