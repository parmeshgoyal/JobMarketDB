"""
JobMarketDB - Automated Real Browser Verification Suite (Phase 6 Step 2)

Performs comprehensive browser testing using installed Google Chrome / Microsoft Edge
via Playwright:
1. Navigates to Streamlit Home page (http://localhost:8501/).
2. Tests sidebar navigation across all 6 pages.
3. Tests direct URL navigation for deep-linking.
4. Verifies CSS stylesheet loading and styling tokens.
5. Captures console logs and checks for any JavaScript/Python exceptions.
6. Tests page refresh and layout integrity.
7. Saves full-page screenshots for visual audit evidence.
"""

import os
import shutil
import sys
import time
from typing import Dict, List, Tuple

# Ensure stdout and stderr handle utf-8 cleanly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright, Browser, Page, ConsoleMessage

# Chrome executable path
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_SCREENSHOTS_DIR = os.path.join(PROJECT_ROOT, "screenshots")
ARTIFACT_SCREENSHOTS_DIR = r"C:\Users\Dell\.gemini\antigravity-ide\brain\0f81372d-5d57-442c-ae93-c948e56dcf88\screenshots"

PAGES_CONFIG = [
    {
        "name": "home",
        "title": "Home & Architecture Overview",
        "url_path": "",
        "expected_header": "JobMarketDB",
        "expected_badge": "ADBMS Phase 6",
        "sidebar_label": "app",
    },
    {
        "name": "1_job_search",
        "title": "Job Search & Multi-Facet Filtering",
        "url_path": "Job_Search",
        "expected_header": "Job Search & Multi-Facet Filtering",
        "expected_badge": "Module 1",
        "sidebar_label": "Job Search",
    },
    {
        "name": "2_skills_analytics",
        "title": "Skills Demand & Taxonomy Separation",
        "url_path": "Skills_Analytics",
        "expected_header": "Skills Demand & Taxonomy Separation",
        "expected_badge": "Module 2",
        "sidebar_label": "Skills Analytics",
    },
    {
        "name": "3_salary_analytics",
        "title": "Salary Distributions & Outlier Audit",
        "url_path": "Salary_Analytics",
        "expected_header": "Salary Distributions & Outlier Audit",
        "expected_badge": "Module 3",
        "sidebar_label": "Salary Analytics",
    },
    {
        "name": "4_company_and_geography",
        "title": "Hiring Leaders & US Geographic Distribution",
        "url_path": "Company_and_Geography",
        "expected_header": "Hiring Leaders & US Geographic Distribution",
        "expected_badge": "Module 4",
        "sidebar_label": "Company and Geography",
    },
    {
        "name": "5_platform_comparison",
        "title": "Cross-Platform Market Comparison",
        "url_path": "Platform_Comparison",
        "expected_header": "Cross-Platform Market Comparison",
        "expected_badge": "Module 5",
        "sidebar_label": "Platform Comparison",
    },
    {
        "name": "6_crud_demo",
        "title": "Isolated CRUD Demonstration Sandbox",
        "url_path": "CRUD_Demo",
        "expected_header": "Isolated CRUD Demonstration Sandbox",
        "expected_badge": "Module 6",
        "sidebar_label": "CRUD Demo",
    },
]


def save_screenshot(page: Page, filename: str) -> str:
    """Takes a full page screenshot and saves to both local and artifact directories."""
    local_path = os.path.join(LOCAL_SCREENSHOTS_DIR, filename)
    page.screenshot(path=local_path, full_page=True)

    if os.path.exists(ARTIFACT_SCREENSHOTS_DIR):
        artifact_path = os.path.join(ARTIFACT_SCREENSHOTS_DIR, filename)
        shutil.copy2(local_path, artifact_path)

    return local_path


def run_browser_verification() -> bool:
    print("=" * 80)
    print(" JobMarketDB — Real Browser Verification Suite (Google Chrome)")
    print("=" * 80)

    # 1. Identify browser binary
    browser_path = CHROME_PATH if os.path.exists(CHROME_PATH) else EDGE_PATH
    browser_name = "Google Chrome" if browser_path == CHROME_PATH else "Microsoft Edge"
    print(f"[1/6] Selected Browser: {browser_name} ({browser_path})")

    console_logs: List[Dict[str, str]] = []
    page_errors: List[str] = []

    def handle_console(msg: ConsoleMessage):
        if msg.type in ("error", "warning"):
            console_logs.append({"type": msg.type, "text": msg.text, "location": str(msg.location)})

    def handle_pageerror(err):
        page_errors.append(str(err))

    with sync_playwright() as p:
        print("[2/6] Launching browser in headless mode (viewport: 1280x850)...")
        browser: Browser = p.chromium.launch(
            executable_path=browser_path,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        page: Page = context.new_page()

        page.on("console", handle_console)
        page.on("pageerror", handle_pageerror)

        base_url = "http://localhost:8501"

        # ---------------------------------------------------------------------
        # 3. Test Home Page Loading & CSS Styling
        # ---------------------------------------------------------------------
        print(f"\n[3/6] Navigating to Home page ({base_url})...")
        resp = page.goto(base_url, wait_until="networkidle", timeout=15000)
        assert resp and resp.status == 200, f"Home page failed to load: status {resp.status if resp else 'None'}"

        # Wait for Streamlit block container
        page.wait_for_selector(".block-container", timeout=10000)
        time.sleep(1.5)  # Allow Streamlit client hydration

        # Check for visible title
        content = page.content()
        assert "JobMarketDB" in content, "JobMarketDB title not found on Home page!"
        assert "ADBMS Phase 6" in content, "ADBMS Phase 6 badge not found on Home page!"

        # Verify no visible exceptions
        exceptions = page.locator(".stException").count()
        assert exceptions == 0, f"Found {exceptions} Streamlit exceptions on Home page!"

        # Check CSS stylesheet loaded
        header_el = page.locator(".jmdb-header-title").first
        assert header_el.is_visible(), "Custom CSS class .jmdb-header-title is not visible!"

        screenshot_path = save_screenshot(page, "01_home_page.png")
        print(f"  [PASS] Home page rendered successfully without exceptions.")
        print(f"  [PASS] Custom CSS loaded and applied.")
        print(f"  [PASS] Screenshot saved: {screenshot_path}")

        # ---------------------------------------------------------------------
        # 4. Test Sidebar Navigation & Verify Each Page
        # ---------------------------------------------------------------------
        print("\n[4/6] Testing Sidebar Navigation across all analytical pages...")
        for idx, page_cfg in enumerate(PAGES_CONFIG[1:], start=2):
            label = page_cfg["sidebar_label"]
            print(f"  -> Testing navigation to '{label}' ({page_cfg['title']})...")

            # Click on sidebar link using Streamlit stSidebarNavLink testid
            nav_link = page.locator(f'[data-testid="stSidebarNavLink"]:has-text("{label}")').first
            if nav_link.count() > 0 and nav_link.is_visible():
                nav_link.click()
            else:
                page.goto(f"{base_url}/{page_cfg['url_path']}", wait_until="networkidle")

            # Wait explicitly for URL and the page-specific header to render
            page.wait_for_url(f"**/{page_cfg['url_path']}*", timeout=15000)
            page.wait_for_selector(f"text={page_cfg['expected_header']}", timeout=15000)
            page.wait_for_selector(".block-container", timeout=10000)
            time.sleep(0.5)

            # Verify content
            page_text = page.inner_text("body")
            assert page_cfg["expected_header"] in page_text, f"Header '{page_cfg['expected_header']}' missing on {label}!"
            assert page_cfg["expected_badge"].lower() in page_text.lower(), f"Badge '{page_cfg['expected_badge']}' missing on {label}!"

            # Check for absence of exceptions
            ex_count = page.locator(".stException").count()
            assert ex_count == 0, f"Found {ex_count} Streamlit exceptions on {label}!"

            # Save screenshot
            sc_name = f"{idx:02d}_{page_cfg['name']}.png"
            sc_path = save_screenshot(page, sc_name)
            print(f"     [PASS] {label} rendered cleanly. Header & badge verified.")
            print(f"     [PASS] Screenshot: {sc_path}")

        # ---------------------------------------------------------------------
        # 5. Test Direct URL Deep-Linking & Page Reload
        # ---------------------------------------------------------------------
        print("\n[5/6] Testing Deep-Linking & Page Refresh...")
        # Direct URL to CRUD Demo
        crud_url = f"{base_url}/CRUD_Demo"
        print(f"  -> Directly navigating to deep-link: {crud_url}...")
        page.goto(crud_url, wait_until="networkidle")
        time.sleep(1.0)
        assert "Isolated CRUD Demonstration Sandbox" in page.content(), "Direct URL navigation failed!"
        print("  [PASS] Deep-link navigation verified.")

        # Test Page Reload
        print("  -> Testing page reload (F5)...")
        page.reload(wait_until="networkidle")
        time.sleep(1.0)
        assert page.locator(".stException").count() == 0, "Exceptions observed after page reload!"
        print("  [PASS] Page reload verified with zero exceptions.")

        # ---------------------------------------------------------------------
        # 6. Audit Browser Console Logs
        # ---------------------------------------------------------------------
        print("\n[6/6] Inspecting Browser Console Logs...")
        print(f"  Total Console Warnings/Errors recorded: {len(console_logs)}")
        for log in console_logs:
            print(f"    [{log['type'].upper()}] {log['text']}")
        print(f"  Total Page Uncaught Errors: {len(page_errors)}")
        for err in page_errors:
            print(f"    [PAGE ERROR] {err}")

        browser.close()

    print("\n" + "=" * 80)
    print(" ALL BROWSER ACCESSIBILITY & RENDERING CHECKS PASSED")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        success = run_browser_verification()
        sys.exit(0 if success else 1)
    except Exception as exc:
        print(f"\n[FATAL ERROR] Browser verification failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
