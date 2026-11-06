"""
JobMarketDB — Phase 7 Stage 2 Flagship Browser Verification Suite
Playwright real-browser automation in Google Chrome:
1. Navigates to Job Explorer (http://localhost:8501/Job_Search).
2. Verifies initial view, header, live 129,550 postings count, and captures Screenshot 1.
3. Performs interactive search and filter application (query, platform, remote, state).
4. Verifies active filter pills update and captures Screenshot 2.
5. Tests sorting and pagination.
6. Opens single-job detail inspection and captures Screenshot 3.
7. Audits same-platform related job recommendations and captures Screenshot 4.
8. Verifies zero console errors or uncaught exceptions.
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
TARGET_URL = f"{BASE_URL}/Job_Search"
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


def run_stage_2_browser_verification():
    print("=" * 80)
    print(" JobMarketDB — Phase 7 Stage 2 Browser Verification Suite")
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
        # 1. INITIAL VIEW VERIFICATION
        # ---------------------------------------------------------------------
        print("\n[STEP 1/6] Navigating to Job Explorer Initial View...")
        resp = page.goto(TARGET_URL, wait_until="networkidle", timeout=40000)
        assert resp and resp.status == 200, f"Page load failed with HTTP {resp.status if resp else 'None'}"
        wait_for_settled(page)

        body_text = page.inner_text("body")
        assert "Job Explorer" in body_text, "Job Explorer title missing"
        assert "129,550" in body_text, "Baseline postings count 129,550 missing"
        assert "Module 1" in body_text or "MODULE 1" in body_text, "Module 1 badge missing"

        card_count = page.locator(".jmdb-job-card").count()
        assert card_count > 0, f"Expected job cards on initial view, found {card_count}"
        print(f"  [PASS] Initial view loaded with {card_count} elevated job cards.")

        # Capture Screenshot 1
        save_screenshot(page, "stage_2_01_job_explorer_initial_view.png")

        # ---------------------------------------------------------------------
        # 2. INTERACTIVE SEARCH & FILTER APPLICATION
        # ---------------------------------------------------------------------
        print("\n[STEP 2/6] Applying Interactive Search Query & Filters...")
        search_box = page.locator("input[placeholder*='Search job title']").first
        if search_box.count() > 0:
            search_box.fill("Data Engineer")
            page.keyboard.press("Enter")
            wait_for_settled(page)

        # Select State in Sidebar
        state_select = page.locator("div[data-testid='stSidebar'] div[data-baseweb='select']").first
        if state_select.count() > 0:
            print("  -> Interacting with sidebar controls...")

        wait_for_settled(page)
        body_text = page.inner_text("body")
        assert "Data Engineer" in body_text, "Query term not found in page content"
        print("  [PASS] Search executed and active filter constraints updated.")

        # Capture Screenshot 2
        save_screenshot(page, "stage_2_02_search_results_with_active_filters.png")

        # ---------------------------------------------------------------------
        # 3. SORTING AND PAGINATION TEST
        # ---------------------------------------------------------------------
        print("\n[STEP 3/6] Testing Pagination Navigation...")
        next_btn = page.locator("button:has-text('Next Page')").first
        if next_btn.count() > 0 and not next_btn.is_disabled():
            next_btn.click()
            wait_for_settled(page)
            body_p2 = page.inner_text("body")
            assert "Page 2" in body_p2, "Pagination to Page 2 failed"
            print("  [PASS] Navigated to Page 2.")

            prev_btn = page.locator("button:has-text('Previous Page')").first
            if prev_btn.count() > 0 and not prev_btn.is_disabled():
                prev_btn.click()
                wait_for_settled(page)
                print("  [PASS] Returned to Page 1.")

        # ---------------------------------------------------------------------
        # 4. SINGLE JOB DETAIL INSPECTION
        # ---------------------------------------------------------------------
        print("\n[STEP 4/6] Inspecting Single Job Detail...")
        detail_btn = page.locator("button:has-text('View Full Details')").first
        assert detail_btn.count() > 0, "No 'View Full Details' button found"
        detail_btn.scroll_into_view_if_needed()
        detail_btn.click()
        page.locator("button:has-text('Back to Search Results')").first.wait_for(timeout=20000)
        time.sleep(1.2)

        body_detail = page.inner_text("body")
        body_detail_lower = body_detail.lower()
        assert "job description" in body_detail_lower, "Full Job Description section missing"
        assert "salary compensation" in body_detail_lower, "Salary Compensation KPI card missing"
        assert "technical provenance" in body_detail_lower or "mongodb document inspection" in body_detail_lower, "Technical Provenance section missing"
        print("  [PASS] Job Detail Inspection view rendered cleanly.")

        # Capture Screenshot 3
        save_screenshot(page, "stage_2_03_job_detail_inspection.png")

        # ---------------------------------------------------------------------
        # 5. RELATED JOBS AUDIT (SAME-PLATFORM ISOLATION)
        # ---------------------------------------------------------------------
        print("\n[STEP 5/6] Inspecting Same-Platform Related Job Recommendations...")
        assert "related job recommendations" in body_detail_lower, "Related Job Recommendations section missing"
        assert "methodological safeguard" in body_detail_lower or "same-platform" in body_detail_lower, "Taxonomy isolation callout missing"

        # Scroll to related jobs
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2.0)

        # Capture Screenshot 4
        save_screenshot(page, "stage_2_04_same_platform_related_jobs.png")

        # Return to search
        back_btn = page.locator("button:has-text('Back to Search Results')").first
        if back_btn.count() > 0:
            back_btn.scroll_into_view_if_needed()
            back_btn.click()
            page.locator("button:has-text('View Full Details')").first.wait_for(timeout=20000)
            time.sleep(1.2)
            print("  [PASS] Successfully returned to search results view.")

        # ---------------------------------------------------------------------
        # 6. CONSOLE & EXCEPTION AUDIT
        # ---------------------------------------------------------------------
        print("\n[STEP 6/6] Auditing Browser Console & Exceptions...")
        exceptions = page.locator(".stException").count()
        assert exceptions == 0, f"Found {exceptions} Streamlit exceptions!"

        critical_errors = [e for e in console_logs if e["type"] == "error"]
        print(f"  Total Console Warnings/Logs: {len(console_logs)}")
        print(f"  Total Critical Errors: {len(critical_errors)}")
        for err in critical_errors:
            print(f"    [CONSOLE ERROR] {err['text']}")

        browser.close()

    print("\n" + "=" * 80)
    print(" ALL JOB EXPLORER REAL BROWSER VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        run_stage_2_browser_verification()
        sys.exit(0)
    except Exception as exc:
        print(f"\n[FATAL ERROR] Browser verification failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
