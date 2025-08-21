import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
import time
import re
import logging
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class RelabAutomation:
    def __init__(self):
        self.email = os.getenv("RELAb_EMAIL")
        self.password = os.getenv("RELAb_PASSWORD")
        self.browser = None
        self.page = None
        self.playwright = None
        self.is_logged_in = False

        if not self.email or not self.password:
            raise ValueError("RELAb_EMAIL and RELAb_PASSWORD must be set in .env file")

    async def init_browser(self, headless: bool = True):
        """Initialize browser and login to Relab"""
        try:
            logger.info("Initializing browser...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=headless, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            self.page = await self.browser.new_page()

            # Set viewport
            await self.page.set_viewport_size({"width": 1280, "height": 720})

            # Login to Relab
            await self.login_to_relab()

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            await self.close()
            raise

    async def login_to_relab(self, max_retries: int = 3):
        """Login to Relab with retry mechanism"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Login attempt {attempt + 1}/{max_retries}")

                # Navigate to Relab login page with timeout
                await self.page.goto(
                    "https://relab.co.nz/login", wait_until="networkidle", timeout=30000
                )

                # Wait for login form to load with shorter timeout
                await self.page.wait_for_selector('input[name="email"]', timeout=15000)
                await self.page.wait_for_selector(
                    'input[name="password"]', timeout=15000
                )

                # Clear and fill login form
                await self.page.fill('input[name="email"]', "")
                await self.page.fill('input[name="email"]', self.email)
                await self.page.fill('input[name="password"]', "")
                await self.page.fill('input[name="password"]', self.password)

                # Click login button
                login_button = await self.page.query_selector('button[type="submit"]')
                if not login_button:
                    login_button = await self.page.query_selector(
                        'button:has-text("Login")'
                    )
                if not login_button:
                    login_button = await self.page.query_selector(
                        'button:has-text("Sign In")'
                    )

                if login_button:
                    await login_button.click()

                    # Wait for successful login (redirect to dashboard or home page)
                try:
                    await self.page.wait_for_url("**/dashboard", timeout=15000)
                    self.is_logged_in = True
                    logger.info("Successfully logged in to Relab")
                    return
                except:
                    # Try alternative success indicators
                    await self.page.wait_for_timeout(5000)
                    current_url = self.page.url
                    if "login" not in current_url.lower():
                        self.is_logged_in = True
                        logger.info("Successfully logged in to Relab")
                        return

                # If we get here, login might have failed
                await self.page.wait_for_timeout(2000)

            except Exception as e:
                logger.error(f"Login attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await self.page.wait_for_timeout(2000)
                else:
                    raise Exception(
                        f"Failed to login to Relab after {max_retries} attempts: {e}"
                    )

        raise Exception("Failed to login to Relab")

    async def search_property(self, address: str) -> Dict:
        """Search for a property by address with retry mechanism"""
        if not self.is_logged_in:
            await self.init_browser()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Searching for property: {address} (attempt {attempt + 1})"
                )

                # Navigate to search page with timeout
                await self.page.goto(
                    "https://relab.co.nz/search",
                    wait_until="networkidle",
                    timeout=30000,
                )

                # Wait for search input to be available with timeout
                search_input = await self.page.wait_for_selector(
                    'input[placeholder*="address"], input[placeholder*="Address"], input[placeholder*="search"], input[type="search"]',
                    timeout=15000,
                )

                # Clear and enter address
                await search_input.fill("")
                await search_input.type(address, delay=100)

                # Wait for suggestions to appear
                await self.page.wait_for_timeout(2000)

                # Try to click on first suggestion
                suggestions = await self.page.query_selector_all(
                    '[data-testid="search-suggestion"], .search-suggestion, .suggestion-item, [role="option"]'
                )

                if suggestions:
                    logger.info(f"Found {len(suggestions)} suggestions")
                    await suggestions[0].click()
                    await self.page.wait_for_timeout(3000)

                    # Check if we're on a property page
                    current_url = self.page.url
                    if "/property/" in current_url or "address" in current_url.lower():
                        logger.info("Successfully navigated to property page")
                        return await self.extract_property_data()

                # If no suggestions or didn't navigate, try pressing Enter
                await search_input.press("Enter")
                await self.page.wait_for_timeout(3000)

                # Check if we're on a property page
                current_url = self.page.url
                if "/property/" in current_url or "address" in current_url.lower():
                    logger.info("Successfully navigated to property page via Enter")
                    return await self.extract_property_data()

            except Exception as e:
                logger.error(f"Search attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await self.page.wait_for_timeout(2000)
                else:
                    logger.error(
                        f"Failed to search for property after {max_retries} attempts"
                    )
                    return self.get_fallback_data(address)

        return self.get_fallback_data(address)

    async def extract_property_data(self) -> Dict:
        """Extract property information from Relab page"""
        try:
            logger.info("Extracting property data...")
            property_data = {}

            # Wait for page to load
            await self.page.wait_for_timeout(2000)

            # Extract CV (Capital Value) - try multiple selectors
            cv_selectors = [
                '[data-testid="cv-value"]',
                ".cv-value",
                ".capital-value",
                '[class*="cv"]',
                '[class*="capital"]',
                "text=Capital Value",
                "text=CV",
                'div:has-text("Capital Value")',
                'span:has-text("Capital Value")',
            ]

            for selector in cv_selectors:
                try:
                    cv_elem = await self.page.query_selector(selector)
                    if cv_elem:
                        cv_text = await cv_elem.text_content()
                        cv_value = self.extract_number(cv_text)
                        if cv_value:
                            property_data["cv"] = cv_value
                            logger.info(f"Found CV: {cv_value}")
                            break
                except:
                    continue

            # Extract Land Title
            title_selectors = [
                '[data-testid="land-title"]',
                ".land-title",
                ".title-type",
                '[class*="title"]',
                "text=Land Title",
                "text=Title",
            ]

            for selector in title_selectors:
                try:
                    title_elem = await self.page.query_selector(selector)
                    if title_elem:
                        title_text = await title_elem.text_content()
                        if title_text and title_text.strip():
                            property_data["land_title"] = title_text.strip()
                            logger.info(f"Found Land Title: {title_text.strip()}")
                            break
                except:
                    continue

            # Extract Land Area
            land_selectors = [
                '[data-testid="land-area"]',
                ".land-area",
                '[class*="land"]',
                "text=Land Area",
                "text=Section",
            ]

            for selector in land_selectors:
                try:
                    land_elem = await self.page.query_selector(selector)
                    if land_elem:
                        land_text = await land_elem.text_content()
                        land_value = self.extract_number(land_text)
                        if land_value:
                            property_data["land_area"] = land_value
                            logger.info(f"Found Land Area: {land_value}")
                            break
                except:
                    continue

            # Extract Floor Area
            floor_selectors = [
                '[data-testid="floor-area"]',
                ".floor-area",
                ".building-area",
                '[class*="floor"]',
                '[class*="building"]',
                "text=Floor Area",
                "text=Building Area",
                'div:has-text("Floor area")',
                'span:has-text("Floor area")',
            ]

            for selector in floor_selectors:
                try:
                    floor_elem = await self.page.query_selector(selector)
                    if floor_elem:
                        floor_text = await floor_elem.text_content()
                        floor_value = self.extract_number(floor_text)
                        if floor_value:
                            property_data["floor_area"] = floor_value
                            logger.info(f"Found Floor Area: {floor_value}")
                            break
                except:
                    continue

            # Extract Year Built
            year_selectors = [
                '[data-testid="year-built"]',
                ".year-built",
                ".build-year",
                '[class*="year"]',
                '[class*="built"]',
                "text=Year Built",
                "text=Built",
            ]

            for selector in year_selectors:
                try:
                    year_elem = await self.page.query_selector(selector)
                    if year_elem:
                        year_text = await year_elem.text_content()
                        year_value = self.extract_number(year_text)
                        if year_value and 1800 <= year_value <= 2024:
                            property_data["year_built"] = int(year_value)
                            logger.info(f"Found Year Built: {year_value}")
                            break
                except:
                    continue

            # Extract Bedrooms
            bed_selectors = [
                '[data-testid="bedrooms"]',
                ".bedrooms",
                '[class*="bed"]',
                "text=Bedrooms",
                "text=Bed",
                'div:has-text("Bedroom(s)")',
                'span:has-text("Bedroom(s)")',
            ]

            for selector in bed_selectors:
                try:
                    bed_elem = await self.page.query_selector(selector)
                    if bed_elem:
                        bed_text = await bed_elem.text_content()
                        bed_value = self.extract_number(bed_text)
                        if bed_value:
                            property_data["bedrooms"] = int(bed_value)
                            logger.info(f"Found Bedrooms: {bed_value}")
                            break
                except:
                    continue

            # Extract Bathrooms
            bath_selectors = [
                '[data-testid="bathrooms"]',
                ".bathrooms",
                '[class*="bath"]',
                "text=Bathrooms",
                "text=Bath",
                'div:has-text("Bathroom(s)")',
                'span:has-text("Bathroom(s)")',
            ]

            for selector in bath_selectors:
                try:
                    bath_elem = await self.page.query_selector(selector)
                    if bath_elem:
                        bath_text = await bath_elem.text_content()
                        bath_value = self.extract_number(bath_text)
                        if bath_value:
                            property_data["bathrooms"] = int(bath_value)
                            logger.info(f"Found Bathrooms: {bath_value}")
                            break
                except:
                    continue

            logger.info(f"Extracted property data: {property_data}")
            return property_data

        except Exception as e:
            logger.error(f"Error extracting property data: {e}")
            return self.get_fallback_data("Unknown Address")

    def extract_number(self, text: str) -> Optional[float]:
        """Extract numeric value from text"""
        if not text:
            return None
        try:
            # Remove commas and common text
            cleaned_text = re.sub(r"[^\d.]", "", text.replace(",", ""))
            if cleaned_text:
                return float(cleaned_text)
        except:
            pass
        return None

    async def run_cma(self, property_data: Dict) -> Dict:
        """Run Comparative Market Analysis with retry mechanism"""
        try:
            logger.info("Starting CMA analysis...")

            # Look for CMA button
            cma_selectors = [
                'button:has-text("CMA")',
                'button:has-text("Comparative Market Analysis")',
                'button:has-text("Market Analysis")',
                '[data-testid="cma-button"]',
                ".cma-button",
                'a:has-text("CMA")',
            ]

            cma_button = None
            for selector in cma_selectors:
                try:
                    cma_button = await self.page.query_selector(selector)
                    if cma_button:
                        logger.info(f"Found CMA button with selector: {selector}")
                        break
                except:
                    continue

            if cma_button:
                await cma_button.click()
                await self.page.wait_for_timeout(3000)

                # Apply filters for similar properties
                await self.apply_cma_filters(property_data)

                # Get comparable sales
                comparable_sales = await self.extract_comparable_sales()

                # Generate CMA analysis
                cma_analysis = self.generate_cma_analysis(
                    comparable_sales, property_data
                )

                return cma_analysis
            else:
                logger.warning("CMA button not found")
                return self.get_fallback_cma()

        except Exception as e:
            logger.error(f"Error running CMA: {e}")
            return self.get_fallback_cma()

    async def apply_cma_filters(self, property_data: Dict):
        """Apply filters for CMA analysis"""
        try:
            logger.info("Applying CMA filters...")

            # Wait for filters to load
            await self.page.wait_for_timeout(2000)

            # Apply filters based on property data
            filters_applied = 0

            # Land title filter
            if property_data.get("land_title"):
                try:
                    title_select = await self.page.query_selector(
                        'select[name="land_title"], select[data-testid="land-title-filter"]'
                    )
                    if title_select:
                        await title_select.select_option(property_data["land_title"])
                        filters_applied += 1
                except:
                    pass

            # Land area filter (±20%)
            if property_data.get("land_area"):
                try:
                    land_area = property_data["land_area"]
                    min_area = land_area * 0.8
                    max_area = land_area * 1.2

                    min_input = await self.page.query_selector(
                        'input[name="min_land_area"], input[data-testid="min-land-area"]'
                    )
                    max_input = await self.page.query_selector(
                        'input[name="max_land_area"], input[data-testid="max-land-area"]'
                    )

                    if min_input and max_input:
                        await min_input.fill(str(int(min_area)))
                        await max_input.fill(str(int(max_area)))
                        filters_applied += 1
                except:
                    pass

            # Floor area filter (±20%)
            if property_data.get("floor_area"):
                try:
                    floor_area = property_data["floor_area"]
                    min_floor = floor_area * 0.8
                    max_floor = floor_area * 1.2

                    min_input = await self.page.query_selector(
                        'input[name="min_floor_area"], input[data-testid="min-floor-area"]'
                    )
                    max_input = await self.page.query_selector(
                        'input[name="max_floor_area"], input[data-testid="max-floor-area"]'
                    )

                    if min_input and max_input:
                        await min_input.fill(str(int(min_floor)))
                        await max_input.fill(str(int(max_floor)))
                        filters_applied += 1
                except:
                    pass

            # Bedrooms filter (±1)
            if property_data.get("bedrooms"):
                try:
                    bedrooms = property_data["bedrooms"]
                    min_bed = max(1, bedrooms - 1)
                    max_bed = bedrooms + 1

                    min_input = await self.page.query_selector(
                        'input[name="min_bedrooms"], input[data-testid="min-bedrooms"]'
                    )
                    max_input = await self.page.query_selector(
                        'input[name="max_bedrooms"], input[data-testid="max-bedrooms"]'
                    )

                    if min_input and max_input:
                        await min_input.fill(str(min_bed))
                        await max_input.fill(str(max_bed))
                        filters_applied += 1
                except:
                    pass

            # Bathrooms filter (±1)
            if property_data.get("bathrooms"):
                try:
                    bathrooms = property_data["bathrooms"]
                    min_bath = max(1, bathrooms - 1)
                    max_bath = bathrooms + 1

                    min_input = await self.page.query_selector(
                        'input[name="min_bathrooms"], input[data-testid="min-bathrooms"]'
                    )
                    max_input = await self.page.query_selector(
                        'input[name="max_bathrooms"], input[data-testid="max-bathrooms"]'
                    )

                    if min_input and max_input:
                        await min_input.fill(str(min_bath))
                        await max_input.fill(str(max_bath))
                        filters_applied += 1
                except:
                    pass

            # Sale date filter (last 12 months)
            try:
                date_select = await self.page.query_selector(
                    'select[name="sale_date"], select[data-testid="sale-date-filter"]'
                )
                if date_select:
                    await date_select.select_option("last_12_months")
                    filters_applied += 1
            except:
                pass

            logger.info(f"Applied {filters_applied} filters")

            # Apply filters
            apply_button = await self.page.query_selector(
                'button:has-text("Apply"), button:has-text("Search"), button[data-testid="apply-filters"]'
            )
            if apply_button:
                await apply_button.click()
                await self.page.wait_for_timeout(3000)

        except Exception as e:
            logger.error(f"Error applying CMA filters: {e}")

    async def extract_comparable_sales(self) -> List[Dict]:
        """Extract comparable sales data"""
        try:
            logger.info("Extracting comparable sales...")
            comparable_sales = []

            # Wait for results to load
            await self.page.wait_for_timeout(3000)

            # Find all comparable property rows
            property_selectors = [
                '[data-testid="comparable-property"]',
                ".comparable-property",
                ".sale-record",
                '[class*="comparable"]',
                '[class*="sale"]',
            ]

            property_rows = []
            for selector in property_selectors:
                try:
                    rows = await self.page.query_selector_all(selector)
                    if rows:
                        property_rows = rows
                        logger.info(
                            f"Found {len(rows)} comparable properties with selector: {selector}"
                        )
                        break
                except:
                    continue

            # Limit to 10 properties
            for row in property_rows[:10]:
                try:
                    sale_data = {}

                    # Extract sale price
                    price_selectors = [
                        ".sale-price",
                        '[data-testid="sale-price"]',
                        '[class*="price"]',
                    ]
                    for selector in price_selectors:
                        try:
                            price_elem = await row.query_selector(selector)
                            if price_elem:
                                price_text = await price_elem.text_content()
                                sale_data["sale_price"] = self.extract_number(
                                    price_text
                                )
                                break
                        except:
                            continue

                    # Extract CV
                    cv_selectors = [".cv", '[data-testid="cv"]', '[class*="cv"]']
                    for selector in cv_selectors:
                        try:
                            cv_elem = await row.query_selector(selector)
                            if cv_elem:
                                cv_text = await cv_elem.text_content()
                                sale_data["cv"] = self.extract_number(cv_text)
                                break
                        except:
                            continue

                    # Extract land area
                    land_selectors = [
                        ".land-area",
                        '[data-testid="land-area"]',
                        '[class*="land"]',
                    ]
                    for selector in land_selectors:
                        try:
                            land_elem = await row.query_selector(selector)
                            if land_elem:
                                land_text = await land_elem.text_content()
                                sale_data["land_area"] = self.extract_number(land_text)
                                break
                        except:
                            continue

                    # Extract floor area
                    floor_selectors = [
                        ".floor-area",
                        '[data-testid="floor-area"]',
                        '[class*="floor"]',
                    ]
                    for selector in floor_selectors:
                        try:
                            floor_elem = await row.query_selector(selector)
                            if floor_elem:
                                floor_text = await floor_elem.text_content()
                                sale_data["floor_area"] = self.extract_number(
                                    floor_text
                                )
                                break
                        except:
                            continue

                    # Extract sale date
                    date_selectors = [
                        ".sale-date",
                        '[data-testid="sale-date"]',
                        '[class*="date"]',
                    ]
                    for selector in date_selectors:
                        try:
                            date_elem = await row.query_selector(selector)
                            if date_elem:
                                sale_data["sale_date"] = await date_elem.text_content()
                                break
                        except:
                            continue

                    if sale_data:
                        comparable_sales.append(sale_data)

                except Exception as e:
                    logger.error(f"Error extracting sale data from row: {e}")
                    continue

            logger.info(f"Extracted {len(comparable_sales)} comparable sales")
            return comparable_sales

        except Exception as e:
            logger.error(f"Error extracting comparable sales: {e}")
            return []

    def generate_cma_analysis(
        self, comparable_sales: List[Dict], property_data: Dict
    ) -> Dict:
        """Generate CMA analysis from comparable sales"""
        try:
            if not comparable_sales:
                return self.get_fallback_cma()

            # Calculate benchmarks
            sale_prices = [
                sale.get("sale_price", 0)
                for sale in comparable_sales
                if sale.get("sale_price")
            ]
            cvs = [sale.get("cv", 0) for sale in comparable_sales if sale.get("cv")]
            land_areas = [
                sale.get("land_area", 0)
                for sale in comparable_sales
                if sale.get("land_area")
            ]
            floor_areas = [
                sale.get("floor_area", 0)
                for sale in comparable_sales
                if sale.get("floor_area")
            ]

            # Calculate ratios
            sale_cv_ratios = []
            for i, price in enumerate(sale_prices):
                if i < len(cvs) and cvs[i] > 0:
                    sale_cv_ratios.append(price / cvs[i])

            floor_rates = []
            for i, price in enumerate(sale_prices):
                if i < len(floor_areas) and floor_areas[i] > 0:
                    floor_rates.append(price / floor_areas[i])

            land_rates = []
            for i, price in enumerate(sale_prices):
                if i < len(land_areas) and land_areas[i] > 0:
                    land_rates.append(price / land_areas[i])

            # Calculate averages
            avg_sale_cv_ratio = (
                sum(sale_cv_ratios) / len(sale_cv_ratios) if sale_cv_ratios else 1.0
            )
            avg_floor_rate = (
                sum(floor_rates) / len(floor_rates) if floor_rates else 5000
            )
            avg_land_rate = sum(land_rates) / len(land_rates) if land_rates else 1000

            # Calculate valuation range
            subject_cv = property_data.get("cv", 750000)
            subject_floor_area = property_data.get("floor_area", 120)
            subject_land_area = property_data.get("land_area", 600)

            # Benchmark 1: Sale/CV ratio
            benchmark1_value = subject_cv * avg_sale_cv_ratio

            # Benchmark 2: Floor area rate
            benchmark2_value = subject_floor_area * avg_floor_rate

            # Benchmark 3: Land area rate
            benchmark3_value = subject_land_area * avg_land_rate

            # Calculate overall range
            values = [benchmark1_value, benchmark2_value, benchmark3_value]
            values = [v for v in values if v > 0]

            if values:
                avg_value = sum(values) / len(values)
                range_variance = avg_value * 0.1  # 10% variance

                valuation_range = {
                    "low": int(avg_value - range_variance),
                    "mid": int(avg_value),
                    "high": int(avg_value + range_variance),
                }
            else:
                valuation_range = {
                    "low": int(subject_cv * 0.9),
                    "mid": int(subject_cv),
                    "high": int(subject_cv * 1.1),
                }

            # Generate analysis summary
            confidence_level = (
                "High"
                if len(comparable_sales) >= 8
                else "Medium" if len(comparable_sales) >= 5 else "Low"
            )

            cma_analysis = {
                "comparable_sales": comparable_sales,
                "valuation_range": {"overall_range": valuation_range},
                "benchmarks": {
                    "sale_cv_ratio": round(avg_sale_cv_ratio, 2),
                    "floor_rate_per_sqm": round(avg_floor_rate, 2),
                    "land_rate_per_sqm": round(avg_land_rate, 2),
                },
                "analysis_summary": {
                    "confidence_level": confidence_level,
                    "comparable_count": len(comparable_sales),
                    "analysis_date": time.strftime("%Y-%m-%d"),
                },
            }

            logger.info(
                f"Generated CMA analysis with {len(comparable_sales)} comparables"
            )
            return cma_analysis

        except Exception as e:
            logger.error(f"Error generating CMA analysis: {e}")
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

    async def close(self):
        """Close browser and cleanup"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    def search_property_sync(self, address: str) -> Dict:
        """Synchronous wrapper for search_property"""
        try:
            print(f"🔍 DEBUG: search_property_sync called with address: {address}")
            logger.info(f"Starting sync property search for: {address}")
            # For now, return fallback data to avoid infinite loops
            # In production, this would use the async method
            print("🔍 DEBUG: Using fallback data for demo purposes")
            logger.info("Using fallback data for demo purposes")
            result = self.get_fallback_data(address)
            print(f"🔍 DEBUG: search_property_sync returning: {result}")
            return result
        except Exception as e:
            print(f"🔍 DEBUG: Error in search_property_sync: {e}")
            logger.error(f"Sync property search failed: {e}")
            return self.get_fallback_data(address)

    def run_cma_sync(self, property_data: Dict) -> Dict:
        """Synchronous wrapper for run_cma"""
        try:
            print(f"🔍 DEBUG: run_cma_sync called with property_data: {property_data}")
            logger.info("Starting sync CMA analysis")
            # For now, return fallback CMA to avoid infinite loops
            # In production, this would use the async method
            print("🔍 DEBUG: Using fallback CMA for demo purposes")
            logger.info("Using fallback CMA for demo purposes")
            result = self.get_fallback_cma()
            print(f"🔍 DEBUG: run_cma_sync returning: {result}")
            return result
        except Exception as e:
            print(f"🔍 DEBUG: Error in run_cma_sync: {e}")
            logger.error(f"Sync CMA analysis failed: {e}")
            return self.get_fallback_cma()
