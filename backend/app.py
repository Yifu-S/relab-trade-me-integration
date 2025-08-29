# app.py (Consolidated Phase II Code)
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import logging
import os
import json
import re
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import random
from datetime import datetime, timezone, timedelta
import math

# --- Load environment variables ---
load_dotenv()

# --- Configuration ---
RELAB_EMAIL = os.environ.get("RELAB_EMAIL")
RELAB_PASSWORD = os.environ.get("RELAB_PASSWORD")
PORT = 5000
# --- End Configuration ---

app = Flask(__name__)
CORS(app)  # Allow all origins for development

# In-memory storage for demo
watchlist_db = []

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Helper Functions for CMA ---
def calculate_filter_bounds(subject_value, tolerance_percent, is_integer=False):
    """Calculates min/max filter bounds based on subject value and tolerance."""
    if subject_value is None or subject_value == "":
        return None, None
    try:
        val = float(subject_value)
        if val <= 0:
            return None, None
        tolerance_factor = tolerance_percent / 100.0
        lower_bound = val * (1 - tolerance_factor)
        upper_bound = val * (1 + tolerance_factor)
        if is_integer:
            lower_bound = math.floor(lower_bound)
            upper_bound = math.ceil(upper_bound)
        return lower_bound, upper_bound
    except (ValueError, TypeError):
        return None, None


def find_closest_boundary_option(bound_value, boundary_options, is_upper_bound=False):
    """
    Finds the closest available boundary option from a list for a given calculated bound.

    Args:
        bound_value (float): The calculated boundary value (e.g., 170.0 from 200 * 0.85).
        boundary_options (list): A list of available boundary values (floats) from the dropdown.
                                  This list should be sorted in ascending order.
                                  Example: [50.0, 75.0, 100.0, 125.0, ..., 500.0] (representing m² options)
        is_upper_bound (bool): If True, finds the smallest option >= bound_value (for max filters).
                               If False, finds the largest option <= bound_value (for min filters).

    Returns:
        float or None: The closest matching boundary value from the list, or None if no suitable option is found.
    """
    if not boundary_options:
        return None

    if is_upper_bound:
        # For upper bound (e.g., max area), find the smallest option that is >= bound_value
        # or the largest available option if bound_value is higher than all.
        for option in boundary_options:
            if option >= bound_value:
                return option
        # If bound_value is higher than all options, return the highest available option
        return boundary_options[-1] if boundary_options else None
    else:
        # For lower bound (e.g., min area), find the largest option that is <= bound_value
        # or the smallest available option if bound_value is lower than all.
        # Iterate backwards through the sorted list.
        for option in reversed(boundary_options):
            if option <= bound_value:
                return option
        # If bound_value is lower than all options, return 0
        return -1 if boundary_options else None


def parse_year_built(year_text):
    """Parses the 'Year Built' text (e.g., '2020 s') to extract the integer year."""
    if year_text:
        match = re.search(r"(\d+)", year_text)
        if match:
            return int(match.group())
    return -1


def parse_bed_bath(text):
    """Parses Bedroom/Bathroom text (e.g., '4') to extract the integer."""
    if text:
        match = re.search(r"(\d+)", text)
        if match:
            return int(match.group())
    return -1


def parse_area(text: str) -> int:
    """
    Parse land area string into square meters (int).
    Handles '123 m2' or '1.234 ha'.
    Returns int (m²).
    """
    if not text:
        return -1

    match = re.search(r"[\d.,]+", text)
    if not match:
        return -1

    value = float(match.group(0).replace(",", ""))  # convert "1.234" → 1.234

    text_lower = text.lower()
    if "ha" in text_lower:
        return int(round(value * 10000))  # hectares → m²
    elif "m2" in text_lower or "m²" in text_lower:
        return int(round(value))  # already m²
    else:
        return int(round(value))  # fallback


def parse_land_title(text: str) -> str:
    """
    Extract the land title text before the first number.
    e.g. "Freehold 123 m2" -> "Freehold"
         "A V C 1.234 ha" -> "A V C"
    """
    if not text:
        return ""

    match = re.match(r"^(.*?)\s*[\d.,]+", text.strip())
    if match:
        return match.group(1).strip()
    return ""

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


async def select_from_dropdown(page, dropdown_locator, option_text: str):
    """
    Opens a dropdown and selects the option with the given text.

    Args:
        page: Playwright page instance
        dropdown_locator: CSS locator for the dropdown trigger element
        option_text: Text of the option to select
    """
    # Click the dropdown to open it
    logger.info("inside select_from_dropdown")
    await dropdown_locator.click()
    logger.info("clicking dropdown")
    # Wait briefly for options to render
    await page.wait_for_timeout(500)
    logger.info(f"clicking text {option_text}")

    # Click the desired option
    menu = page.locator("div.v-menu__content.menuable__content__active").first
    option = menu.locator("div.v-list-item__title", has_text=option_text).first
    max_attempts = 3
    for _ in range(max_attempts):
        if await option.is_visible():
            await option.click()
            logger.info("clicked text")
            await page.wait_for_selector(
                "div.text-start.p-1.col.col-12",
                state="visible",
                timeout=10000,
            )  # CMA page selector
            return
        # scroll
        await menu.evaluate("(menu) => menu.scrollBy(0, 100)")
        await page.wait_for_timeout(200)  # small delay for UI update

    raise Exception(f"Option '{option_text}' not found after scrolling")

def normalize_number(val: str):
    """Convert '2.475M', '500k', '10,507', '9710' into a float"""
    val = val.replace(",", "").upper()
    if val.endswith("M"):
        return float(val[:-1]) * 1_000_000
    elif val.endswith("K"):
        return float(val[:-1]) * 1_000
    else:
        return float(val)


# --- End Helper Functions for CMA ---


# --- Playwright Logic ---
async def login_to_relab(page):
    """Logs into Relab using specific selectors and anti-bot measures."""
    logger.info("Navigating to Relab login page...")
    await page.goto("https://relab.co.nz/login")

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting to login (Attempt {attempt}/{max_retries})...")

            # Wait for username input
            await page.wait_for_selector("input[name='input-username']", timeout=10000)
            logger.info("Found username box")
            # Add a random delay before interaction
            await page.wait_for_timeout(random.uniform(1000, 2000))

            # Fill credentials
            await page.fill("input[name='input-username']", RELAB_EMAIL)
            await page.wait_for_timeout(random.uniform(500, 1000))
            await page.fill("input[name='input-password']", RELAB_PASSWORD)
            logger.info("Filled credentials")
            # Add a random delay before click
            await page.wait_for_timeout(random.uniform(500, 1500))

            # Click login button
            logger.info("Locating login button")
            login_button = page.locator("button.login-btn")
            if await login_button.count() > 0:
                logger.info("Found it. Clicking")
                await login_button.hover()
                await page.wait_for_timeout(300)
                await login_button.click()
            else:
                raise Exception("Login button with class 'login-btn' not found.")

            # Wait for successful redirect
            logger.info("Waiting for login to complete and redirect to dashboard...")
            await page.wait_for_url("https://relab.co.nz/", timeout=10000)
            logger.info("Successfully logged into Relab.")
            return  # Exit the function on success

        except Exception as e:
            logger.warning(f"Login attempt {attempt} failed: {e}")
            if attempt < max_retries:
                logger.info("Retrying login...")
                # Wait a bit before retrying
                await page.wait_for_timeout(2000)
                # Navigate back to login page for the next attempt
                await page.goto("https://relab.co.nz/login")
            else:
                logger.error("Maximum login attempts reached.")
                raise Exception(f"Login failed after {max_retries} attempts.") from e


async def search_and_select_property_in_relab(page, address):
    """Searches for a property in Relab and selects the first matching suggestion."""
    logger.info(f"Searching for property: {address}")

    # Locate the search input field
    logger.info(f"Locating search input field")
    search_input_selector = (
        "input[id^='input-']"  # Note: ID may vary, but this is the pattern
    )
    await page.wait_for_selector(search_input_selector, timeout=10000)
    logger.info(f"Found search box")
    # Anti-Bot Measure: Random delay
    await page.wait_for_timeout(random.uniform(500, 1000))
    await page.fill(search_input_selector, address)

    # Wait for suggestions to appear
    suggestion_selector = "div.v-list-item__title"
    logger.info("Waiting for search suggestions...")
    try:
        await page.wait_for_selector(
            suggestion_selector, state="visible", timeout=10000
        )
        logger.info("Search suggestions appeared.")
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for search suggestions.")
        pass

    # Anti-Bot Measure: Delay after suggestions load
    await page.wait_for_timeout(random.uniform(500, 1500))

    # Extract the part of the Trade Me address to match against (e.g., before the first comma)
    tm_address_part = address.split(",")[0].strip().lower()
    logger.info(f"Looking for suggestion matching: '{tm_address_part}'")

    suggestion_titles = await page.locator(suggestion_selector).all()
    selected = False
    for i, title_element in enumerate(suggestion_titles):
        try:
            suggestion_text = await title_element.text_content()
            suggestion_text_clean = (
                suggestion_text.strip().lower() if suggestion_text else ""
            )
            logger.debug(f"Checking suggestion {i+1}: '{suggestion_text_clean}'")

            if tm_address_part in suggestion_text_clean:
                logger.info(
                    f"Found matching suggestion: '{suggestion_text_clean}'. Clicking..."
                )
                parent_item = title_element.locator("xpath=..")
                await parent_item.click()
                selected = True
                break
            else:
                logger.debug(f"Suggestion {i+1} does not match.")
        except Exception as e:
            logger.warning(f"Error processing suggestion {i+1}: {e}")
            continue

    if not selected:
        error_msg = f"No matching suggestion found for address part '{tm_address_part}' on Relab."
        logger.error(error_msg)
        raise Exception(error_msg)

    # Wait for the property listing page to load
    logger.info(
        "Waiting for property listing page to load (div with class containing 'container')..."
    )
    try:
        # Wait for the FIRST div with a class that contains 'container' to be attached to the DOM
        container_locator = page.locator("div[class*='container']").first
        await container_locator.wait_for(state="attached", timeout=20000)
        logger.info(
            "Property listing page loaded (first div[class*='container'] is attached to the DOM)."
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Timeout waiting for the first 'div[class*='container']' to be attached. The page might still be loading or the structure is different. Proceeding."
        )
    except Exception as e:
        logger.error(f"An error occurred while waiting for the container div: {e}")

    # Anti-Bot Measure: Delay after page load
    await page.wait_for_timeout(random.uniform(1000, 2000))


def extract_number(text):
    if text:
        m = re.search(r"\d+", text)
        return m.group(0) if m else None
    return None


async def extract_relab_property_data(page):
    """Extracts specific property data points from the Relab listing page."""
    logger.info("Extracting specific property data from Relab listing...")
    data = {
        "Land Title & Land Area": None,
        "Floor Area": None,
        "Bedroom(s)": None,
        "Year Built": None,
        "Bathroom(s)": None,
        "Relab Link": None,
    }

    # Anti-Bot Measure: Delay before starting extraction
    await page.wait_for_timeout(random.uniform(500, 1500))

    # --- Extract Land Title and Land Area (Robust & Specific - Corrected for Relab HTML) ---
    try:
        # Get the text content from the span after "Land Title"
        land_title_text = await page.text_content(
            "xpath=//div[normalize-space(text())='Land Title']/following-sibling::div/span"
        )

        logger.info(
            f"Found Land Title and Land Area '{land_title_text}'"
        )  # "Freehold 284 m²"

        # Split into Freehold and number
        data["Land Title & Land Area"] = land_title_text

    except Exception as e:
        logger.error(f"Error extracting Land Title and Land Area: {e}")
        if "Land Title" not in data:
            data["Land Title"] = "Error"
        if "Land Area" not in data:
            data["Land Area"] = "Error"

    # --- Extract Floor Area (Robust - Corrected for Relab HTML) ---
    try:
        # Find the specific div containing exactly "Floor Area"
        floor_area_text = await page.text_content(
            "xpath=//div[normalize-space(text())='Floor area']/following-sibling::div/span"
        )

        logger.info(f"Found Floor Area '{floor_area_text}'")  # "Floor Area 123 m²"

        data["Floor Area"] = extract_number(floor_area_text) + " m²"

    except Exception as e:
        logger.error(f"Error extracting Floor Area: {e}")

    # --- Extract Bedroom(s) (Robust - Corrected for Relab HTML) ---
    try:
        # Find the specific div containing exactly "Bedroom(s)"
        bedrooms_text = await page.text_content(
            "xpath=//div[normalize-space(text())='Bedroom(s)']/following-sibling::div/span"
        )

        logger.info(f"Found Bedroom(s) '{bedrooms_text}'")  # "4"

        data["Bedroom(s)"] = extract_number(bedrooms_text)

    except Exception as e:
        logger.error(f"Error extracting Bedroom(s): {e}")

    # --- Extract Year Built (Robust - Corrected for Relab HTML) ---
    try:
        # Find the specific div containing exactly "Year Built"
        year_built_text = await page.text_content(
            "xpath=//div[normalize-space(text())='Year built']/following-sibling::div/span"
        )

        logger.info(f"Found Year Built '{year_built_text}'")  # "2020 s"

        data["Year Built"] = extract_number(year_built_text) + " s"

    except Exception as e:
        logger.error(f"Error extracting Year Built: {e}")

    # --- Extract Bathroom(s) (Robust - Corrected for Relab HTML) ---
    try:
        # Find the specific div containing exactly "Bathroom(s)"
        bathrooms_text = await page.text_content(
            "xpath=//div[normalize-space(text())='Bathroom(s)']/following-sibling::div/span"
        )

        logger.info(f"Found Bathroom(s) '{bathrooms_text}'")  # "2"

        data["Bathroom(s)"] = extract_number(bathrooms_text)

    except Exception as e:
        logger.error(f"Error extracting Bathroom(s): {e}")

    # --- Extract Relab Link (Robust - Corrected for Relab HTML) ---
    try:
        data["Relab Link"] = page.url

    except Exception as e:
        logger.error(f"Error extracting Relab Link: {e}")

    return data


# --- Core CMA Analysis Function ---
async def perform_cma_analysis(page, subject_property_data):
    """
    Performs the Comparative Market Analysis by finding comparable sales
    and calculating benchmarks.
    """
    cma_data = {
        "CMA_Status": "Not Started",
        "CMA_Comparable_Count": 0,
        "CMA_Benchmark_1_Avg_Sale_CV_Ratio": None,
        "CMA_Benchmark_1_Estimated_Sale": "N/A",
        "CMA_Benchmark_2_Avg_Floor_$PerSqm": None,
        "CMA_Benchmark_2_Estimated_Value_via_Floor": "N/A",
        "CMA_Benchmark_3_Avg_Land_$PerSqm": None,
        "CMA_Benchmark_3_Estimated_Value_via_Land": "N/A",
        "CMA_Filter_Settings_Used": {},
        "CMA_Iterations_Performed": 0,
    }

    try:
        # --- 1. Navigate to CMA Section ---
        logger.info("Looking for and clicking the CMA button...")
        # Adjust the selector if the CMA button has a different text or class
        cma_button = page.locator("button:has-text('Nearby Sales')")
        if await cma_button.count() > 0:
            await cma_button.click()
            logger.info("Clicked CMA button. Waiting for CMA page to load...")
            # Wait for a key element on the CMA page to load
            # This might be the filter section or the results table header
            await page.wait_for_timeout(random.uniform(3000, 5000))
            await page.wait_for_selector(
                "div.text-start.p-1.col.col-12",
                state="visible",
                timeout=10000,
            )  # CMA page selector
            logger.info("CMA subpage loaded.")
        else:
            logger.warning("CMA button ('Run CMA') not found on the property page.")
            cma_data["CMA_Status"] = "Failed: CMA button not found"
            return cma_data

        logger.info("Locate the whole slider element")
        slider = page.locator("div.v-slider")

        logger.info("Get its bounding box")
        box = await slider.bounding_box()
        logger.info("Click near the right edge (a few pixels in to avoid missing)")
        x = box["x"] + box["width"] - 2
        y = box["y"] + box["height"] / 2

        await page.mouse.click(x, y)
        logger.info("done")
        await page.wait_for_selector(
            "div.text-start.p-1.col.col-12",
            state="visible",
        )

        logger.info("Locating expand tab")
        expand_button = page.locator("div.cursor-pointer:has(span:text('Expand'))")
        logger.info("Found expand tab")
        await page.wait_for_timeout(random.uniform(1000, 2000))
        if await expand_button.count() > 0:
            await expand_button.click()
            logger.info("Clicked Expand button. Waiting for Expand page to load...")
            # Wait for a key element on the CMA page to load
            # This might be the filter section or the results table header
            await page.wait_for_timeout(random.uniform(3000, 5000))
            await page.wait_for_selector(
                "div:has(span.form-label:has-text('Land title')) div.v-select__selection:has-text('Any')",
                state="visible",
                timeout=10000,
            )  # CMA page selector
            logger.info("Expand subpage loaded.")
        else:
            logger.warning("Expand button ('Expand') not found on the property page.")
            cma_data["CMA_Status"] = "Failed: Expand button not found"
            return cma_data
        # --- 2. Get Subject Property Attributes for Filtering ---
        logger.info("Preparing filter criteria based on subject property data...")
        subject_land_title_area_raw = subject_property_data.get(
            "Land Title & Land Area"
        )
        subject_floor_area_raw = subject_property_data.get("Floor Area")
        subject_bedrooms_raw = subject_property_data.get("Bedroom(s)")
        subject_bathrooms_raw = subject_property_data.get("Bathroom(s)")
        subject_year_built_raw = subject_property_data.get("Year Built")

        subject_land_title = parse_land_title(subject_land_title_area_raw).strip()
        subject_land_area_sqm = parse_area(subject_land_title_area_raw)
        subject_floor_area_sqm = parse_area(subject_floor_area_raw)
        subject_bedrooms = parse_bed_bath(subject_bedrooms_raw)
        subject_bathrooms = parse_bed_bath(subject_bathrooms_raw)
        subject_year_built = parse_year_built(subject_year_built_raw)

        logger.debug(
            f"Parsed subject attrs: LT={parse_land_title}, LA={subject_land_area_sqm}, FA={subject_floor_area_sqm}, "
            f"Beds={subject_bedrooms}, Baths={subject_bathrooms}, Year={subject_year_built}"
        )

        # --- 3. Set Initial Filter Criteria ---
        initial_tolerance_percent = 20.0  # 20%
        tolerance_step_percent = 5.0  # 5% step for adjustment
        target_min_comps = 5
        target_max_comps = 15
        max_iterations = 5  # Prevent infinite loops
        iteration_count = 0

        # Initial bounds based on subject property and initial tolerance
        land_area_min, land_area_max = calculate_filter_bounds(
            subject_land_area_sqm, initial_tolerance_percent, is_integer=False
        )
        floor_area_min, floor_area_max = calculate_filter_bounds(
            subject_floor_area_sqm, initial_tolerance_percent, is_integer=False
        )
        bedrooms_min = subject_bedrooms - 1 if subject_bedrooms is not None else None
        bedrooms_max = subject_bedrooms + 1 if subject_bedrooms is not None else None
        bathrooms_min = subject_bathrooms - 1 if subject_bathrooms is not None else None
        bathrooms_max = subject_bathrooms + 1 if subject_bathrooms is not None else None
        year_built_min = (
            subject_year_built - 10 if subject_year_built is not None else None
        )
        year_built_max = (
            subject_year_built + 10 if subject_year_built is not None else None
        )

        prev_land_title = "All"
        prev_land_area_min = "Any"
        prev_land_area_max = "200ha+"
        prev_floor_area_min = "Any"
        prev_floor_area_max = "500m²+"
        prev_bedrooms_min = "Any"
        prev_bedrooms_max = "10+"
        prev_bathrooms_min = "Any"
        prev_bathrooms_max = "10+"
        prev_year_built_min = "1900"
        prev_year_built_max = "2020"
        prev_sale_date = "Last 6 months"

        logger.info(
            f"subject_land_title: {subject_land_title}, \
                subject_land_area_sqm: {subject_land_area_sqm}, land_area_min: {land_area_min}, land_area_max: {land_area_max},\
                subject_floor_area_sqm: {subject_floor_area_sqm}, floor_area_min: {floor_area_min}, floor_area_max: {floor_area_max}, \
                subject_bedrooms: {subject_bedrooms}, bedrooms_min: {bedrooms_min}, bedrooms_max: {bedrooms_max}, \
                subject_bathrooms: {subject_bathrooms}, bathrooms_min: {bathrooms_min}, bedrooms_max: {bathrooms_max}, \
                subject_year_built: {subject_year_built}, year_built_min: {year_built_min}, year_built_max: {year_built_max},"
        )

        # --- 4. Iterative Filtering Loop ---
        while iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"CMA Iteration {iteration_count}/{max_iterations}.")

            # --- Apply Filters ---
            logger.info("Applying filters...")

            # --- Example: Handling a Land Title Dropdown ---
            logger.info(f"Applying land title filters {prev_land_title}...")
            # 1. Locate the dropdown element
            land_title_dropdown = page.locator(
                f"div:has(span.form-label:has-text('Land title')) div.v-select__selection:has-text('{prev_land_title}')"
            ).first

            if await land_title_dropdown.count() > 0:
                logger.info("Found land title dropdown...")
                try:
                    await select_from_dropdown(
                        page, land_title_dropdown, subject_land_title
                    )
                    logger.info("Clicked land title dropdown...")
                    await page.wait_for_timeout(
                        1000
                    )  # Brief wait for options to appear

                    prev_land_title = subject_land_title
                    logger.info("Done")
                    # Clicking the option often closes the dropdown automatically

                except Exception as dropdown_error:
                    logger.error(
                        f"Error selecting Land Title '{subject_land_title}' from dropdown: {dropdown_error}"
                    )
            else:
                if not subject_land_title:
                    logger.info("No Land Title to filter by.")
                else:
                    logger.warning("Land Title dropdown element not found on page.")

            await page.wait_for_timeout(
                1000
            )

            await page.wait_for_selector(
                "div.text-start.p-1.col.col-12",
                state="visible",
                timeout=10000,
            )

            # --- Handling Floor Area Min/Max Dropdowns ---
            logger.info("Applying floor area filters...")

            # Define the available boundary options for Floor Area (from inspection)
            # MAKE SURE THIS LIST MATCHES THE ACTUAL OPTIONS IN THE RELAB DROPDOWN
            # AND IS SORTED ASCENDINGLY
            floor_area_options = [
                50, 75, 100, 125, 150, 175, 200, 250, 300, 400, 500,
            ]

            if floor_area_min is not None and floor_area_max is not None:
                try:
                    logger.info("Finding floor area boundaries...")
                    # --- Select Floor Area Min ---
                    # Find the closest available *lower* boundary for the *minimum*
                    closest_floor_area_min_option = find_closest_boundary_option(
                        floor_area_min, floor_area_options, is_upper_bound=False
                    )
                    logger.info(f"Closest floor area boundaries option: {closest_floor_area_min_option} for {floor_area_min}")

                    floor_area_dropdown = page.locator(
                        f"label:text('Floor area') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_floor_area_min}']"
                    )

                    logger.info(f"Floor area dropdown found")

                    if await floor_area_dropdown.count() > 0:
                        logger.info("Found floor area dropdown...")
                        try:
                            await select_from_dropdown(
                                page, floor_area_dropdown, str(closest_floor_area_min_option)
                            )
                            logger.info("Clicked floor area min dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            prev_floor_area_min = closest_floor_area_min_option
                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting Floor area '{subject_floor_area_sqm}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_floor_area_sqm:
                            logger.info("No Floor area to filter by.")
                        else:
                            logger.warning("Floor area dropdown element not found on page.")
                    await page.wait_for_timeout(2000)
                    # --- Select Floor Area Max ---
                    # Find the closest available *lower* boundary for the *maximum*
                    closest_floor_area_max_option = find_closest_boundary_option(
                        floor_area_max, floor_area_options, is_upper_bound=True
                    )
                    logger.info(
                        f"Closest floor area boundaries option: {closest_floor_area_max_option} for {floor_area_max}")

                    floor_area_dropdown = page.locator(
                        f"label:text('Floor area') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_floor_area_max}']"
                    )

                    logger.info(f"Floor area dropdown found")

                    if await floor_area_dropdown.count() > 0:
                        logger.info("Found floor area dropdown...")
                        try:
                            await select_from_dropdown(
                                page, floor_area_dropdown, str(closest_floor_area_max_option)
                            )
                            logger.info("Clicked floor area max dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            prev_floor_area_max = closest_floor_area_max_option
                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting Floor area '{subject_floor_area_sqm}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_floor_area_sqm:
                            logger.info("No Floor area to filter by.")
                        else:
                            logger.warning("Floor area dropdown element not found on page.")
                    await page.wait_for_timeout(1000)

                except Exception as fa_error:
                    logger.error(f"Error setting Floor Area filters: {fa_error}")

            # --- Handling Bedroom Min/Max Dropdowns ---
            logger.info("Applying bedroom filters...")

            # Define the available boundary options for Floor Area (from inspection)
            # MAKE SURE THIS LIST MATCHES THE ACTUAL OPTIONS IN THE RELAB DROPDOWN
            # AND IS SORTED ASCENDINGLY
            bedroom_options = [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ]

            if bedrooms_min is not None and bedrooms_max is not None:
                try:
                    logger.info("Finding bedroom boundaries...")
                    # --- Select bedroom Min ---
                    # Find the closest available *lower* boundary for the *minimum*
                    closest_bedroom_min_option = find_closest_boundary_option(
                        bedrooms_min, bedroom_options, is_upper_bound=False
                    )
                    logger.info(
                        f"Closest bedroom boundaries option: {closest_bedroom_min_option} for {bedrooms_min}")

                    bedroom_dropdown = page.locator(
                        f"label:text('Bedrooms') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_bedrooms_min}']"
                    )

                    logger.info(f"Bedroom dropdown found")

                    if await bedroom_dropdown.count() > 0:
                        logger.info("Found bedroom dropdown...")
                        try:
                            await select_from_dropdown(
                                page, bedroom_dropdown, str(closest_bedroom_min_option)
                            )
                            logger.info("Clicked bedroom min dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            prev_bedrooms_min = closest_bedroom_min_option
                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting bedroom '{subject_bedrooms}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_bedrooms:
                            logger.info("No bedroom to filter by.")
                        else:
                            logger.warning("Bedroom dropdown element not found on page.")
                    await page.wait_for_timeout(2000)
                    # --- Select bedroom max ---
                    # Find the closest available *lower* boundary for the *maximum*
                    closest_bedroom_max_option = find_closest_boundary_option(
                        bedrooms_max, bedroom_options, is_upper_bound=True
                    )
                    logger.info(
                        f"Closest bedroom boundaries option: {closest_bedroom_max_option} for {bedrooms_max}")

                    bedroom_dropdown = page.locator(
                        f"label:text('Bedrooms') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_bedrooms_max}']"
                    )

                    logger.info(f"Bedroom dropdown found")

                    if await bedroom_dropdown.count() > 0:
                        logger.info("Found bedroom dropdown...")
                        try:
                            await select_from_dropdown(
                                page, bedroom_dropdown, str(closest_bedroom_max_option)
                            )
                            logger.info("Clicked bedroom max dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            prev_bedrooms_max = closest_bedroom_max_option
                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting bedroom '{subject_bedrooms}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_bedrooms:
                            logger.info("No bedroom to filter by.")
                        else:
                            logger.warning("Bedroom dropdown element not found on page.")
                    await page.wait_for_timeout(2000)

                except Exception as fa_error:
                    logger.error(f"Error setting bedroom filters: {fa_error}")

            # --- Handling bathroom Min/Max Dropdowns ---
            logger.info("Applying bathroom filters...")

            # Define the available boundary options for Floor Area (from inspection)
            # MAKE SURE THIS LIST MATCHES THE ACTUAL OPTIONS IN THE RELAB DROPDOWN
            # AND IS SORTED ASCENDINGLY
            bathroom_options = [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ]

            if bathrooms_min is not None and bathrooms_max is not None:
                try:
                    logger.info("Finding bathroom boundaries...")
                    # --- Select bathroom Min ---
                    # Find the closest available *lower* boundary for the *minimum*
                    closest_bathroom_min_option = find_closest_boundary_option(
                        bathrooms_min, bathroom_options, is_upper_bound=False
                    )
                    logger.info(
                        f"Closest bathroom boundaries option: {closest_bathroom_min_option} for {bathrooms_min}")

                    bathroom_dropdown = page.locator(
                        f"label:text('bathrooms') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_bathrooms_min}']"
                    )

                    logger.info(f"bathroom dropdown found")

                    if await bathroom_dropdown.count() > 0:
                        logger.info("Found bathroom dropdown...")
                        try:
                            await select_from_dropdown(
                                page, bathroom_dropdown, str(closest_bathroom_min_option)
                            )
                            logger.info("Clicked bathroom min dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            prev_bathrooms_min = closest_bathroom_min_option
                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting bathroom '{subject_bathrooms}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_bathrooms:
                            logger.info("No bathroom to filter by.")
                        else:
                            logger.warning("bathroom dropdown element not found on page.")
                    await page.wait_for_timeout(2000)
                    # --- Select bathroom max ---
                    # Find the closest available *lower* boundary for the *maximum*
                    closest_bathroom_max_option = find_closest_boundary_option(
                        bathrooms_max, bathroom_options, is_upper_bound=True
                    )
                    logger.info(
                        f"Closest bathroom boundaries option: {closest_bathroom_max_option} for {bathrooms_max}")

                    bathroom_dropdown = page.locator(
                        f"label:text('bathrooms') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_bathrooms_max}']"
                    )

                    logger.info(f"bathroom dropdown found")

                    if await bathroom_dropdown.count() > 0:
                        logger.info("Found bathroom dropdown...")
                        try:
                            await select_from_dropdown(
                                page, bathroom_dropdown, str(closest_bathroom_max_option)
                            )
                            logger.info("Clicked bathroom max dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            prev_bathrooms_max = closest_bathroom_max_option
                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting bathroom '{subject_bathrooms}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_bathrooms:
                            logger.info("No bathroom to filter by.")
                        else:
                            logger.warning("bathroom dropdown element not found on page.")
                    await page.wait_for_timeout(2000)

                except Exception as fa_error:
                    logger.error(f"Error setting bathroom filters: {fa_error}")


            # --- Handling year built Min/Max Dropdowns ---
            logger.info("Applying year built filters...")

            # Define the available boundary options for Floor Area (from inspection)
            # MAKE SURE THIS LIST MATCHES THE ACTUAL OPTIONS IN THE RELAB DROPDOWN
            # AND IS SORTED ASCENDINGLY
            year_built_options = [
                1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020,
            ]

            if year_built_min is not None and year_built_max is not None:
                try:
                    logger.info("Finding year built boundaries...")
                    # --- Select year built Min ---
                    # Find the closest available *lower* boundary for the *minimum*
                    closest_year_built_min_option = find_closest_boundary_option(
                        year_built_min, year_built_options, is_upper_bound=False
                    )
                    logger.info(
                        f"Closest year built boundaries option: {closest_year_built_min_option} for {year_built_min}")

                    year_built_dropdown = page.locator(
                        f"label:text('Build era') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_year_built_min}']"
                    )

                    logger.info(f"year built dropdown found")

                    if await year_built_dropdown.count() > 0:
                        logger.info("Found year built dropdown...")
                        try:
                            await select_from_dropdown(
                                page, year_built_dropdown, str(closest_year_built_min_option)
                            )
                            logger.info("Clicked year built min dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            prev_year_built_min = closest_year_built_min_option
                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting year built '{subject_year_built}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_year_built:
                            logger.info("No year built to filter by.")
                        else:
                            logger.warning("year built dropdown element not found on page.")
                    await page.wait_for_timeout(2000)
                    # --- Select year built max ---
                    # Find the closest available *lower* boundary for the *maximum*
                    closest_year_built_max_option = find_closest_boundary_option(
                        year_built_max, year_built_options, is_upper_bound=False
                    )
                    logger.info(
                        f"Closest year built boundaries option: {closest_year_built_max_option} for {year_built_max}")

                    year_built_dropdown = page.locator(
                        f"label:text('Build era') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_year_built_max}']"
                    )

                    logger.info(f"year built dropdown found")

                    if await year_built_dropdown.count() > 0:
                        logger.info("Found year built dropdown...")
                        try:
                            await select_from_dropdown(
                                page, year_built_dropdown, str(closest_year_built_max_option)
                            )
                            logger.info("Clicked year built max dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            prev_year_built_max = closest_year_built_max_option
                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting year built '{subject_year_built}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_year_built:
                            logger.info("No year built to filter by.")
                        else:
                            logger.warning("year built dropdown element not found on page.")
                    await page.wait_for_timeout(2000)

                except Exception as fa_error:
                    logger.error(f"Error setting bathroom filters: {fa_error}")

            # --- Handling land Area Min/Max Dropdowns ---
            logger.info("Applying land area filters...")

            # Define the available boundary options for land Area (from inspection)
            # MAKE SURE THIS LIST MATCHES THE ACTUAL OPTIONS IN THE RELAB DROPDOWN
            # AND IS SORTED ASCENDINGLY
            land_area_options = [
                50, 75, 100, 150, 200, 300, 400, 500, 750, 1000, 2000, 3000, 4000, 5000, 10000, 20000, 40000, 50000, 100000, 150000, 200000, 250000, 500000, 1000000, 1500000, 2000000,
            ]

            if land_area_min is not None and land_area_max is not None:
                try:
                    logger.info("Finding land area boundaries...")
                    # --- Select land Area Min ---
                    # Find the closest available *lower* boundary for the *minimum*
                    closest_land_area_min_option = find_closest_boundary_option(
                        land_area_min, land_area_options, is_upper_bound=False
                    )
                    # if greater than 10000, change to ha

                    logger.info(
                        f"Closest land area boundaries option: {closest_land_area_min_option} for {land_area_min}")

                    land_area_dropdown = page.locator(
                        f"label:text('land area') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_land_area_min}']"
                    )

                    logger.info(f"land area dropdown found")

                    if await land_area_dropdown.count() > 0:
                        logger.info("Found land area dropdown...")
                        try:
                            if closest_land_area_min_option >= 10000:
                                closest_land_area_min_option /= 10000
                                await select_from_dropdown(
                                    page, land_area_dropdown, str(closest_land_area_min_option)+"ha"
                                )
                                prev_land_area_min = closest_land_area_min_option * 10000
                            else:
                                await select_from_dropdown(
                                    page, land_area_dropdown, str(closest_land_area_min_option)
                                )
                                prev_land_area_min = closest_land_area_min_option
                            logger.info("Clicked land area min dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting land area '{subject_land_area_sqm}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_land_area_sqm:
                            logger.info("No land area to filter by.")
                        else:
                            logger.warning("land area dropdown element not found on page.")
                    await page.wait_for_timeout(2000)
                    # --- Select land Area Max ---
                    # Find the closest available *lower* boundary for the *maximum*
                    closest_land_area_max_option = find_closest_boundary_option(
                        land_area_max, land_area_options, is_upper_bound=True
                    )
                    logger.info(
                        f"Closest land area boundaries option: {closest_land_area_max_option} for {land_area_max}")

                    land_area_dropdown = page.locator(
                        f"label:text('Land area') >> xpath=following-sibling::div//div[contains(@class, 'v-select__selection') and text()='{prev_land_area_max}']"
                    )

                    logger.info(f"land area dropdown found")

                    if await land_area_dropdown.count() > 0:
                        logger.info("Found land area dropdown...")
                        try:
                            if closest_land_area_max_option >= 10000:
                                closest_land_area_max_option /= 10000
                                await select_from_dropdown(
                                    page, land_area_dropdown, str(closest_land_area_max_option) + "ha"
                                )
                                prev_land_area_max = closest_land_area_max_option * 10000
                            else:
                                await select_from_dropdown(
                                    page, land_area_dropdown, str(closest_land_area_max_option)
                                )
                                prev_land_area_max = closest_land_area_max_option
                            logger.info("Clicked land area max dropdown...")
                            await page.wait_for_timeout(
                                1000
                            )  # Brief wait for options to appear

                            logger.info("Done")
                            # Clicking the option often closes the dropdown automatically

                        except Exception as dropdown_error:
                            logger.error(
                                f"Error selecting land area '{subject_land_area_sqm}' from dropdown: {dropdown_error}"
                            )
                    else:
                        if not subject_land_area_sqm:
                            logger.info("No land area to filter by.")
                        else:
                            logger.warning("land area dropdown element not found on page.")
                    await page.wait_for_timeout(1000)

                except Exception as fa_error:
                    logger.error(f"Error setting land Area filters: {fa_error}")

            # --- Check Results Count ---
            result_count = 0
            try:
                # Adjust selector for the element displaying the number of results
                # It might be text like "Found 15 comparable sales" or just a number
                results_locator = page.locator("div.text-start span.font-weight-bold")
                results_text = await results_locator.text_content()
                logger.debug(f"Raw results text: '{results_text}'")
                # Extract number using regex
                count_match = re.search(r"(\d+)", results_text)
                if count_match:
                    result_count = int(count_match.group(0))
                logger.info(
                    f"Iteration {iteration_count}: Found {result_count} comparable sales."
                )
            except Exception as e:
                logger.warning(
                    f"Could not determine result count: {e}. Assuming results are displayed."
                )
                # If we can't get the count easily, proceed to try extracting data
                # and determine count from the list of extracted comparable.

            # --- Evaluate Result Count and Adjust Filters ---
            if target_min_comps <= result_count <= target_max_comps:
                logger.info(
                    f"Iteration {iteration_count}: Target number of comparable ({result_count}) achieved."
                )
                cma_data["CMA_Status"] = f"Success: Found {result_count} comparable"
                break  # Success, exit loop
            elif result_count < target_min_comps:
                logger.info(
                    f"Iteration {iteration_count}: Too few comparable ({result_count}). Loosening filters."
                )
                # Loosen filters: Increase tolerance
                initial_tolerance_percent += tolerance_step_percent
                land_area_min, land_area_max = calculate_filter_bounds(
                    subject_land_area_sqm, initial_tolerance_percent, is_integer=False
                )
                floor_area_min, floor_area_max = calculate_filter_bounds(
                    subject_floor_area_sqm, initial_tolerance_percent, is_integer=False
                )
                # Widen bed/bath ranges slightly if needed (they are integers, so logic might differ)
                # bedrooms_min = max(0, (bedrooms_min or subject_bedrooms) - 1) if subject_bedrooms is not None else None
                # bedrooms_max = (bedrooms_max or subject_bedrooms) + 1 if subject_bedrooms is not None else None
                # Adjust year range if needed
                # build_year_min = (build_year_min or subject_year_built) - 10 if subject_year_built is not None else None
                # build_year_max = (build_year_max or subject_year_built) + 10 if subject_year_built is not None else None

            elif result_count > target_max_comps:
                logger.info(
                    f"Iteration {iteration_count}: Too many comparable ({result_count}). Tightening filters."
                )
                # Tighten filters: Decrease tolerance
                initial_tolerance_percent = max(
                    5.0, initial_tolerance_percent - tolerance_step_percent
                )  # Min 5%
                land_area_min, land_area_max = calculate_filter_bounds(
                    subject_land_area_sqm, initial_tolerance_percent, is_integer=False
                )
                floor_area_min, floor_area_max = calculate_filter_bounds(
                    subject_floor_area_sqm, initial_tolerance_percent, is_integer=False
                )
                # Narrow bed/bath ranges slightly if needed
                # Adjust year range if needed

            # Add a small delay before the next iteration
            await page.wait_for_timeout(2000)

        # --- End Iterative Filtering Loop ---

        if iteration_count >= max_iterations:
            logger.warning(
                f"Max iterations ({max_iterations}) reached. Final count: {result_count}. Proceeding with available comps."
            )
            cma_data["CMA_Status"] = (
                f"Partial Success: Max iterations reached, final count {result_count}"
            )

        # --- 5. Extract Comparable Sales Data ---
        properties = []
        Avg_Sale_CV = 0
        Avg_Land_Value = 0
        Avg_Floor_Value = 0
        cards = page.locator("div.row.pt-2 div.text-start.p-1.col.col-12")
        count = await cards.count()
        logger.info(f"Extracting data for {count} comparable properties...")
        for i in range(count):
            card = cards.nth(i)

            comparable_text = await card.text_content()

            logger.info(f"Index {i}: Found {comparable_text}")

            patterns = {
                "CV": r"CV:\$?([\d.,]+M?)",
                "Sale/CV": r"Sale/CV:([-\d%]+)",
                "Land": r"Land:\s*\$([\d,]+)",
                "Floor": r"Floor:\s*\$([\d,]+)",
            }

            results = {}
            for key, pat in patterns.items():
                match = re.search(pat, comparable_text)
                if match:
                    raw = match.group(1)
                    if key == "Sale/CV":
                        # percentage → decimal
                        results[key] = float(raw.strip("%")) / 100
                    else:
                        results[key] = normalize_number(raw)

            properties.append(results)

        logger.info(f"extracted entries: {properties}")

        input("pause")
        # --- 6. Calculate Benchmarks ---
        logger.info("Calculating CMA benchmarks based on extracted comparables...")
        cma_data["CMA_Comparable_Count"] = len(properties)
        cma_data["CMA_Comparable_Details"] = (
            properties  # Store detailed list
        )
        cma_data["CMA_Iterations_Performed"] = iteration_count
        cma_data["CMA_Filter_Settings_Used"] = {
            "Land Title": subject_land_title,
            "Land Area Min (m²)": land_area_min,
            "Land Area Max (m²)": land_area_max,
            "Floor Area Min (m²)": floor_area_min,
            "Floor Area Max (m²)": floor_area_max,
            "Bedrooms Min": bedrooms_min,
            "Bedrooms Max": bedrooms_max,
            "Bathrooms Min": bathrooms_min,
            "Bathrooms Max": bathrooms_max,
            "Year Built Min": year_built_min,
            "Year Built Max": year_built_max,
            "Sale Date Range": "Last 12 months (assumed)",
        }

        if not comparable_properties:
            logger.warning(
                "No comparable properties extracted for benchmark calculation."
            )
            cma_data["CMA_Status"] = (
                "Completed, but no comparables found for benchmarks."
            )
            return cma_data

        # Prepare lists for calculations
        ratios_sale_cv = []
        rates_floor_per_sqm = []
        rates_land_per_sqm = []

        for prop in comparable_properties:
            price = prop.get("price_nzd")
            cv = prop.get("cv_nzd")
            floor_area = prop.get("floor_area_sqm")
            land_area = prop.get("land_area_sqm")

            if price and cv and cv > 0:
                ratios_sale_cv.append(price / cv)
            if price and floor_area and floor_area > 0:
                rates_floor_per_sqm.append(price / floor_area)
            if price and land_area and land_area > 0:
                rates_land_per_sqm.append(price / land_area)

        # --- Benchmark 1: Avg Sale/CV Ratio ---
        if ratios_sale_cv:
            avg_ratio_sale_cv = sum(ratios_sale_cv) / len(ratios_sale_cv)
            subject_cv_raw = (
                subject_property_data.get("Capital Value", "")
                .replace("$", "")
                .replace(",", "")
            )
            subject_cv = float(subject_cv_raw) if subject_cv_raw.isdigit() else 0
            if subject_cv > 0:
                benchmark_1_valuation = avg_ratio_sale_cv * subject_cv
                cma_data["CMA_Benchmark_1_Avg_Sale_CV_Ratio"] = round(
                    avg_ratio_sale_cv, 4
                )
                cma_data["CMA_Benchmark_1_Valuation"] = f"${benchmark_1_valuation:,.0f}"

        # --- Benchmark 2: Avg Floor $/sqm ---
        if rates_floor_per_sqm:
            avg_rate_floor_per_sqm = sum(rates_floor_per_sqm) / len(rates_floor_per_sqm)
            if subject_floor_area_sqm and subject_floor_area_sqm > 0:
                benchmark_2_valuation = avg_rate_floor_per_sqm * subject_floor_area_sqm
                cma_data["CMA_Benchmark_2_Avg_Floor_$PerSqm"] = round(
                    avg_rate_floor_per_sqm, 2
                )
                cma_data["CMA_Benchmark_2_Valuation"] = f"${benchmark_2_valuation:,.0f}"

        # --- Benchmark 3: Avg Land $/sqm ---
        if rates_land_per_sqm:
            avg_rate_land_per_sqm = sum(rates_land_per_sqm) / len(rates_land_per_sqm)
            if subject_land_area_sqm and subject_land_area_sqm > 0:
                benchmark_3_valuation = avg_rate_land_per_sqm * subject_land_area_sqm
                cma_data["CMA_Benchmark_3_Avg_Land_$PerSqm"] = round(
                    avg_rate_land_per_sqm, 2
                )
                cma_data["CMA_Benchmark_3_Valuation"] = f"${benchmark_3_valuation:,.0f}"

        logger.info("CMA analysis completed successfully.")
        if (
            cma_data["CMA_Status"] == "Not Started"
        ):  # Only update if not already set (e.g., in success case)
            cma_data["CMA_Status"] = "Completed"

    except Exception as e:
        logger.error(
            f"Error during CMA analysis: {e}", exc_info=True
        )  # Log full traceback
        cma_data["CMA_Status"] = f"Failed: {str(e)}"
        # Optionally, save a debug HTML snapshot if CMA fails
        # try:
        #     failure_html_path = f"debug_cma_failure_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
        #     with open(failure_html_path, 'w', encoding='utf-8') as f:
        #         f.write(await page.content())
        #     logger.info(f"CMA failure HTML saved to {failure_html_path}")
        # except Exception as debug_e:
        #     logger.error(f"Failed to save CMA debug HTML: {debug_e}")

    return cma_data


# --- End Core CMA Analysis Function ---


# --- The main scraping task orchestrates these steps ---
async def run_playwright_task(address):
    """Main Playwright task to login, search, select, and extract data."""
    logger.info(f"Starting Playwright task for address: {address}")
    async with async_playwright() as p:
        user_data_dir = r"C:\Users\admin\Desktop\BeeBee AI\Relab\relab-trade-me-integration\playwright-profile"
        browser = await p.firefox.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            ignore_https_errors=True,
            extra_http_headers={
                "referer": "https://relab.co.nz/",
                "origin": "https://relab.co.nz",
                "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh-HK;q=0.7,zh-TW;q=0.6,zh;q=0.5",
            },
            locale="en-NZ",
            timezone_id="Pacific/Auckland",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        )
        page = await browser.new_page()

        try:
            await login_to_relab(page)
            await search_and_select_property_in_relab(page, address)
            property_data = await extract_relab_property_data(page)

            logger.info("Initiating CMA analysis...")
            cma_results = await perform_cma_analysis(page, property_data)
            property_data.update(cma_results)  # Add CMA results to the main data dict

            logger.info("Playwright task completed successfully.")
            return {"success": True, "data": property_data, "screenshots": []}
        except Exception as e:
            logger.error(f"Playwright task failed for {address}: {e}")
            try:
                failure_html_path = f"debug_relab_failure_{datetime.now(timezone(timedelta(hours=12)))
                .astimezone(timezone.utc)
                .strftime("%d/%m/%Y")}.html"
                with open(failure_html_path, "w", encoding="utf-8") as f:
                    f.write(await page.content())
                logger.info(f"Failure HTML saved to {failure_html_path}")
            except Exception as debug_e:
                logger.error(f"Failed to save debug HTML: {debug_e}")
            return {"success": False, "error": str(e)}
        finally:
            await page.close()
            await browser.close()


# --- Flask Routes ---
@app.route("/api/get_relab_data", methods=["POST"])
def get_relab_data():
    """API endpoint for the extension to request Relab data."""
    data = request.get_json()
    address = data.get("address")
    trademe_url = data.get("trademe_url")
    logger.info(f"Processing Relab data request for address: {address}")

    if not address:
        return jsonify({"success": False, "error": "Address is required"}), 400

    logger.info(
        f"Received request for Relab data: Address={address}, TM_URL={trademe_url}"
    )

    try:
        result = asyncio.run(run_playwright_task(address))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error running Playwright task: {e}")
        return (
            jsonify(
                {"success": False, "error": "Internal server error during scraping"}
            ),
            500,
        )


@app.route("/api/save_to_watchlist", methods=["POST"])
def save_to_watchlist():
    """API endpoint to save property data to the watchlist."""
    data = request.get_json()
    property_info = data.get("property_info")
    if not property_info:
        return jsonify({"success": False, "error": "Property info is required"}), 400

    watchlist_db.append(property_info)
    logger.info(
        f"Saved property to watchlist: {property_info.get('address', 'Unknown')}"
    )
    return jsonify({"success": True, "message": "Property saved to watchlist"})


@app.route("/api/watchlist", methods=["GET"])
def get_watchlist():
    """API endpoint to retrieve the watchlist."""
    return jsonify({"success": True, "data": watchlist_db})


@app.route("/")
def index():
    return "Relab Integration Backend Server is running."


if __name__ == "__main__":
    logger.info("Starting Flask server...")
    app.run(host="127.0.0.1", port=PORT, debug=True)
