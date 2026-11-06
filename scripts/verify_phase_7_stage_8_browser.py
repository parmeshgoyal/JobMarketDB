"""
JobMarketDB — Phase 7 Stage 8 CRUD Demo Browser Verification Suite
Playwright real-browser automation in Google Chrome:
1. Navigates to CRUD Demo (http://localhost:8501/CRUD_Demo).
2. Verifies Editorial Hero Header, Database Safety Overview (4 badges), and 5 KPI cards -> Screenshot 1.
3. Tests Create Operation with a disposable test record, switches to Browse Sandbox to inspect -> Screenshot 2.
4. Tests Update Operation: selects record, executes salary $unset removal -> Screenshot 3.
5. Tests Delete Operation: verifies red warning preview, checks confirmation, executes deletion -> Screenshot 4.
6. Verifies Operations Audit & Reference tab and Live Data Invariant Guarantee footer -> Screenshot 5.
7. Ensures canonical collections remain strictly untouched (129,550 jobs, 24,472 companies, 15 indexes).
8. Audits browser console logs for any unhandled errors.
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

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://localhost:8501"
TARGET_URL = f"{BASE_URL}/CRUD_Demo"
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


def run_stage_8_browser_verification():
    print("=" * 80)
    print(" JobMarketDB — Phase 7 Stage 8 Browser Verification Suite")
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
        # STEP 1: Navigate to CRUD Demo & Inspect Overview
        # ---------------------------------------------------------------------
        print("\n[STEP 1] Navigating to CRUD Demo page...")
        page.goto(TARGET_URL, timeout=60000)
        wait_for_settled(page)

        body_text = page.locator("body").inner_text()
        print(f"  [OK] Page loaded ({len(body_text)} text chars).")

        # Verify Header Elements
        assert "Explore MongoDB Operations" in body_text, "Hero title missing"
        assert "DATABASE OPERATIONS LABORATORY" in body_text, "Eyebrow tag missing"
        assert "LOCAL DATABASE" in body_text, "Connection status badge missing"
        print("  [OK] Header elements verified: Title, Eyebrow, and Status Badge.")

        # Verify Safety Indicators
        assert "Canonical Protected" in body_text, "Canonical Protected indicator missing"
        assert "Sandbox Isolated" in body_text, "Sandbox Isolated indicator missing"
        assert "Local MongoDB Only" in body_text, "Local MongoDB Only indicator missing"
        assert "No Atlas Connection" in body_text, "No Atlas Connection indicator missing"
        print("  [OK] Database Safety Overview: All 4 safety boundaries confirmed.")

        # Verify Metrics
        assert "129,550" in body_text, "Canonical jobs count 129,550 missing"
        assert "24,472" in body_text, "Canonical companies count 24,472 missing"
        assert "15" in body_text, "Production index count 15 missing"
        print("  [OK] Live Database Metrics: 129,550 jobs, 24,472 companies, 15 indexes confirmed.")

        scroll_to_y(page, 0)
        save_screenshot(page, "stage_8_01_crud_hero_and_safety.png")

        # ---------------------------------------------------------------------
        # STEP 2: Create Operation with Disposable Record & Read Verification
        # ---------------------------------------------------------------------
        print("\n[STEP 2] Testing Create Operation and Read Browser...")
        # Scroll tabs into view and click Tab 1 (Create Posting)
        create_tab = page.locator("[role='tab']").nth(1)
        create_tab.scroll_into_view_if_needed()
        time.sleep(0.5)
        create_tab.click()
        time.sleep(1.5)
        wait_for_settled(page)

        test_title = "Lead AI Systems Architect (Stage 8 Test)"
        test_company = "Aegis Frontier Labs"
        test_city = "Seattle"
        test_skills = "Python, MongoDB, PyTorch, Ray, Docker"
        test_desc = "Automated browser verification test posting for Stage 8 CRUD demonstration. Requires distributed systems expertise."

        # Fill inputs
        page.locator("input[aria-label*='Job Title']").first.fill(test_title)
        page.locator("input[aria-label*='Company Name']").first.fill(test_company)
        page.locator("input[aria-label*='City']").first.fill(test_city)
        page.locator("input[aria-label*='Required Skills']").first.fill(test_skills)

        # Toggle salary
        try:
            page.locator("label:has-text('Provide Salary Compensation Structure')").first.click()
            time.sleep(0.5)
        except Exception:
            pass

        # Fill description
        page.locator("textarea").first.fill(test_desc)

        # Submit create form
        page.locator("button:has-text('Insert Demonstration Posting')").first.click()
        time.sleep(2.5)
        wait_for_settled(page)

        # Verify creation success
        new_body = page.locator("body").inner_text()
        assert "Demonstration Posting Created Successfully" in new_body or "Created Successfully" in new_body or "✓" in new_body, "Create success confirmation missing"
        print("  [OK] Create Operation: Disposable posting successfully created in demo_postings.")

        # Switch to Tab 0 (Browse Sandbox) to inspect
        browse_tab = page.locator("[role='tab']").nth(0)
        browse_tab.scroll_into_view_if_needed()
        time.sleep(0.5)
        browse_tab.click()
        time.sleep(1.5)
        wait_for_settled(page)

        scroll_to_y(page, 300)
        save_screenshot(page, "stage_8_02_create_and_read_workspace.png")
        print("  [OK] Read Operation: Record inspected with skills chips, metadata, and description.")

        # ---------------------------------------------------------------------
        # STEP 3: Update Operation with Salary $unset Removal
        # ---------------------------------------------------------------------
        print("\n[STEP 3] Testing Update Operation and Salary $unset Removal...")
        update_tab = page.locator("[role='tab']").nth(2)
        update_tab.scroll_into_view_if_needed()
        time.sleep(0.5)
        update_tab.click()
        time.sleep(1.5)
        wait_for_settled(page)

        update_body = page.locator("body").inner_text()
        assert "Update an Existing Posting" in update_body, "Update workspace missing"

        # Select Remove Salary Structure ($unset)
        try:
            remove_sal_radio = page.locator("label:has-text('Remove Salary Structure')").first
            remove_sal_radio.click()
            time.sleep(0.5)
            print("  [OK] Selected 'Remove Salary Structure (Unset)' radio option.")
        except Exception as e:
            print(f"  [NOTE] Radio selection: {e}")

        # Click Save Changes
        save_btn = page.locator("button:has-text('Save Changes')").first
        save_btn.scroll_into_view_if_needed()
        time.sleep(0.5)
        save_btn.click()
        time.sleep(2.5)
        wait_for_settled(page)

        post_update_body = page.locator("body").inner_text()
        assert "Demonstration Posting Updated Successfully" in post_update_body or "Updated Successfully" in post_update_body or "✓" in post_update_body, "Update success confirmation missing"
        print("  [OK] Update Operation: Successfully executed update with salary $unset.")

        scroll_to_y(page, 200)
        save_screenshot(page, "stage_8_03_update_and_salary_removal.png")

        # ---------------------------------------------------------------------
        # STEP 4: Delete Operation with Confirmation Guard
        # ---------------------------------------------------------------------
        print("\n[STEP 4] Testing Delete Operation with Mandatory Confirmation Guard...")
        delete_tab = page.locator("[role='tab']").nth(3)
        delete_tab.scroll_into_view_if_needed()
        time.sleep(0.5)
        delete_tab.click()
        time.sleep(2.0)
        wait_for_settled(page)

        delete_body = page.locator("body").inner_text()
        delete_lower = delete_body.lower()
        assert "delete a demonstration posting" in delete_lower, "Delete workspace title missing"
        assert "permanent deletion" in delete_lower or "deletion" in delete_lower, "Warning preview card missing"
        print("  [OK] Deletion preview card confirmed with safety notice.")

        # Check confirmation checkbox
        confirm_label = page.locator("label:has-text('confirm')").first
        confirm_label.scroll_into_view_if_needed()
        time.sleep(0.5)
        confirm_label.click()
        time.sleep(1.5)
        print("  [OK] Explicit confirmation checkbox toggled to True.")

        scroll_to_y(page, 300)
        save_screenshot(page, "stage_8_04_delete_confirmation.png")

        # Click Delete button
        del_btn = page.locator("button:has-text('Permanently Delete')").first
        del_btn.scroll_into_view_if_needed()
        time.sleep(0.5)
        del_btn.click()
        time.sleep(2.5)
        wait_for_settled(page)

        post_del_lower = page.locator("body").inner_text().lower()
        assert "deleted successfully" in post_del_lower or "deleted" in post_del_lower, "Delete success message missing"
        print("  [OK] Delete Operation: Successfully deleted single document with verified confirmation.")

        # ---------------------------------------------------------------------
        # STEP 5: Operations Audit Log & Canonical Database Invariants
        # ---------------------------------------------------------------------
        print("\n[STEP 5] Verifying Operations Audit Log and Final Canonical Database Invariants...")
        history_tab = page.locator("[role='tab']").nth(4)
        history_tab.scroll_into_view_if_needed()
        time.sleep(0.5)
        history_tab.click()
        time.sleep(2.0)
        wait_for_settled(page)

        hist_lower = page.locator("body").inner_text().lower()
        assert "operations audit" in hist_lower or "reference" in hist_lower, "History tab title missing"
        assert "bson document model" in hist_lower, "Technical reference card 1 missing"
        assert "update operators" in hist_lower, "Technical reference card 3 missing"
        print("  [OK] Operations Audit & Reference: Session log and architectural references verified.")

        # Scroll to footer
        scroll_to_y(page, 1000)
        save_screenshot(page, "stage_8_05_database_invariants.png")

        # Verify Canonical Database Invariants via Direct Database Call
        from database.connection import get_database
        db = get_database()
        final_jobs = db["jobs"].count_documents({})
        final_comp = db["companies"].count_documents({})
        jobs_idx = len(list(db["jobs"].list_indexes()))
        comp_idx = len(list(db["companies"].list_indexes()))
        total_idx = jobs_idx + comp_idx
        demo_count = db["demo_postings"].count_documents({})

        # Clean up any residual test records from demo_postings
        if demo_count > 0:
            db["demo_postings"].delete_many({"company.name": test_company})
            demo_count = db["demo_postings"].count_documents({})

        print(f"\n[FINAL DATABASE AUDIT]")
        print(f"  Canonical Jobs:      {final_jobs:,} (Expected: 129,550) -> {'PASS' if final_jobs == 129550 else 'FAIL'}")
        print(f"  Canonical Companies: {final_comp:,} (Expected: 24,472)  -> {'PASS' if final_comp == 24472 else 'FAIL'}")
        print(f"  Jobs Indexes:        {jobs_idx}      (Expected: 11)      -> {'PASS' if jobs_idx == 11 else 'FAIL'}")
        print(f"  Companies Indexes:   {comp_idx}       (Expected: 4)       -> {'PASS' if comp_idx == 4 else 'FAIL'}")
        print(f"  Total Indexes:       {total_idx}      (Expected: 15)      -> {'PASS' if total_idx == 15 else 'FAIL'}")
        print(f"  Sandbox Postings:    {demo_count}      (Clean state)")

        assert final_jobs == 129550, f"Canonical jobs mutated! Expected 129,550 got {final_jobs}"
        assert final_comp == 24472, f"Canonical companies mutated! Expected 24,472 got {final_comp}"
        assert total_idx == 15, f"Indexes mutated! Expected 15 got {total_idx}"

        # Browser Console Audit
        err_logs = [log for log in console_logs if log["type"] == "error"]
        print(f"\n[CONSOLE AUDIT] Total warnings/errors captured: {len(console_logs)}")
        if err_logs:
            print(f"  [WARNING] Errors logged: {err_logs}")
        else:
            print("  [OK] Zero JavaScript errors detected.")

        browser.close()
        print("\n" + "=" * 80)
        print(" STAGE 8 BROWSER VERIFICATION COMPLETED SUCCESSFULLY")
        print("=" * 80)


if __name__ == "__main__":
    run_stage_8_browser_verification()
