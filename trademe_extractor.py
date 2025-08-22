#!/usr/bin/env python3
"""
Trade Me Address Extractor
Extracts only the property address from Trade Me listings using Playwright
"""

import asyncio
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)


class TradeMeExtractor:
    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None

    def extract_from_url(self, trademe_url):
        """Extract property address from Trade Me URL using Playwright"""
        try:
            logger.info(f"Extracting address from Trade Me URL: {trademe_url}")

            # Run the async extraction
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                address = loop.run_until_complete(self._extract_address_async(trademe_url))
                logger.info(f"Extracted address: {address}")
                return {"address": address, "url": trademe_url}
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Error extracting Trade Me address: {e}")
            return {"address": "Address not found", "url": trademe_url}

    async def _extract_address_async(self, trademe_url):
        """Async method to extract property address using Playwright"""
        try:
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            self.page = await self.browser.new_page()

            # Set viewport
            await self.page.set_viewport_size({"width": 1280, "height": 720})

            # Navigate to the page
            await self.page.goto(trademe_url, wait_until="networkidle", timeout=30000)

            # Extract address using the specific selector
            address_element = await self.page.query_selector('h1[class*="tm-property-listing-body__location"]')
            
            if address_element:
                address = await address_element.text_content()
                if address and address.strip():
                    return address.strip()
            
            # Fallback to page title if specific selector not found
            title = await self.page.title()
            if title and len(title) > 5:
                return title.strip()
            
            return "Address not found"

        except Exception as e:
            logger.error(f"Error in async address extraction: {e}")
            return "Address not found"
        finally:
            # Clean up
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
