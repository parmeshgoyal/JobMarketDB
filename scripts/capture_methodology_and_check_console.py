import os
import shutil
import time
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
    print(f"Captured screenshot: {filename}")

def main():
    console_logs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--window-size=1920,1080"],
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        page.goto(f"{BASE_URL}/Platform_Comparison", wait_until="networkidle", timeout=30000)
        time.sleep(2.0)

        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.0)

        # Click the stExpander
        expander = page.locator("[data-testid='stExpander']")
        if expander.count() > 0:
            expander.first.locator("summary, [data-testid='stExpanderToggleIcon'], div").first.click()
            time.sleep(1.5)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.0)
            save_screenshot(page, "06_8_methodology_reference.png")
            print("Successfully expanded and captured 06_8_methodology_reference.png")
        else:
            print("stExpander not found by selector.")

        # Print all console messages to inspect the 404s
        print("\nAll console messages:")
        for log in console_logs:
            print("  ", log)

        browser.close()

if __name__ == "__main__":
    main()
