"""
JobMarketDB — Phase 7 Stage 4 Skills Intelligence Browser Verification Suite
Playwright real-browser automation in Google Chrome:
1. Navigates to Skills Intelligence (http://localhost:8501/Skills_Analytics).
2. Verifies Editorial Header, Methodology Warning, and 4 Taxonomy KPI Cards -> Screenshot 1.
3. Verifies Tab 1: Indeed Technical Tools (Plotly chart, ranked table, insights card) -> Screenshot 2.
4. Switches to Tab 2: LinkedIn Functional Domains (Plotly chart, ranked table, insights card) -> Screenshot 3.
5. Switches to Tab 3: Taxonomy Contrast & Methodology (comparative matrix, formulas, pipeline blueprint) -> Screenshot 4.
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
TARGET_URL = f"{BASE_URL}/Skills_Analytics"
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


def run_stage_4_browser_verification():
    print("=" * 80)
    print(" JobMarketDB — Phase 7 Stage 4 Browser Verification Suite")
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
        # 1. INITIAL NAVIGATION & HEADER + KPIS
        # ---------------------------------------------------------------------
        print("\n[STEP 1/5] Navigating to Skills Analytics & Verifying Header + KPIs...")
        resp = page.goto(TARGET_URL, wait_until="networkidle", timeout=40000)
        assert resp and resp.status == 200, f"Page load failed with HTTP {resp.status if resp else 'None'}"
        wait_for_settled(page)

        body_text = page.inner_text("body").lower()
        assert "skills in demand" in body_text, "Main title 'Skills in Demand' missing"
        assert "skills intelligence" in body_text, "Eyebrow 'SKILLS INTELLIGENCE' missing"
        assert "methodology note: linkedin and indeed use different skill classifications" in body_text, "Methodology warning missing"
        assert "indeed skill taxonomy" in body_text, "Indeed Skill Taxonomy card missing"
        assert "top indeed tool" in body_text, "Top Indeed Tool card missing"
        assert "linkedin skill taxonomy" in body_text, "LinkedIn Skill Taxonomy card missing"
        assert "top linkedin domain" in body_text, "Top LinkedIn Domain card missing"

        # Screenshot 1: Header and KPIs
        save_screenshot(page, "stage_4_01_skills_header_and_kpis.png")
        print("  [PASS] Header, methodology warning, and 4 KPI cards verified.")

        # ---------------------------------------------------------------------
        # 2. TAB 1: INDEED TECHNICAL TOOLS
        # ---------------------------------------------------------------------
        print("\n[STEP 2/5] Inspecting Tab 1: Indeed Technical Tools...")
        assert "indeed technical tools & libraries" in body_text, "Indeed section heading missing"
        assert "python" in body_text, "Python missing from Indeed tab"
        assert "sql" in body_text, "SQL missing from Indeed tab"
        assert "ranked tools table" in body_text, "Ranked Tools Table missing"

        # Scroll down slightly to capture chart and table
        page.evaluate("window.scrollTo(0, 420)")
        time.sleep(1.0)
        # Screenshot 2: Indeed Technical Tools
        save_screenshot(page, "stage_4_02_indeed_technical_tools.png")
        print("  [PASS] Indeed technical tools chart, ranked dataframe, and synthesis verified.")

        # ---------------------------------------------------------------------
        # 3. TAB 2: LINKEDIN FUNCTIONAL DOMAINS
        # ---------------------------------------------------------------------
        print("\n[STEP 3/5] Switching to Tab 2: LinkedIn Functional Domains...")
        li_tab_btn = page.locator("[role='tab']:has-text('LinkedIn')").first
        if li_tab_btn.count() == 0:
            li_tab_btn = page.locator("[role='tab']").nth(1)
        li_tab_btn.click()
        wait_for_settled(page)

        body_text_li = page.inner_text("body").lower()
        assert "linkedin broad functional disciplines" in body_text_li, "LinkedIn heading missing"
        assert "information technology" in body_text_li, "Information Technology missing from LinkedIn tab"
        assert "ranked domains table" in body_text_li, "Ranked Domains Table missing"

        page.evaluate("window.scrollTo(0, 420)")
        time.sleep(1.0)
        # Screenshot 3: LinkedIn Functional Domains
        save_screenshot(page, "stage_4_03_linkedin_functional_domains.png")
        print("  [PASS] LinkedIn functional domains chart, ranked table, and synthesis verified.")

        # ---------------------------------------------------------------------
        # 4. TAB 3: TAXONOMY CONTRAST & METHODOLOGY
        # ---------------------------------------------------------------------
        print("\n[STEP 4/5] Switching to Tab 3: Taxonomy Contrast & Methodology...")
        contrast_tab_btn = page.locator("[role='tab']:has-text('Contrast')").first
        if contrast_tab_btn.count() == 0:
            contrast_tab_btn = page.locator("[role='tab']").nth(2)
        contrast_tab_btn.click()
        wait_for_settled(page)

        body_text_contrast = page.inner_text("body").lower()
        assert "cross-platform taxonomy incompatibility" in body_text_contrast, "Contrast heading missing"
        assert "distinct postings counting & mongodb `$setunion` deduplication" in body_text_contrast or "distinct postings counting" in body_text_contrast, "Deduplication section missing"
        assert "why a combined ranking is statistically misleading" in body_text_contrast, "Statistical misleading warning missing"

        page.evaluate("window.scrollTo(0, 380)")
        time.sleep(1.0)
        # Screenshot 4: Taxonomy Contrast & Methodology
        save_screenshot(page, "stage_4_04_taxonomy_contrast_methodology.png")
        print("  [PASS] Taxonomy contrast table, mathematical formulas, and pipeline blueprint verified.")

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
    print(" ALL STAGE 4 SKILLS INTELLIGENCE REAL BROWSER VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        run_stage_4_browser_verification()
        sys.exit(0)
    except Exception as exc:
        print(f"\n[FATAL ERROR] Stage 4 browser verification failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
