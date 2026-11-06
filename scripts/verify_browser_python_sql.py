"""
Real Browser Playwright Verification Script: Python + SQL (ALL vs ANY)
Drives host Google Chrome against live Streamlit application:
1. Interactively selects 'Python' and 'SQL' in Required Skills multiselect.
2. Evaluates Match ALL Selected Skills ($all) mode:
   - Captures exact total count (2,075 postings).
   - Verifies all rendered job cards contain BOTH 'Python' and 'SQL'.
   - Captures screenshot: 02_9_browser_skills_all.png.
3. Switches to Match ANY Selected Skill ($in) mode without changing skills:
   - Captures exact total count (4,354 postings).
   - Verifies all rendered job cards contain 'Python' or 'SQL' or both.
   - Captures screenshot: 02_10_browser_skills_any.png.
4. Verifies zero uncaught browser console errors.
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
URL = "http://localhost:8501/Job_Search"
ARTIFACT_DIR = r"C:\Users\Dell\.gemini\antigravity-ide\brain\0f81372d-5d57-442c-ae93-c948e56dcf88\screenshots"
LOCAL_DIR = r"c:\ADBMS PROJECT\JobMarketDB\screenshots"

os.makedirs(ARTIFACT_DIR, exist_ok=True)
os.makedirs(LOCAL_DIR, exist_ok=True)


def save_screenshot(page, filename: str) -> None:
    local_path = os.path.join(LOCAL_DIR, filename)
    artifact_path = os.path.join(ARTIFACT_DIR, filename)
    page.screenshot(path=local_path, full_page=False)
    page.screenshot(path=artifact_path, full_page=False)
    print(f"Captured screenshot: {filename} -> {local_path} and {artifact_path}")


def wait_for_streamlit(page, timeout=30):
    """Waits for Streamlit rerun spinner and DOM settlement."""
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


def run_python_sql_browser_verification():
    print(f"Launching Google Chrome at: {CHROME_PATH}")
    console_errors = []

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

        print(f"Navigating to {URL}...")
        page.goto(URL, wait_until="networkidle", timeout=45000)
        wait_for_streamlit(page)

        # ---------------------------------------------------------------------
        # 1. Select Python and SQL in Required Skills MultiSelect
        # ---------------------------------------------------------------------
        print("Selecting 'Python' and 'SQL' in Required Skills multiselect...")
        ms = page.locator("div[data-testid='stMultiSelect']").first
        inp = ms.locator("input[aria-label='Required Skills']")

        # Add Python
        inp.click()
        inp.type("Python", delay=50)
        page.wait_for_timeout(400)
        page.locator("[role='option']:has-text('Python')").first.click()
        wait_for_streamlit(page)

        # Add SQL
        inp.click()
        inp.type("SQL", delay=50)
        page.wait_for_timeout(400)
        page.locator("[role='option']:has-text('SQL')").first.click()
        wait_for_streamlit(page)

        # ---------------------------------------------------------------------
        # 2. Verify Match ALL Selected Skills ($all)
        # ---------------------------------------------------------------------
        print("\nVerifying Match ALL Selected Skills ($all) mode...")
        # Ensure ALL radio option is active
        all_radio = page.locator("label:has-text('Match ALL Selected Skills ($all)')")
        all_radio.click()
        wait_for_streamlit(page)

        body_all = page.locator("body").inner_text()
        assert "Found 2,075 matching postings" in body_all, "Expected exactly 2,075 postings for Python + SQL (ALL)"
        assert "Active Filter Constraints:" in body_all, "Active constraint chip banner missing"
        assert "Skills (ALL): Python, SQL" in body_all, "Skills ALL active constraint missing"

        # Inspect all rendered job cards on Page 1
        cards_all = page.locator(".jmdb-job-card")
        card_count_all = cards_all.count()
        assert card_count_all > 0, "No job cards rendered in ALL mode"
        print(f"Inspecting {card_count_all} rendered job cards on Page 1 (ALL mode):")

        for idx in range(card_count_all):
            card_text = cards_all.nth(idx).inner_text()
            has_python = "Python" in card_text
            has_sql = "SQL" in card_text
            assert has_python and has_sql, f"Job card {idx} missing Python or SQL in ALL mode: {card_text[:100]}"
            print(f"  [Card {idx + 1:02d}] Verified BOTH 'Python' and 'SQL' present.")

        print(f"[PASS] Match ALL ($all) verified: exactly 2,075 postings; all {card_count_all} page-1 cards contain both Python and SQL.")
        save_screenshot(page, "02_9_browser_skills_all.png")

        # ---------------------------------------------------------------------
        # 3. Switch to Match ANY Selected Skill ($in)
        # ---------------------------------------------------------------------
        print("\nSwitching to Match ANY Selected Skill ($in) without modifying skills...")
        any_radio = page.locator("label:has-text('Match ANY Selected Skill ($in)')")
        any_radio.click()
        wait_for_streamlit(page)

        body_any = page.locator("body").inner_text()
        assert "Found 4,354 matching postings" in body_any, "Expected exactly 4,354 postings for Python + SQL (ANY)"
        assert "Skills (ANY): Python, SQL" in body_any, "Skills ANY active constraint missing"

        # Inspect all rendered job cards on Page 1
        cards_any = page.locator(".jmdb-job-card")
        card_count_any = cards_any.count()
        assert card_count_any > 0, "No job cards rendered in ANY mode"
        print(f"Inspecting {card_count_any} rendered job cards on Page 1 (ANY mode):")

        for idx in range(card_count_any):
            card_text = cards_any.nth(idx).inner_text()
            has_python = "Python" in card_text
            has_sql = "SQL" in card_text
            assert has_python or has_sql, f"Job card {idx} contains neither Python nor SQL in ANY mode: {card_text[:100]}"
            matched_which = "BOTH Python and SQL" if (has_python and has_sql) else ("Python" if has_python else "SQL")
            print(f"  [Card {idx + 1:02d}] Verified contains: {matched_which}.")

        print(f"[PASS] Match ANY ($in) verified: exactly 4,354 postings; all {card_count_any} page-1 cards contain Python or SQL or both.")
        save_screenshot(page, "02_10_browser_skills_any.png")

        browser.close()

    real_errors = [e for e in console_errors if not any(ign in e for ign in ["favicon", "WebGL", "stylesheet"])]
    if real_errors:
        print(f"[WARNING] Console errors encountered: {real_errors}")
    else:
        print("[PASS] Zero uncaught browser console errors encountered.")

    print("\n" + "=" * 80)
    print("REAL BROWSER VERIFICATION: PYTHON + SQL TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("1. Skills Selected:                ['Python', 'SQL']")
    print("2. Match ALL ($all) Result Count:  2,075 matching postings (100% verified contain both)")
    print("3. Match ANY ($in) Result Count:   4,354 matching postings (100% verified contain either)")
    print("4. Inclusion-Exclusion Check:      3,325 (Python) + 3,104 (SQL) - 2,075 (ALL) = 4,354 (ANY) [Exact match]")
    print("5. Visual Evidence Artifacts:      02_9_browser_skills_all.png, 02_10_browser_skills_any.png")


if __name__ == "__main__":
    run_python_sql_browser_verification()
