import os
from playwright.sync_api import sync_playwright

def run():
    user_data_dir = r"C:\Users\admin\Desktop\BeeBee AI\Relab\relab-trade-me-integration\playwright-profile"

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--disable-extensions",
                "--disable-popup-blocking"
            ]
        )

        page = browser.new_page()
        page.goto("https://relab.co.nz")
        print("Page title:", page.title())

        # Keep the browser open to check login/session
        input("Press ENTER to close...")
        browser.close()

if __name__ == "__main__":
    run()
