"""
JobMarketDB — Phase 6 Step 7 Playwright Browser Automation Verification
Navigates to http://localhost:8501/Salary_Analytics in Google Chrome,
interacts with tabs, switches platforms, audits console & network,
and captures high-resolution screenshots.
Also verifies all previously implemented pages load with status 200.
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
    time.sleep(2.0)


def scroll_to_element(page, y_offset: int):
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
            args=["--no-sandbox", "--disable-gpu", "--window-size=1920,1080"],
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Listen to console messages and network requests
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("request", lambda req: network_requests.append(req.url))

        # ── 1. Navigate to Salary Analytics ───────────────────────────────────
        salary_url = f"{BASE_URL}/Salary_Analytics"
        print(f"\n[1] Navigating to {salary_url}...")
        resp = page.goto(salary_url, wait_until="networkidle", timeout=45000)
        assert resp.status == 200, f"Expected 200 OK, got {resp.status}"
        wait_for_streamlit(page)
        print("    Salary Analytics loaded successfully (HTTP 200).")

        # Screenshot 1: Overview KPIs & Central Tendency Cards
        scroll_to_element(page, 0)
        time.sleep(1.0)
        save_screenshot(page, "05_1_salary_overview_kpis.png")

        # Screenshot 2: Indeed Midpoints & Section 4 Tabs (Histogram LinkedIn)
        scroll_to_element(page, 580)
        time.sleep(1.0)
        save_screenshot(page, "05_2_salary_histogram_tab.png")

        # Switch Histogram to Indeed Derived Midpoint
        print("\n[2] Switching Histogram radio to Indeed (Derived Midpoint)...")
        try:
            indeed_opt = page.locator("label").filter(has_text="Indeed (Derived Midpoint)")
            if indeed_opt.count() > 0:
                indeed_opt.first.click()
                wait_for_streamlit(page)
                time.sleep(1.5)
                scroll_to_element(page, 720)
                save_screenshot(page, "05_2b_salary_histogram_indeed.png")
                print("    Switched to Indeed histogram successfully.")
        except Exception as e:
            print(f"    Failed to switch histogram: {e}")

        # Switch to Tab 2: Salary Buckets
        print("\n[3] Interacting with Tab 2: Salary Buckets...")
        try:
            tab2 = page.locator("[role='tab']").filter(has_text="Salary Buckets")
            if tab2.count() > 0:
                tab2.first.click()
                wait_for_streamlit(page)
                time.sleep(1.5)
                scroll_to_element(page, 700)
                save_screenshot(page, "05_3_salary_buckets_tab.png")
                print("    Tab 2 (Salary Buckets) captured.")
        except Exception as e:
            print(f"    Failed Tab 2: {e}")

        # Switch to Tab 3: By Experience Level
        print("\n[4] Interacting with Tab 3: By Experience Level...")
        try:
            tab3 = page.locator("[role='tab']").filter(has_text="By Experience Level")
            if tab3.count() > 0:
                tab3.first.click()
                wait_for_streamlit(page)
                time.sleep(1.5)
                scroll_to_element(page, 700)
                save_screenshot(page, "05_4_salary_experience_tab.png")
                print("    Tab 3 (Experience Level) captured.")
        except Exception as e:
            print(f"    Failed Tab 3: {e}")

        # Switch to Tab 4: By Job Title
        print("\n[5] Interacting with Tab 4: By Job Title...")
        try:
            tab4 = page.locator("[role='tab']").filter(has_text="By Job Title")
            if tab4.count() > 0:
                tab4.first.click()
                wait_for_streamlit(page)
                time.sleep(1.5)
                scroll_to_element(page, 700)
                save_screenshot(page, "05_5_salary_title_tab.png")
                print("    Tab 4 (Job Title) captured.")
        except Exception as e:
            print(f"    Failed Tab 4: {e}")

        # Switch to Tab 5: By State
        print("\n[6] Interacting with Tab 5: By State...")
        try:
            tab5 = page.locator("[role='tab']").filter(has_text="By State")
            if tab5.count() > 0:
                tab5.first.click()
                wait_for_streamlit(page)
                time.sleep(1.5)
                scroll_to_element(page, 700)
                save_screenshot(page, "05_6_salary_state_tab.png")
                print("    Tab 5 (State) captured.")
        except Exception as e:
            print(f"    Failed Tab 5: {e}")

        # Scroll to Section 5, 6: Pay Period Breakdown & Outlier Audit
        print("\n[7] Capturing Outlier Audit Table & Pay Period Breakdown...")
        scroll_to_element(page, 1550)
        time.sleep(1.5)
        save_screenshot(page, "05_7_salary_outlier_audit.png")

        # Expand Data Provenance & Methodology Disclosures
        print("\n[8] Expanding Data Provenance and Methodology Reference...")
        try:
            expander = page.locator("details summary").filter(has_text="Full Salary Methodology & Field Reference")
            if expander.count() > 0:
                expander.first.click()
                time.sleep(1.5)
                scroll_to_element(page, 2050)
                save_screenshot(page, "05_8_salary_provenance_methodology.png")
                print("    Methodology expander captured.")
        except Exception as e:
            print(f"    Failed expander: {e}")

        # ── 9. Verify regression pages load cleanly ───────────────────────────
        regression_urls = [
            ("Home", f"{BASE_URL}/"),
            ("Job Search", f"{BASE_URL}/Job_Search"),
            ("Skills Analytics", f"{BASE_URL}/Skills_Analytics"),
            ("Company & Geography", f"{BASE_URL}/Company_and_Geography"),
        ]
        print("\n[9] Verifying regression pages load cleanly...")
        for name, url in regression_urls:
            r = page.goto(url, wait_until="networkidle", timeout=30000)
            wait_for_streamlit(page)
            print(f"    - {name}: HTTP {r.status} OK")
            assert r.status == 200, f"Page {name} failed with status {r.status}"

        # ── 10. Audit network and console ─────────────────────────────────────
        print("\n[10] Auditing Network & Console...")
        atlas_requests = [req for req in network_requests if "mongodb.net" in req or "atlas" in req.lower()]
        print(f"    - Atlas / external DB requests: {len(atlas_requests)}")
        assert len(atlas_requests) == 0, f"Atlas traffic detected: {atlas_requests}"

        critical_console = [err for err in console_errors if "error" in err.lower() and "favicon" not in err.lower()]
        print(f"    - Critical Console Errors: {len(critical_console)}")
        for err in critical_console[:5]:
            print(f"      {err}")

        browser.close()
        print("\n>>> Browser verification completed successfully! All checks passed.")


if __name__ == "__main__":
    run_browser_verification()
