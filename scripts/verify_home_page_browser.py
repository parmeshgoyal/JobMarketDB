"""
JobMarketDB - Dedicated Real Browser Verification Suite for Phase 6 Step 3 (Home Page)

Launches Google Chrome via Playwright and executes automated end-to-end verification of:
1. Streamlit app hydration and connectivity.
2. Live Database KPIs:
   - Total Job Postings: 129,550
   - Total Company Profiles: 24,472
   - Salary Information Coverage: 32.24%
   - Explicit Remote Adoption: 11.76%
3. Platform Overview (LinkedIn vs Indeed volume chart and empirical comparison table).
4. System Architecture 6-Layer blueprint cards.
5. Live Database Information & 15-Index Catalog (expanders for jobs & companies).
6. 3-Tier Data Provenance Framework (SOURCE, NORMALIZED, DERIVED).
7. Console log auditing (no uncaught JS/Python exceptions).
8. Captures updated full-page screenshot into local and artifact folders.
"""

import os
import shutil
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_SCREENSHOTS_DIR = os.path.join(PROJECT_ROOT, "screenshots")
ARTIFACT_SCREENSHOTS_DIR = r"C:\Users\Dell\.gemini\antigravity-ide\brain\0f81372d-5d57-442c-ae93-c948e56dcf88\screenshots"

os.makedirs(LOCAL_SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(ARTIFACT_SCREENSHOTS_DIR, exist_ok=True)


def main():
    print("=" * 80)
    print(" JobMarketDB - Phase 6 Step 3 Real Browser Verification Suite")
    print("=" * 80)

    console_errors = []

    with sync_playwright() as p:
        print(f">>> Launching Google Chrome from: {CHROME_PATH}")
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--window-size=1920,1080"],
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        def on_console(msg):
            if msg.type in ["error"]:
                # Ignore benign favicon or font 404 warnings if any
                if "favicon" not in msg.text.lower():
                    console_errors.append(msg.text)
                    print(f"    [BROWSER CONSOLE ERROR] {msg.text}")

        page.on("console", on_console)

        target_url = "http://localhost:8501/"
        print(f">>> Navigating to Home Page: {target_url}")
        resp = page.goto(target_url, wait_until="networkidle", timeout=30000)
        print(f"    HTTP Status: {resp.status}")
        assert resp.status == 200, f"Expected HTTP 200, got {resp.status}"

        # Wait for Streamlit app hydration
        print(">>> Waiting for Streamlit DOM hydration...")
        page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=15000)
        time.sleep(3)  # Allow Streamlit animations and cache load to settle

        # 1. Header & Title Verification
        print(">>> 1. Verifying Main Header & Badge...")
        body_text = page.locator("body").inner_text()
        assert "JobMarketDB" in body_text, "Missing 'JobMarketDB' in page content"
        assert "Enterprise US Tech Job Market Analytics" in body_text, "Missing subtitle in page content"
        assert "ADBMS PHASE 6" in body_text.upper(), "Missing 'ADBMS Phase 6' badge"
        print("    [PASS] Header and badge verified.")

        # 2. Live Database KPIs Verification
        print(">>> 2. Verifying Live Database KPI Metrics...")
        assert "129,550" in body_text, "Missing Total Postings '129,550'"
        assert "24,472" in body_text, "Missing Total Companies '24,472'"
        assert "32.24%" in body_text, "Missing Salary Coverage '32.24%'"
        assert "11.76%" in body_text, "Missing Remote Adoption '11.76%'"
        print("    [PASS] All 4 Live KPIs present and accurate:")
        print("           * Total Postings: 129,550")
        print("           * Total Companies: 24,472")
        print("           * Salary Coverage: 32.24%")
        print("           * Remote Adoption: 11.76%")

        # 3. Cross-Platform Intelligence Section Verification
        print(">>> 3. Verifying Cross-Platform Intelligence (LinkedIn vs Indeed)...")
        assert "Cross-Platform Intelligence" in body_text, "Missing Cross-Platform section"
        assert "Market Share & Posting Volume Distribution" in body_text, "Missing Volume chart header"
        assert "Empirical Platform Comparison" in body_text, "Missing comparison table"
        assert "123,835" in body_text, "Missing LinkedIn count 123,835"
        assert "5,715" in body_text, "Missing Indeed count 5,715"
        assert "Continuous Base Salary" in body_text, "Missing LinkedIn compensation type"
        assert "Search Query Buckets" in body_text, "Missing Indeed compensation type"
        print("    [PASS] Platform comparison metrics, table, and compensation types verified.")

        # Check Plotly volume chart rendered
        plotly_charts = page.locator(".js-plotly-plot").count()
        assert plotly_charts >= 1, f"Expected at least 1 Plotly chart, found {plotly_charts}"
        print(f"    [PASS] Verified Plotly volume chart rendering (count: {plotly_charts}).")

        # 4. System Architecture 6-Layer Blueprint
        print(">>> 4. Verifying System Architecture 6 Layers...")
        arch_layers = [
            "Layer 1: Presentation & Visualization",
            "Layer 2: Unified Service Interface",
            "Layer 3: Operational Query Engine",
            "Layer 4: Analytical Aggregation Engine",
            "Layer 5: Connection & Pooling Layer",
            "Layer 6: Database Storage Engine",
        ]
        for layer in arch_layers:
            assert layer.lower() in body_text.lower(), f"Missing architectural layer: {layer}"
        assert "jobmarketanalyticsservice" in body_text.lower(), "Missing service class reference"
        assert "mongodb community 9.0.4" in body_text.lower(), "Missing MongoDB version reference"
        print("    [PASS] All 6 architectural layers verified.")

        # 5. Live Database Specifications & Index Catalog
        print(">>> 5. Verifying Database Specifications & Index Catalog...")
        assert "Live Database Information & Index Catalog" in body_text
        assert "jobmarketdb" in body_text
        assert "WiredTiger" in body_text
        assert "15 Indexes" in body_text
        assert "jobs" in body_text
        assert "companies" in body_text
        print("    [PASS] Live Database specs and 15-index catalog verified.")

        # 6. Data Provenance Framework
        print(">>> 6. Verifying Data Provenance Framework...")
        assert "Data Provenance Framework" in body_text
        assert "1. SOURCE TIER (Raw Truth)" in body_text
        assert "2. NORMALIZED TIER (Cleaned)" in body_text
        assert "3. DERIVED TIER (Analytical Artifacts)" in body_text
        print("    [PASS] 3-tier provenance framework verified.")

        # 7. Navigation Hub & Sidebar
        print(">>> 7. Verifying Navigation Hub & Sidebar...")
        assert "1. Job Search" in body_text
        assert "2. Skills Analytics" in body_text
        assert "3. Salary Analytics" in body_text
        assert "4. Company & Geography" in body_text
        assert "5. Platform Comparison" in body_text
        assert "6. CRUD Demo Sandbox" in body_text
        assert "Local MongoDB Active" in body_text
        print("    [PASS] Navigation hub and sidebar status verified.")

        # 8. Console Error Audit
        print(">>> 8. Auditing Browser Console Errors...")
        print(f"    Console errors count: {len(console_errors)}")
        assert len(console_errors) == 0, f"Found console errors: {console_errors}"
        print("    [PASS] 0 uncaught console errors.")

        # 9. Screenshot Capture
        print(">>> 9. Capturing Multi-Section Visual Screenshots...")
        # Section 1: Hero KPIs and Platform Comparison
        screenshot_path = os.path.join(LOCAL_SCREENSHOTS_DIR, "01_home_page.png")
        page.screenshot(path=screenshot_path)
        print(f"    Saved local hero screenshot: {screenshot_path}")

        artifact_screenshot_path = os.path.join(ARTIFACT_SCREENSHOTS_DIR, "01_home_page.png")
        shutil.copy2(screenshot_path, artifact_screenshot_path)

        # Section 2: Architecture & Live Database Specifications
        print("    Scrolling to Architecture & Live Database Specifications...")
        page.mouse.move(800, 500)
        page.mouse.wheel(0, 1000)
        time.sleep(1.5)
        arch_screenshot_path = os.path.join(LOCAL_SCREENSHOTS_DIR, "01_home_page_architecture.png")
        page.screenshot(path=arch_screenshot_path)
        print(f"    Saved architecture screenshot: {arch_screenshot_path}")
        shutil.copy2(arch_screenshot_path, os.path.join(ARTIFACT_SCREENSHOTS_DIR, "01_home_page_architecture.png"))

        # Section 3: Data Provenance & Module Navigation Hub
        print("    Scrolling to Data Provenance & Module Navigation Hub...")
        page.mouse.move(800, 500)
        page.mouse.wheel(0, 1200)
        time.sleep(1.5)
        prov_screenshot_path = os.path.join(LOCAL_SCREENSHOTS_DIR, "01_home_page_provenance.png")
        page.screenshot(path=prov_screenshot_path)
        print(f"    Saved provenance screenshot: {prov_screenshot_path}")
        shutil.copy2(prov_screenshot_path, os.path.join(ARTIFACT_SCREENSHOTS_DIR, "01_home_page_provenance.png"))

        browser.close()
        print("=" * 80)
        print(" [PASS] PHASE 6 STEP 3 BROWSER VERIFICATION COMPLETED SUCCESSFULLY")
        print("=" * 80)


if __name__ == "__main__":
    main()
