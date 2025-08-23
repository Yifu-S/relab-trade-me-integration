#!/usr/bin/env python3
"""
Trade Me Address Extractor
Extracts property address and listing date from Trade Me listings using Playwright
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

# --- Define Base URLs for different listing types ---
BASE_URL_RENTAL = "https://www.trademe.co.nz/a/property/residential/rent/search"
BASE_URL_SALE = "https://www.trademe.co.nz/a/property/residential/sale/search"
# --- End Base URLs ---

# --- Global variable to hold the current BASE_URL based on listing type ---
CURRENT_BASE_URL = BASE_URL_RENTAL  # Default, will be changed based on argument
# --- End Global variable ---

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
]

HEADERS = [
    {
        "referer": "https://www.trademe.co.nz/",
        "accept-language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
    },
]


def parse_list_date(date_text: str) -> str:
    """Parses 'Listed: Mon, 4 Aug' or 'Listed: Today' into 'dd/mm/yyyy'."""
    if not date_text:
        return None
    date_text = date_text.strip()
    try:
        if "today" in date_text.lower():
            # Return today's date formatted as dd/mm/yyyy
            return (
                datetime.now(timezone(timedelta(hours=12)))
                .astimezone(timezone.utc)
                .strftime("%d/%m/%Y")
            )
        elif "yesterday" in date_text.lower():
            # Return yesterday's date formatted as dd/mm/yyyy
            return (
                datetime.now(timezone(timedelta(hours=12))).astimezone(timezone.utc)
                - timedelta(days=1)
            ).strftime("%d/%m/%Y")
        else:
            # Assume format like "Listed: Mon, 4 Aug"
            # Remove "Listed:" prefix
            date_part = date_text.split(":", 1)[1].strip()  # Split on first ':'
            # Parse the date string like "Mon, 4 Aug"
            current_date = datetime.now(timezone(timedelta(hours=12))).astimezone(
                timezone.utc
            )
            current_year = current_date.year

            # Try current year first
            try:
                parsed_date = datetime.strptime(
                    f"{date_part} {current_year}", "%a, %d %b %Y"
                )

                # Make parsed_date timezone-aware for comparison
                parsed_date = parsed_date.replace(tzinfo=timezone(timedelta(hours=12)))

                # If the parsed date is in the future (e.g., Sep 15 when today is Aug 25),
                # it means the listing is from last year
                if parsed_date > current_date:
                    parsed_date = datetime.strptime(
                        f"{date_part} {current_year - 1}", "%a, %d %b %Y"
                    )
                    parsed_date = parsed_date.replace(
                        tzinfo=timezone(timedelta(hours=12))
                    )

                return parsed_date.strftime("%d/%m/%Y")
            except ValueError:
                # If current year fails, try previous year
                try:
                    parsed_date = datetime.strptime(
                        f"{date_part} {current_year - 1}", "%a, %d %b %Y"
                    )
                    parsed_date = parsed_date.replace(
                        tzinfo=timezone(timedelta(hours=12))
                    )
                    return parsed_date.strftime("%d/%m/%Y")
                except ValueError:
                    # If both fail, return None
                    return None

    except Exception as e:
        print(f"\n⚠️ Error parsing list date '{date_text}': {e}")
        return None


class TradeMeExtractor:
    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None

    def extract_from_url(self, trademe_url):
        """Extract property address and listing date from Trade Me URL using Playwright"""
        try:
            logger.info(f"Extracting data from Trade Me URL: {trademe_url}")

            # Run the async extraction
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._scrape_listing_async(trademe_url)
                )
                logger.info(f"Extracted data: {result}")
                return result
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Error extracting Trade Me data: {e}")
            return {
                "address": "Address not found",
                "url": trademe_url,
                "listing_date": None,
            }

    async def _scrape_listing_async(self, listing_url: str, retry: int = 2):
        """Async method to scrape listing data using Playwright"""
        try:
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            # Determine listing type based on URL
            is_rental = "/rent/" in listing_url
            is_sale = "/sale/" in listing_url
            listing_type = "rental" if is_rental else "sale" if is_sale else "unknown"

            # Set up browser context with random user agent and headers
            user_agent = random.choice(USER_AGENTS)
            extra_headers = random.choice(HEADERS).copy()
            extra_headers["user-agent"] = user_agent

            context = await self.browser.new_context(
                user_agent=user_agent,
                extra_http_headers=extra_headers,
                locale="en-US",
                timezone_id="Pacific/Auckland",
                viewport={"width": 1280, "height": 800},
            )

            # Add a slight delay
            await asyncio.sleep(random.uniform(2, 3))

            self.page = await context.new_page()

            # Navigate to the page
            await self.page.goto(listing_url, timeout=20000)

            # Wait for the key element that signifies the listing content has loaded
            await self.page.wait_for_selector(
                "h1[class*='tm-property-listing-body__location']", timeout=20000
            )

            # Extract address using the specific selector
            address_element = await self.page.query_selector(
                'h1[class*="tm-property-listing-body__location"]'
            )

            address = "Address not found"
            if address_element:
                address_text = await address_element.text_content()
                if address_text and address_text.strip():
                    address = address_text.strip()

            # Extract listing date
            listing_date = None
            try:
                # Look for listing date in various selectors
                date_selectors = [
                    '[data-testid="listing-date"]',
                    ".listing-date",
                    ".date-listed",
                    '[class*="date"]',
                    '[class*="listed"]',
                ]

                for selector in date_selectors:
                    date_element = await self.page.query_selector(selector)
                    if date_element:
                        date_text = await date_element.text_content()
                        if date_text and "listed" in date_text.lower():
                            listing_date = parse_list_date(date_text)
                            break
            except Exception as e:
                logger.error(f"Error extracting listing date: {e}")

            return {
                "address": address,
                "url": listing_url,
                "listing_date": listing_date,
                "listing_type": listing_type,
            }

        except Exception as e:
            logger.error(f"Error in async scraping: {e}")
            return {
                "address": "Address not found",
                "url": listing_url,
                "listing_date": None,
            }
        finally:
            # Clean up
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
