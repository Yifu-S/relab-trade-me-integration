from playwright.async_api import async_playwright
import asyncio

USER_DATA_DIR = r"C:\Users\admin\AppData\Local\Google\Chrome\User Data"


async def main():
    async with async_playwright() as pw:
        # Launch Chromium in headful mode with persistent context
        browser_context = await pw.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,  # headful so you can see the browser
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "referer": "https://relab.co.nz/",
                "origin": "https://relab.co.nz",
                "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh-HK;q=0.7,zh-TW;q=0.6,zh;q=0.5",
            },
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )

        page = await browser_context.new_page()

        await page.goto("https://relab.co.nz/login")

        # Now you can save cookies / continue automated tasks
        await page.wait_for_timeout(200000)
        print(await page.title())

        # Close the browser
        await browser_context.close()


asyncio.run(main())
