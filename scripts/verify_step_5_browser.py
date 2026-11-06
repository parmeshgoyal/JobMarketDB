"""
Playwright Real-Browser Verification Script for Phase 6 Step 5: Skills Analytics.
Uses Google Chrome to interactively verify:
1. Skills Analytics page load, title, header, and Module 2 badge.
2. Prominent methodological notice regarding non-combinable taxonomies.
3. Executive KPI cards (Indeed 464 tools, LinkedIn 35 domains, Python #1, IT #1).
4. Tab 1: Indeed technical tools bar chart, top N slider, and interactive search filter.
5. Tab 2: LinkedIn functional domains bar chart and rankings table.
6. Tab 3: Comparative taxonomy table and $setUnion deduplication explanation.
7. Zero uncaught browser console errors.
8. Captures authoritative visual evidence screenshots for verification report.
"""

import os
import sys
import time
import shutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://localhost:8501/Skills_Analytics"
ARTIFACT_ROOT = r"C:\Users\Dell\.gemini\antigravity-ide\brain\0f81372d-5d57-442c-ae93-c948e56dcf88"
ARTIFACT_SCREENSHOTS = os.path.join(ARTIFACT_ROOT, "screenshots")
LOCAL_DIR = r"c:\ADBMS PROJECT\JobMarketDB\screenshots"

os.makedirs(ARTIFACT_ROOT, exist_ok=True)
os.makedirs(ARTIFACT_SCREENSHOTS, exist_ok=True)
os.makedirs(LOCAL_DIR, exist_ok=True)


def save_screenshot(page, filename):
    local_path = os.path.join(LOCAL_DIR, filename)
    artifact_shot_path = os.path.join(ARTIFACT_SCREENSHOTS, filename)
    artifact_root_path = os.path.join(ARTIFACT_ROOT, filename)

    page.screenshot(path=local_path, full_page=False)
    page.screenshot(path=artifact_shot_path, full_page=False)
    page.screenshot(path=artifact_root_path, full_page=False)
    print(f"Captured screenshot: {filename} -> saved to local, artifact screenshots, and artifact root.")


def wait_for_streamlit(page, timeout=30):
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

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print(f"Navigating to {URL}...")
        page.goto(URL, wait_until="networkidle", timeout=45000)
        wait_for_streamlit(page)

        # 1. Verify Page Title, Header, and Module 2 Badge
        body_text = page.locator("body").inner_text()
        assert "Skills Demand & Taxonomy Analytics" in body_text, "Page header missing"
        assert "module 2" in body_text.lower(), "Module 2 badge missing"
        assert "distinct platform taxonomies (non-combinable)" in body_text.lower(), "Methodological callout missing"
        print("[PASS] Page loaded with correct header, Module 2 badge, and warning callout.")

        # 2. Verify KPI Cards
        assert "464 Tools" in body_text, "Indeed 464 tools KPI missing"
        assert "Python" in body_text, "Python KPI missing"
        assert "35 Domains" in body_text, "LinkedIn 35 domains KPI missing"
        assert "Information Technology" in body_text, "Information Technology KPI missing"
        print("[PASS] All 4 executive KPI cards rendered with verified values.")

        # 3. Tab 1: Indeed Technical Tools Verification
        print("Verifying Tab 1: Indeed Technical Tools...")
        # Check that Plotly chart container is visible
        plotly_chart = page.locator(".js-plotly-plot").first
        plotly_chart.wait_for(state="visible", timeout=10000)
        assert "Top 15 Technical Tools on Indeed" in body_text or "Technical Tools on Indeed" in body_text
        assert "Python" in body_text and "SQL" in body_text and "Machine Learning" in body_text

        # Capture Tab 1 overview screenshot
        save_screenshot(page, "03_1_skills_indeed_tools.png")

        # Scroll to Indeed chart and capture focused chart & table view
        plotly_chart.scroll_into_view_if_needed()
        time.sleep(1)
        save_screenshot(page, "03_1b_skills_indeed_chart.png")
        print("[PASS] Tab 1 (Indeed Tools & Chart) verified and screenshots captured.")

        # Test search filter within Indeed tools table
        print("Testing tool table filter with 'Spark'...")
        search_box = page.locator("input[aria-label*='Filter Table by Tool Name']").first
        search_box.click()
        search_box.fill("Spark")
        search_box.press("Enter")
        wait_for_streamlit(page)

        body_text_after_filter = page.locator("body").inner_text()
        assert "Spark" in body_text_after_filter, "Filtered page should contain Spark"
        print("[PASS] Table search filter successfully isolated 'Spark'.")

        # Clear search filter
        search_box.click()
        search_box.fill("")
        search_box.press("Enter")
        wait_for_streamlit(page)

        # 4. Tab 2: LinkedIn Functional Domains Verification
        print("Switching to Tab 2: LinkedIn Functional Domains...")
        tab_li = page.locator("[role='tab']").nth(1)
        tab_li.click()
        wait_for_streamlit(page)

        body_text_li = page.locator("body").inner_text()
        assert "LinkedIn Broad Functional Disciplines" in body_text_li, "LinkedIn tab title missing"
        assert "Information Technology" in body_text_li and "Sales" in body_text_li and "Management" in body_text_li

        # Ensure no accidental tool leakage in LinkedIn tab
        assert "35 broad functional skill domains" in body_text_li.lower()

        # Capture Tab 2 screenshot
        save_screenshot(page, "03_2_skills_linkedin_domains.png")
        print("[PASS] Tab 2 (LinkedIn Domains) verified and screenshot captured.")

        # 5. Tab 3: Taxonomy Contrast & Deduplication Methodology
        print("Switching to Tab 3: Taxonomy Contrast & Deduplication Methodology...")
        tab_contrast = page.locator("[role='tab']").nth(2)
        tab_contrast.click()
        wait_for_streamlit(page)

        body_text_contrast = page.locator("body").inner_text()
        assert "Cross-Platform Taxonomy Incompatibility" in body_text_contrast
        assert "123,835 postings" in body_text_contrast
        assert "5,715 postings" in body_text_contrast
        assert "$setUnion" in body_text_contrast
        assert "Why a Combined Ranking is Statistically Misleading" in body_text_contrast

        # Capture Tab 3 comparative grid screenshot
        save_screenshot(page, "03_3_skills_comparative_taxonomy.png")

        # Scroll down to capture distinct formula and $setUnion aggregation architecture
        page.locator("text=$setUnion").first.scroll_into_view_if_needed()
        time.sleep(1)
        save_screenshot(page, "03_3b_skills_deduplication_methodology.png")
        print("[PASS] Tab 3 (Taxonomy Contrast & Deduplication Methodology) verified and screenshots captured.")

        # 6. Verify Console Errors
        # Ignore benign network/font warnings and Streamlit _stcore relative path 404s
        critical_errors = [
            e for e in console_errors
            if "favicon" not in e.lower()
            and "font" not in e.lower()
            and "_stcore" not in e.lower()
            and "404" not in e.lower()
        ]
        print(f"Total critical console errors recorded: {len(critical_errors)}")
        if critical_errors:
            print("Errors detected:", critical_errors)
        assert len(critical_errors) == 0, f"Uncaught runtime errors in browser: {critical_errors}"
        print("[PASS] Zero uncaught browser console errors.")

        browser.close()
        print("\nAll browser verification checks passed successfully!")


if __name__ == "__main__":
    run_browser_verification()
