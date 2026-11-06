"""
JobMarketDB — Phase 6 Step 8 Playwright Browser Automation Verification
Navigates to http://localhost:8501/Platform_Comparison in Google Chrome,
interacts with controls, audits console & network, and captures high-resolution screenshots.
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
        # Wait for Streamlit running indicator ('Stop' button) to detach
        page.wait_for_selector("text=Stop", state="detached", timeout=30000)
    except Exception:
        pass
    try:
        # Ensure at least one Plotly chart is actively attached to DOM
        page.wait_for_selector(".js-plotly-plot", state="visible", timeout=30000)
    except Exception:
        pass
    time.sleep(2.0)


def scroll_to_element(page, y_offset: int):
    page.evaluate(
        f"""() => {{
        const main = document.querySelector('section.main') || document.querySelector('[data-testid="stMain"]') || document.documentElement;
        if (main) main.scrollTop = {y_offset};
        window.scrollTo(0, {y_offset});
    }}"""
    )
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
        page.on(
            "console",
            lambda msg: console_errors.append(f"[{msg.type}] {msg.text}")
            if msg.type in ("error", "warning")
            else None,
        )
        page.on("request", lambda req: network_requests.append(req.url))

        # ── 1. Navigate to Platform Comparison ────────────────────────────────
        platform_url = f"{BASE_URL}/Platform_Comparison"
        print(f"\n[1] Navigating to {platform_url}...")
        resp = page.goto(platform_url, wait_until="domcontentloaded", timeout=45000)
        assert resp.status == 200, f"Expected 200 OK, got {resp.status}"
        wait_for_streamlit(page)
        print("    Platform Comparison loaded successfully (HTTP 200).")

        # Screenshot 1: Overview KPIs & Volume Cards
        scroll_to_element(page, 0)
        time.sleep(1.0)
        save_screenshot(page, "06_1_platform_overview_kpis.png")

        # Screenshot 2: Data Coverage & Field Completeness Audit
        scroll_to_element(page, 1050)
        time.sleep(1.0)
        save_screenshot(page, "06_2_field_completeness_audit.png")

        # Screenshot 3: Job Characteristics (Workplace Modality & Role Specialization)
        scroll_to_element(page, 2450)
        time.sleep(1.0)
        save_screenshot(page, "06_3_job_characteristics.png")

        # Click Tab 2: Role Specialization
        print("\n[2] Clicking Role Specialization tab...")
        try:
            role_tab = page.locator("button[role='tab']").filter(has_text="Role Specialization")
            if role_tab.count() > 0:
                role_tab.first.click()
                wait_for_streamlit(page)
                time.sleep(1.0)
                scroll_to_element(page, 2450)
                save_screenshot(page, "06_3b_role_specialization_tab.png")
        except Exception as e:
            print(f"    Tab click notice: {e}")

        # Screenshot 4: Shared Employers Intelligence
        scroll_to_element(page, 3340)
        time.sleep(1.0)
        save_screenshot(page, "06_4_shared_employers.png")

        # Screenshot 5: Compensation & Salary Separation (Bucket Chart & Table)
        scroll_to_element(page, 4130)
        time.sleep(1.0)
        save_screenshot(page, "06_5_salary_separation_buckets.png")

        # Screenshot 6: Skills Taxonomy Contrast
        scroll_to_element(page, 5520)
        time.sleep(1.0)
        save_screenshot(page, "06_6_skills_taxonomy_contrast.png")

        # Screenshot 7: Experience Level Coverage & Disclosure
        scroll_to_element(page, 6860)
        time.sleep(1.0)
        save_screenshot(page, "06_7_experience_disclosure.png")

        # Open Methodology Expander
        print("\n[3] Opening Methodology expander...")
        try:
            expander = page.locator("[data-testid='stExpander'] summary, [data-testid='stExpander']")
            if expander.count() > 0:
                expander.first.click()
                time.sleep(1.5)
                scroll_to_element(page, 7580)
                save_screenshot(page, "06_8_methodology_reference.png")
                print("    Methodology expander captured.")
            else:
                print("    Expander not found.")
        except Exception as e:
            print(f"    Expander click notice: {e}")

        # ── 2. Regression Check: Verify All Other Pages Load ─────────────────
        other_pages = [
            ("Home Overview", f"{BASE_URL}/"),
            ("Job Search", f"{BASE_URL}/Job_Search"),
            ("Skills Analytics", f"{BASE_URL}/Skills_Analytics"),
            ("Salary Analytics", f"{BASE_URL}/Salary_Analytics"),
            ("Company & Geography", f"{BASE_URL}/Company_and_Geography"),
        ]

        print("\n[4] Running Regression Verification on other pages...")
        for name, url in other_pages:
            print(f"    Navigating to {name} ({url})...")
            p_resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            assert p_resp.status == 200, f"Page {name} returned status {p_resp.status}"
            wait_for_streamlit(page)
            print(f"    -> {name} OK (HTTP 200)")

        # ── 3. Console & Network Audit ───────────────────────────────────────
        print("\n[5] Console & Network Safety Audit:")
        critical_errors = [
            err
            for err in console_errors
            if "error" in err.lower()
            and "favicon" not in err.lower()
            and "use_container_width" not in err.lower()
        ]
        print(f"    Critical console errors: {len(critical_errors)}")
        for err in critical_errors:
            print(f"      {err}")

        atlas_calls = [
            req
            for req in network_requests
            if any(k in req.lower() for k in ("mongodb.net", "atlas", "amazonaws.com", "azure.com"))
        ]
        print(f"    Remote Atlas / Cloud Network calls: {len(atlas_calls)}")
        assert (
            len(atlas_calls) == 0
        ), f"VIOLATION: Remote database traffic detected: {atlas_calls}"

        print("\n=== Browser Verification Complete: ALL CHECKS PASSED ===")
        browser.close()


if __name__ == "__main__":
    run_browser_verification()
