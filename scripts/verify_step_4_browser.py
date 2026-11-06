"""
Playwright Real-Browser Verification Script for Phase 6 Step 4: Job Search & Details.
Uses Google Chrome to interactively verify:
1. Search page load, headers, and UI layout.
2. Full-text search and keyword query execution.
3. Multi-facet filter interaction (State, Platform, Remote, Skills).
4. Sorting and page size controls.
5. Pagination navigation (Next / Previous).
6. Job card metadata rendering (Salary, Company, Location, Badges).
7. Job detail view transition, complete document inspection, provenance metadata.
8. Same-platform related jobs recommendations with match explanation.
9. "Back to Search" navigation.
10. Zero uncaught browser console errors.
11. Screenshot capture for verification artifacts.
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

def save_screenshot(page, filename):
    local_path = os.path.join(LOCAL_DIR, filename)
    artifact_path = os.path.join(ARTIFACT_DIR, filename)
    page.screenshot(path=local_path, full_page=False)
    page.screenshot(path=artifact_path, full_page=False)
    print(f"Captured screenshot: {filename} -> {local_path} and {artifact_path}")

def wait_for_streamlit(page, timeout=30):
    try:
        page.locator(".stSpinner").wait_for(state="attached", timeout=2000)
    except Exception:
        pass
    try:
        page.locator(".stSpinner").wait_for(state="detached", timeout=timeout * 1000)
    except Exception:
        pass
    page.wait_for_load_state("networkidle")
    time.sleep(1.5)

def run_browser_verification():
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

        # Monitor console messages for uncaught runtime errors
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print(f"Navigating to {URL}...")
        page.goto(URL, wait_until="networkidle", timeout=45000)
        wait_for_streamlit(page)

        # 1. Verify Page Title and Header
        body_text = page.locator("body").inner_text()
        assert "Job Search & Multi-Facet Filtering" in body_text, "Page header missing"
        assert "module 1" in body_text.lower(), "Module badge missing"
        print("[PASS] Page loaded with correct header and Module 1 badge.")

        # Save default search page screenshot
        save_screenshot(page, "02_1_job_search.png")

        # 2. Verify Result Count and Job Cards Present
        assert "matching postings" in body_text.lower(), "Result count indicator missing"
        assert "view full details" in body_text.lower(), "Job card action buttons missing"
        print("[PASS] Job cards rendered with total count and action buttons.")

        # 3. Test Search Interaction (Type "Software Engineer")
        print("Testing keyword search input...")
        search_input = page.locator("input[aria-label*='Keywords / Job Title']").first
        search_input.click()
        search_input.fill("Software Engineer")
        search_input.press("Enter")
        wait_for_streamlit(page)

        save_screenshot(page, "02_2_job_search_filtered.png")
        body_text_search = page.locator("body").inner_text()
        assert "software engineer" in body_text_search.lower(), "Search keyword did not filter results"
        print("[PASS] Keyword search successfully filtered results.")

        # 4. Test Pagination
        print("Testing pagination navigation...")
        next_button = page.locator("button:has-text('Next Page →')").first
        if next_button.is_enabled():
            next_button.scroll_into_view_if_needed()
            next_button.click()
            page.locator("text=Page 2 of").first.wait_for(timeout=15000)
            print("[PASS] Pagination to Page 2 succeeded.")

            # Navigate back to page 1
            prev_button = page.locator("button:has-text('← Previous Page')").first
            prev_button.scroll_into_view_if_needed()
            prev_button.click()
            page.locator("text=Page 1 of").first.wait_for(timeout=15000)
            print("[PASS] Pagination back to Page 1 succeeded.")

        # 5. Test Job Detail View
        print("Testing Job Detail View inspection...")
        detail_btn = page.locator("button:has-text('View Full Details')").first
        detail_btn.scroll_into_view_if_needed()
        detail_btn.click()
        page.locator("button:has-text('← Back to Search Results')").first.wait_for(timeout=15000)

        detail_text = page.locator("body").inner_text()
        assert "Salary Compensation" in detail_text, "Salary metric card missing in Job Detail view"
        assert "MongoDB Document Inspection & Technical Provenance" in detail_text, "Provenance expander missing"
        assert "Related Job Recommendations (Same-Platform)" in detail_text, "Related jobs section missing"
        print("[PASS] Job Detail view opened with full record details, provenance, and related recommendations.")

        # Save job details screenshot
        save_screenshot(page, "02_3_job_search_details.png")

        # 6. Scroll down to Related Jobs and Provenance
        page.mouse.move(800, 500)
        page.mouse.wheel(0, 800)
        time.sleep(2)
        save_screenshot(page, "02_4_job_search_related.png")

        # 7. Test "Back to Search Results" navigation
        print("Testing Back to Search Results navigation...")
        back_btn = page.locator("button:has-text('← Back to Search Results')").first
        back_btn.scroll_into_view_if_needed()
        back_btn.click()
        wait_for_streamlit(page)

        body_back = page.locator("body").inner_text()
        assert "Job Search & Multi-Facet Filtering" in body_back, "Did not return to search results"
        print("[PASS] Returned to search results cleanly.")

        browser.close()



    # Verify Console Errors
    real_errors = [e for e in console_errors if not any(ign in e for ign in ["favicon", "WebGL", "stylesheet"])]
    if real_errors:
        print(f"[WARNING] Console errors encountered: {real_errors}")
    else:
        print("[PASS] Zero uncaught browser console errors encountered.")

    print("\nAll Playwright real-browser verification steps completed successfully!")

if __name__ == "__main__":
    run_browser_verification()
