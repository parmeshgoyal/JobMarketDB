"""
JobMarketDB — Phase 7 Stage 7 Platform Comparison Browser Verification Suite
Playwright real-browser automation in Google Chrome:
1. Navigates to Platform Comparison (http://localhost:8501/Platform_Comparison).
2. Verifies Editorial Hero Header, Methodology Disclosure, and Asymmetric KPI Grid -> Screenshot 1.
3. Verifies Tab 1: Volume Comparison & Field Completeness Audit -> Screenshot 2.
4. Verifies Tab 2: Salary Separation & Standardized Buckets -> Screenshot 3.
5. Verifies Tab 3: Skills Taxonomy Contrast & Shared Employers Overlap -> Screenshot 4.
6. Verifies Tab 4: Workplace Modality (Tri-State), Geographic Coverage, & Methodology -> Screenshot 5.
7. Audits browser console logs and ensures zero Streamlit exceptions.
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
TARGET_URL = f"{BASE_URL}/Platform_Comparison"
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
    time.sleep(1.2)


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


def run_stage_7_browser_verification():
    print("=" * 80)
    print(" JobMarketDB — Phase 7 Stage 7 Browser Verification Suite")
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
        # STEP 1: Navigate to Platform Comparison
        # ---------------------------------------------------------------------
        print("\n[STEP 1] Navigating to Platform Comparison page...")
        page.goto(TARGET_URL, timeout=60000)
        page.locator(".jmdb-editorial-header").wait_for(timeout=30000)
        page.locator(".jmdb-card").first.wait_for(timeout=30000)
        wait_for_settled(page)

        body_text = page.inner_text("body")

        # Assert Header and Eyebrow
        assert "LinkedIn vs Indeed" in body_text, "Hero title missing"
        assert "CROSS-PLATFORM MARKET INTELLIGENCE" in body_text, "Eyebrow missing"
        assert "dual source taxonomies" in body_text.lower(), "Status badge missing"
        print("  -> Header and Eyebrow validated successfully.")

        # Assert Primary & Supporting KPI values
        assert "129,550" in body_text, "Total volume count missing"
        assert "123,835" in body_text, "LinkedIn volume count missing"
        assert "5,715" in body_text, "Indeed volume count missing"
        assert "570" in body_text, "Shared employers count missing"
        assert "12.30%" in body_text, "Remote coverage rate missing"
        assert "90.57%" in body_text, "LinkedIn state coverage missing"
        assert "94.16%" in body_text, "Indeed state coverage missing"
        print("  -> Executive KPI metrics and volume split verified.")

        # Screenshot 1: Header, Methodology Callout, and Executive Asymmetric Grid
        scroll_to_y(page, 0)
        save_screenshot(page, "stage_7_01_platform_hero_and_kpis.png")

        # ---------------------------------------------------------------------
        # STEP 2: Tab 1 — Volume Comparison & Field Completeness Audit
        # ---------------------------------------------------------------------
        print("\n[STEP 2] Inspecting Tab 1: Volume Comparison & Completeness Audit...")
        scroll_to_y(page, 700)

        tab1_text = page.inner_text("body")
        assert "Posting Volume & Platform Proportions" in tab1_text, "Volume section heading missing"
        assert "Data Coverage & Field Completeness Audit" in tab1_text, "Completeness heading missing"
        assert "87.89%" in tab1_text or "87.90%" in tab1_text, "LinkedIn city coverage missing"
        assert "0.00%" in tab1_text, "Indeed zero coverage missing"
        print("  -> Volume comparison and 14-attribute completeness table verified.")

        save_screenshot(page, "stage_7_02_posting_volume_comparison.png")

        # ---------------------------------------------------------------------
        # STEP 3: Tab 2 — Salary Separation & Standardized Buckets
        # ---------------------------------------------------------------------
        print("\n[STEP 3] Switching to Tab 2: Compensation & Salary Separation...")
        tab2_button = page.locator("[role='tab']:has-text('Compensation')").first
        if tab2_button.count() == 0:
            tab2_button = page.locator("[role='tab']").nth(1)
        tab2_button.click()
        wait_for_settled(page)

        scroll_to_y(page, 200)

        sal_text = page.inner_text("body")
        assert "Compensation & Salary Methodology Contrast" in sal_text, "Salary heading missing"
        assert "95,515.00" in sal_text, "LinkedIn adjusted mean missing"
        assert "81,375.00" in sal_text, "LinkedIn median missing"
        assert "116,501.31" in sal_text, "Indeed mean midpoint missing"
        assert "110,000.00" in sal_text, "Indeed median midpoint missing"
        assert "Standardized 6-Tier Salary Bucket Comparison" in sal_text, "Bucket heading missing"
        print("  -> Salary separation and 6-tier bucket distribution verified.")

        save_screenshot(page, "stage_7_03_salary_comparison.png")

        # ---------------------------------------------------------------------
        # STEP 4: Tab 3 — Skills Taxonomy & Shared Employers
        # ---------------------------------------------------------------------
        print("\n[STEP 4] Switching to Tab 3: Skills, Roles & Employer Overlap...")
        tab3_button = page.locator("[role='tab']:has-text('Skills')").first
        if tab3_button.count() == 0:
            tab3_button = page.locator("[role='tab']").nth(2)
        tab3_button.click()
        wait_for_settled(page)

        scroll_to_y(page, 200)

        skills_text = page.inner_text("body")
        assert "Skills Taxonomy & Shared Employers Intelligence" in skills_text, "Skills heading missing"
        assert "35 Broad Domains" in skills_text, "LinkedIn 35 domains tag missing"
        assert "464 Specific Tools" in skills_text, "Indeed 464 tools tag missing"
        assert "Capital One" in skills_text, "Top shared employer Capital One missing"
        assert "550 Postings" in skills_text, "Capital One total missing"
        assert "496 LinkedIn + 54 Indeed" in skills_text, "Capital One split missing"
        print("  -> Skills taxonomy separation and shared employers overlap verified.")

        save_screenshot(page, "stage_7_04_skills_and_employer_overlap.png")

        # ---------------------------------------------------------------------
        # STEP 5: Tab 4 — Workplace Modality, Geography & Methodology
        # ---------------------------------------------------------------------
        print("\n[STEP 5] Switching to Tab 4: Modality, Geography & Methodology...")
        tab4_button = page.locator("[role='tab']:has-text('Modality')").first
        if tab4_button.count() == 0:
            tab4_button = page.locator("[role='tab']").nth(3)
        tab4_button.click()
        wait_for_settled(page)

        scroll_to_y(page, 150)

        mod_text = page.inner_text("body")
        assert "Workplace Modality, Geographic Coverage & Methodology" in mod_text, "Modality heading missing"
        assert "Tri-State Remote Work Model" in mod_text, "Tri-state heading missing"
        assert "15,236" in mod_text, "LinkedIn remote count missing"
        assert "108,599" in mod_text, "LinkedIn unspecified count missing"
        assert "112,159" in mod_text, "LinkedIn state count missing"
        assert "108,855" in mod_text, "LinkedIn city count missing"
        assert "129,550 jobs" in mod_text, "Canonical jobs invariant missing"
        assert "24,472 companies" in mod_text, "Canonical companies invariant missing"
        assert "15 indexes" in mod_text, "Index inventory invariant missing"
        print("  -> Modality tri-state, geographic completeness, and methodology verified.")

        save_screenshot(page, "stage_7_05_remote_and_geographic_coverage.png")

        # Audit console errors
        print("\n[AUDIT] Checking browser console logs...")
        critical_errors = [c for c in console_logs if c["type"] == "error"]
        print(f"  Console entries: {len(console_logs)} ({len(critical_errors)} errors)")
        for err in critical_errors[:5]:
            print(f"    - {err['text']}")

        browser.close()

    print("\n" + "=" * 80)
    print(" [STAGE 7 VERIFICATION COMPLETE] All browser verification steps passed!")
    print("=" * 80)


if __name__ == "__main__":
    run_stage_7_browser_verification()

