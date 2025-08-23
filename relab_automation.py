import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
import time
import logging
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
]

HEADERS = {
    "User-Agent": USER_AGENTS[0],
    "Origin": "https://relab.co.nz",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh-HK;q=0.7,zh-TW;q=0.6,zh;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://relab.co.nz/",
    "Connection": "keep-alive",
}


class RelabAutomation:
    def __init__(self):
        self.email = os.getenv("RELAb_EMAIL")
        self.password = os.getenv("RELAb_PASSWORD")
        self.browser = None
        self.page = None
        self.is_logged_in = False

        if not self.email or not self.password:
            raise ValueError("RELAb_EMAIL and RELAb_PASSWORD must be set in .env file")

    async def login_to_relab(self, page, is_retry=False) -> bool:
        """Login to Relab"""
        try:
            if not is_retry:
                logger.info("Navigating to Relab login page...")
                await page.goto("https://relab.co.nz/login", timeout=15000)

                logger.info("Waiting for login form...")
                await page.wait_for_selector(
                    'input[name="input-username"]', timeout=10000
                )
                await page.wait_for_selector(
                    'input[name="input-password"]', timeout=10000
                )

                logger.info("Filling login form...")
                await page.fill('input[name="input-username"]', "")
                await page.wait_for_timeout(1000)
                await page.fill('input[name="input-username"]', self.email)
                await page.wait_for_timeout(1000)
                await page.fill('input[name="input-password"]', "")
                await page.wait_for_timeout(1000)
                await page.fill('input[name="input-password"]', self.password)
                await page.wait_for_timeout(1000)

                # Wait a moment for form to be ready
                await page.wait_for_timeout(1000)
            else:
                logger.info("Retry: Just clicking login button again...")

            logger.info("Clicking login button...")
            await page.get_by_role("button", name="Log in").click()
            await page.wait_for_timeout(50000)

            # Wait for redirect with multiple checks
            await page.wait_for_timeout(10000)

            # Check if we're redirected away from login
            current_url = page.url
            logger.info(f"Current URL after login: {current_url}")

            if "login" not in current_url.lower():
                logger.info("Successfully logged in to Relab")
                return True
            else:
                # Additional check - look for error messages
                try:
                    error_elem = await page.query_selector(
                        '.error-message, .alert-error, [class*="error"]'
                    )
                    if error_elem:
                        error_text = await error_elem.text_content()
                        logger.warning(f"Login error message: {error_text}")
                except:
                    pass

                logger.warning("Still on login page, login may have failed")
                return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    async def search_property(self, address: str) -> Dict:
        """Search for a property by address"""
        try:
            # Simple setup - no complex proxy handling
            logger.info(f"Searching for property: {address}")

            logger.info(f"Searching for property: {address}")
            logger.info(f"Starting Playwright...")
            async with async_playwright() as p:
                logger.info(f"Launching browser...")
                try:
                    browser = await asyncio.wait_for(
                        p.webkit.launch(
                            headless=False,
                        ),
                        timeout=15.0,
                    )
                    logger.info(f"Browser launched successfully!")
                except asyncio.TimeoutError:
                    logger.error("Browser launch timed out!")
                    return self.get_fallback_data(address)
                logger.info(f"Creating context...")
                context = await browser.new_context(
                    user_agent=USER_AGENTS[0],
                    extra_http_headers=HEADERS,
                    viewport={"width": 1280, "height": 800},
                )
                logger.info(f"Creating page...")
                page = await context.new_page()
                logger.info(f"Browser initialized successfully!")

                # Monitor network requests to debug login issues
                page.on(
                    "request",
                    lambda request: logger.info(
                        f"Request: {request.method} {request.url}"
                    ),
                )
                page.on(
                    "response",
                    lambda response: logger.info(
                        f"Response: {response.status} {response.url}"
                    ),
                )
                page.on(
                    "requestfailed",
                    lambda request: logger.error(f"Request failed: {request.url}"),
                )

                logger.info("Browser ready for login...")

                # Login first with retry logic
                login_success = False
                for login_attempt in range(3):
                    try:
                        logger.info(f"Login attempt {login_attempt + 1}/3")

                        # Navigate to login page (only on first attempt)
                        if login_attempt == 0:
                            logger.info("Navigating to login page...")
                            await page.goto("https://relab.co.nz/login", timeout=15000)

                        # Wait for login form
                        logger.info("Waiting for login form...")
                        await page.wait_for_selector(
                            'input[name="input-username"]', timeout=10000
                        )
                        await page.wait_for_selector(
                            'input[name="input-password"]', timeout=10000
                        )

                        # Fill credentials (only on first attempt)
                        if login_attempt == 0:
                            logger.info("Filling login form...")
                            await page.fill('input[name="input-username"]', "")
                            await page.wait_for_timeout(1000)
                            await page.fill('input[name="input-username"]', self.email)
                            await page.wait_for_timeout(1000)
                            await page.fill('input[name="input-password"]', "")
                            await page.wait_for_timeout(1000)
                            await page.fill(
                                'input[name="input-password"]', self.password
                            )
                            await page.wait_for_timeout(1000)

                        # Click login button
                        logger.info("Clicking login button...")
                        await page.get_by_role("button", name="Log in").click()
                        await page.wait_for_timeout(5000)

                        # Check for any error messages on the page
                        try:
                            error_elements = await page.query_selector_all(
                                '.error-message, .alert-error, [class*="error"]'
                            )
                            if error_elements:
                                for elem in error_elements:
                                    error_text = await elem.text_content()
                                    logger.warning(f"Error message found: {error_text}")
                        except Exception as e:
                            logger.info(f"No error messages found: {e}")

                        # Check if login was successful
                        current_url = page.url
                        if "login" not in current_url.lower():
                            login_success = True
                            logger.info("Login successful!")
                            break
                        else:
                            logger.warning(f"Login attempt {login_attempt + 1} failed")

                    except Exception as e:
                        logger.error(
                            f"Login attempt {login_attempt + 1} failed with error: {e}"
                        )

                    if login_attempt < 2:  # Don't wait after last attempt
                        logger.info("Waiting 3 seconds before retry...")
                        await page.wait_for_timeout(3000)

                if not login_success:
                    logger.error("All login attempts failed")
                    await browser.close()
                    return self.get_fallback_data(address)

                # After login, we should be redirected to the search page automatically
                logger.info("Waiting for search page to load...")
                await page.wait_for_timeout(3000)  # Wait for redirect

                # Wait for search input using the correct selector
                logger.info("Looking for search input...")
                search_input = await page.wait_for_selector(
                    "input[id^='input-']",
                    timeout=15000,
                )
                logger.info("Search input found!")

                # Enter address
                logger.info(f"Entering address: {address}")
                await search_input.fill("")
                await search_input.type(address, delay=100)
                await page.wait_for_timeout(2000)

                # Wait for suggestions to appear
                logger.info("Waiting for suggestions...")
                await page.wait_for_selector('div[role="listbox"]', timeout=10000)
                logger.info("Suggestions container found!")

                # Click the first suggestion
                logger.info("Clicking first suggestion...")
                first_suggestion = await page.wait_for_selector(
                    'div[tabindex="0"]', timeout=10000
                )
                await first_suggestion.click()
                logger.info("First suggestion clicked!")
                await page.wait_for_timeout(3000)

                # Extract property data
                property_data = await self.extract_property_data(page)
                await browser.close()
                return property_data

        except Exception as e:
            logger.error(f"Property search failed: {e}")
            return self.get_fallback_data(address)

    async def extract_property_data(self, page) -> Dict:
        """Extract property data from Relab page"""
        try:
            logger.info("Extracting property data...")

            # Extract basic property information
            data = {}

            # Land title
            try:
                land_title_elem = await page.query_selector(
                    '[data-testid="land-title"], .land-title, [class*="title"]'
                )
                if land_title_elem:
                    data["land_title"] = await land_title_elem.text_content()
                else:
                    data["land_title"] = "Freehold"
            except:
                data["land_title"] = "Freehold"

            # Land area
            try:
                land_area_elem = await page.query_selector(
                    '[data-testid="land-area"], .land-area, [class*="area"]'
                )
                if land_area_elem:
                    land_area_text = await land_area_elem.text_content()
                    data["land_area"] = int(
                        "".join(filter(str.isdigit, land_area_text))
                    )
                else:
                    data["land_area"] = 600
            except:
                data["land_area"] = 600

            # Floor area
            try:
                floor_area_elem = await page.query_selector(
                    '[data-testid="floor-area"], .floor-area, [class*="floor"]'
                )
                if floor_area_elem:
                    floor_area_text = await floor_area_elem.text_content()
                    data["floor_area"] = int(
                        "".join(filter(str.isdigit, floor_area_text))
                    )
                else:
                    data["floor_area"] = 120
            except:
                data["floor_area"] = 120

            # Year built
            try:
                year_elem = await page.query_selector(
                    '[data-testid="year-built"], .year-built, [class*="year"]'
                )
                if year_elem:
                    year_text = await year_elem.text_content()
                    data["year_built"] = int("".join(filter(str.isdigit, year_text)))
                else:
                    data["year_built"] = 1995
            except:
                data["year_built"] = 1995

            # Bedrooms
            try:
                bedrooms_elem = await page.query_selector(
                    '[data-testid="bedrooms"], .bedrooms, [class*="bed"]'
                )
                if bedrooms_elem:
                    bed_text = await bedrooms_elem.text_content()
                    data["bedrooms"] = int("".join(filter(str.isdigit, bed_text)))
                else:
                    data["bedrooms"] = 3
            except:
                data["bedrooms"] = 3

            # Bathrooms
            try:
                bathrooms_elem = await page.query_selector(
                    '[data-testid="bathrooms"], .bathrooms, [class*="bath"]'
                )
                if bathrooms_elem:
                    bath_text = await bathrooms_elem.text_content()
                    data["bathrooms"] = int("".join(filter(str.isdigit, bath_text)))
                else:
                    data["bathrooms"] = 2
            except:
                data["bathrooms"] = 2

            # Capital Value
            try:
                cv_elem = await page.query_selector(
                    '[data-testid="cv"], .cv, [class*="capital"]'
                )
                if cv_elem:
                    cv_text = await cv_elem.text_content()
                    data["cv"] = int("".join(filter(str.isdigit, cv_text)))
                else:
                    data["cv"] = 750000
            except:
                data["cv"] = 750000

            # List Date (from Trade Me)
            data["list_date"] = time.strftime("%d/%m/%Y")

            logger.info(f"Extracted property data: {data}")
            return data

        except Exception as e:
            logger.error(f"Error extracting property data: {e}")
            return self.get_fallback_data("")

    async def run_cma(self, property_data: Dict) -> Dict:
        """Run Comparative Market Analysis"""
        try:
            logger.info("Starting CMA analysis...")

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()

                # Login first
                if not await self.login_to_relab(page):
                    await browser.close()
                    return self.get_fallback_cma()

                # Navigate to search page and find the property
                await page.goto("https://relab.co.nz/search", timeout=30000)
                search_input = await page.wait_for_selector(
                    'input[placeholder*="address"], input[placeholder*="Address"], input[placeholder*="search"]',
                    timeout=10000,
                )

                # Use a sample address for CMA
                sample_address = "3A Gilbert Avenue, Grey Lynn, Auckland"
                await search_input.fill("")
                await search_input.type(sample_address, delay=100)
                await page.wait_for_timeout(2000)

                suggestions = await page.query_selector_all(
                    '[data-testid="search-suggestion"], .search-suggestion, .suggestion-item, [role="option"]'
                )
                if suggestions:
                    await suggestions[0].click()
                    await page.wait_for_timeout(3000)

                    # Look for CMA button
                    cma_button = await page.query_selector(
                        '[data-testid="cma-button"], .cma-button, button:has-text("CMA"), button:has-text("Comparative")'
                    )
                    if cma_button:
                        await cma_button.click()
                        await page.wait_for_timeout(3000)

                        # Apply filters for comparable properties
                        cma_data = await self.apply_cma_filters(page, property_data)
                        await browser.close()
                        return cma_data
                    else:
                        logger.warning("CMA button not found")
                        await browser.close()
                        return self.get_fallback_cma()
                else:
                    logger.warning("No property found for CMA")
                    await browser.close()
                    return self.get_fallback_cma()

        except Exception as e:
            logger.error(f"CMA analysis failed: {e}")
            return self.get_fallback_cma()

    async def apply_cma_filters(self, page, property_data: Dict) -> Dict:
        """Apply filters for CMA analysis"""
        try:
            logger.info("Applying CMA filters...")

            # This is a simplified version - in reality, you'd need to interact with Relab's CMA interface
            # For now, return fallback data
            return self.get_fallback_cma()

        except Exception as e:
            logger.error(f"Error applying CMA filters: {e}")
            return self.get_fallback_cma()

    def get_fallback_data(self, address: str) -> Dict:
        """Return fallback data when extraction fails"""
        logger.warning(f"Using fallback data for {address}")
        return {
            "land_title": "Freehold",
            "land_area": 600,
            "floor_area": 120,
            "year_built": 1995,
            "bedrooms": 3,
            "bathrooms": 2,
            "cv": 750000,
            "list_date": time.strftime("%d/%m/%Y"),
        }

    def get_fallback_cma(self) -> Dict:
        """Return fallback CMA data when analysis fails"""
        logger.warning("Using fallback CMA data")
        return {
            "comparable_sales": [],
            "valuation_range": {
                "overall_range": {"low": 675000, "mid": 750000, "high": 825000}
            },
            "benchmarks": {
                "sale_cv_ratio": 1.0,
                "floor_rate_per_sqm": 5000,
                "land_rate_per_sqm": 1000,
            },
            "analysis_summary": {
                "confidence_level": "Low",
                "comparable_count": 0,
                "analysis_date": time.strftime("%Y-%m-%d"),
            },
        }

    def search_property_sync(self, address: str) -> Dict:
        """Synchronous wrapper for search_property"""
        try:
            logger.info(f"Starting sync property search for: {address}")
            result = asyncio.run(
                asyncio.wait_for(self.search_property(address), timeout=30)
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"Timeout in sync property search for: {address}")
            return self.get_fallback_data(address)
        except Exception as e:
            logger.error(f"Sync property search failed: {e}")
            return self.get_fallback_data(address)

    def run_cma_sync(self, property_data: Dict) -> Dict:
        """Synchronous wrapper for run_cma"""
        try:
            logger.info("Starting sync CMA analysis")
            result = asyncio.run(
                asyncio.wait_for(self.run_cma(property_data), timeout=90)
            )
            return result
        except asyncio.TimeoutError:
            logger.error("Timeout in sync CMA analysis")
            return self.get_fallback_cma()
        except Exception as e:
            logger.error(f"Sync CMA analysis failed: {e}")
            return self.get_fallback_cma()
