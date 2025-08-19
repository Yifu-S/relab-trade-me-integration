# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import logging
from playwright.async_api import async_playwright
import os
import json
from datetime import datetime, timedelta, timezone
import re
import random # Import for random delays

# --- Configuration ---
RELAb_EMAIL = os.environ.get("RELAB_EMAIL", "your_email@example.com") # Use environment variables for credentials
RELAb_PASSWORD = os.environ.get("RELAB_PASSWORD", "your_password")
PORT = 5000
# --- End Configuration ---

app = Flask(__name__)
# Allow CORS for requests from the browser extension (adjust origin as needed)
#CORS(app, origins=["chrome-extension://kfgnnoilgkhdagnamnlhpdnkncmcmgkp", "http://localhost:*"])
CORS(app)

# In-memory storage for demo (use a real DB in production)
watchlist_db = []

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Updated Playwright Logic ---
async def login_to_relab(page):
    """Logs into Relab using specific selectors and anti-bot measures."""
    logger.info("Navigating to Relab login page...")
    await page.goto("https://relab.co.nz/login")
    
    # Wait for the username input to be present
    await page.wait_for_selector("input[name='input-username']", timeout=10000)
    
    # --- Anti-Bot Measure: Random delay before interaction ---
    await page.wait_for_timeout(random.uniform(1000, 2000)) # 1-2 seconds

    # Fill credentials
    await page.fill("input[name='input-username']", RELAb_EMAIL)
    await page.fill("input[name='input-password']", RELAb_PASSWORD)
    
    # --- Anti-Bot Measure: Random delay before click ---
    await page.wait_for_timeout(random.uniform(500, 1500)) # 0.5-1.5 seconds

    # Click the login button using its class (more robust than full class string if it changes slightly)
    # Inside login_to_relab function in app.py

    # Maximum number of retries for the entire login process
    MAX_LOGIN_ATTEMPTS = 3
    attempt = 1

    while attempt <= MAX_LOGIN_ATTEMPTS:
        logger.info(f"Login attempt {attempt}/{MAX_LOGIN_ATTEMPTS}")

        # --- Perform Click (Place your robust click logic here) ---
        # Example using dispatchEvent as it seemed effective before:
        try:
            await page.evaluate("""() => {
                const button = document.querySelector("button.login-btn");
                if (button) {
                    console.log("JS Dispatch: Found login button, dispatching click event.");
                    button.dispatchEvent(new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    }));
                } else {
                    console.error("JS Dispatch: Login button not found for event dispatch.");
                }
            }""")
            logger.info(f"Login button click dispatched (Attempt {attempt}).")
        except Exception as click_error:
            logger.error(f"Error dispatching click (Attempt {attempt}): {click_error}")
            if attempt == MAX_LOGIN_ATTEMPTS:
                raise
            attempt += 1
            continue # Retry the click
        # --- End Perform Click ---

        # --- Wait and Check ---
        # Wait a few seconds to see if navigation starts
        wait_after_click = 10000 # 10 seconds
        logger.debug(f"Waiting {wait_after_click/1000}s to observe page state after click (Attempt {attempt})...")
        await page.wait_for_timeout(wait_after_click)

        current_url_after_wait = page.url
        logger.debug(f"Page URL after waiting (Attempt {attempt}): {current_url_after_wait}")

        # Check if we are still on the login page
        if current_url_after_wait.startswith("https://relab.co.nz/login"):
            logger.warning(f"Attempt {attempt}: Still on the login page after click and wait. This might indicate the click didn't trigger navigation or was blocked.")
            # --- Retry Logic ---
            if attempt < MAX_LOGIN_ATTEMPTS:
                logger.info("Retrying login click...")
                # Optional: Add a slightly longer delay between retries
                await page.wait_for_timeout(2000)
                attempt += 1
                continue # Go to the next iteration of the while loop to retry
            else:
                logger.error(f"Failed to log in after {MAX_LOGIN_ATTEMPTS} attempts. Stuck on the login page.")
                raise Exception("Login failed: Could not navigate away from the login page after multiple click attempts. The click action might not be triggering the expected behavior.")
        else:
            # If the URL has changed, it means navigation likely started.
            # Proceed to the standard "wait for success or error" logic.
            logger.info(f"Attempt {attempt}: Page URL changed, navigation seems to have started.")
            break # Exit the retry loop, login process is underway
        # --- End Wait and Check ---

    # --- Wait for the login process to start and show a loading state ---
    try:
        logger.info("Waiting briefly for login process to initiate (e.g., loading icon)...")
        await page.wait_for_timeout(2000) # 2 seconds
    except asyncio.TimeoutError:
        logger.info("No explicit loading indicator appeared or timed out waiting for it.")

    # --- Wait for the loading state to finish ---
    try:
        logger.info("Waiting for login process to complete (loading to disappear or redirect)...")
        # Define potential outcomes
        success_url = "https://relab.co.nz/"
        await page.wait_for_function(
            """
            (expectedUrl) => {
                // Check if URL matches success
                if (window.location.href === expectedUrl) {
                    return { type: 'success' };
                }
                // Check for common error indicators (add/modify selectors as needed)
                const errorElements = document.querySelectorAll('div.error-message, span.error-text, div.alert'); // Example selectors
                for (let el of errorElements) {
                    if (el.textContent && el.textContent.trim() !== '') {
                        return { type: 'error', message: el.textContent.trim() };
                    }
                }
                // If neither, keep waiting
                return null;
            }
            """,
            arg=success_url, # Pass the success URL as an argument
            timeout=25000 # Wait up to 25 seconds
        )
        logger.info("Login process finished (success or error detected by waitForFunction).")

        # --- Determine the final outcome ---
        # Re-evaluate the page state after waitForFunction completes
        current_url = page.url
        if current_url == success_url:
            logger.info("Successfully logged into Relab and redirected.")
            return # Login successful

        # If not redirected, check for errors explicitly
        error_message_locator = page.locator("div.error-message, span.error-text, div.alert") # Use same selectors as JS
        if await error_message_locator.count() > 0:
            # Get the text of the first visible error message
            visible_error_locators = []
            for i in range(await error_message_locator.count()):
                loc = error_message_locator.nth(i)
                if await loc.is_visible():
                    visible_error_locators.append(loc)

            if visible_error_locators:
                error_text = await visible_error_locators[0].text_content()
                error_text = error_text.strip() if error_text else "Unknown error element found"
                logger.error(f"Login failed. Error message detected on page: {error_text}")
                raise Exception(f"Login failed: {error_text}")


        # If no error message found but also not redirected, it's ambiguous
        logger.warning(f"Login process finished, but neither success redirect ({success_url}) nor clear error message was detected. Current URL: {current_url}")
        # Optional: Raise an error or proceed based on your logic
        # For now, let's assume if it didn't redirect, it failed.
        raise Exception("Login process completed but did not redirect to the dashboard. Likely authentication failure or page error.")

    except asyncio.TimeoutError:
        logger.error("Timeout waiting for login process to complete (loading to disappear, redirect, or error).")
        raise Exception("Login timed out. The process started but did not finish within the expected time.")

    # --- End waiting for login process ---

async def search_and_select_property_in_relab(page, address):
    """
    Searches for a property in Relab and selects the first matching suggestion.
    Assumes already logged in.
    """
    logger.info(f"Searching for property: {address}")
    
    # Locate the search input field using the provided ID
    search_input_selector = "div.v-select__slot input[type='text']"
    await page.wait_for_selector(search_input_selector, timeout=30000)
    
    # --- Anti-Bot Measure: Random delay and simulate typing ---
    await page.wait_for_timeout(random.uniform(500, 1000))
    # Optionally, use page.type with a delay for more human-like typing
    # await page.type(search_input_selector, address, delay=random.randint(50, 150))
    await page.fill(search_input_selector, address) # Simpler fill for now

    # Wait for suggestions to appear (wait for the list item title element)
    suggestion_selector = "div.v-list-item__title"
    logger.info("Waiting for search suggestions...")
    try:
        await page.wait_for_selector(suggestion_selector, state='visible', timeout=10000)
        logger.info("Search suggestions appeared.")
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for search suggestions.")
        # Check if there's an explicit "no results" message if needed
        # For now, we'll proceed and let the selection logic handle no suggestions
        pass # Continue, selection logic will handle empty list

    # --- Anti-Bot Measure: Delay after suggestions load ---
    await page.wait_for_timeout(random.uniform(500, 1500))

    # --- Select the first matching suggestion ---
    # Extract the part of the Trade Me address to match against (e.g., before the first comma)
    tm_address_part = address.split(',')[0].strip().lower()
    logger.info(f"Looking for suggestion matching: '{tm_address_part}'")

    # Find all suggestion titles
    suggestion_titles = await page.locator(suggestion_selector).all()
    selected = False
    for i, title_element in enumerate(suggestion_titles):
        try:
            suggestion_text = await title_element.text_content()
            suggestion_text_clean = suggestion_text.strip().lower() if suggestion_text else ""
            logger.debug(f"Checking suggestion {i+1}: '{suggestion_text_clean}'")
            
            # Check if the TM address part is in the suggestion text
            if tm_address_part in suggestion_text_clean:
                logger.info(f"Found matching suggestion: '{suggestion_text_clean}'. Clicking...")
                # Click the parent list item, not just the title div
                # The title div is usually inside a .v-list-item
                parent_item = title_element.locator('xpath=..') # Get parent
                await parent_item.click()
                selected = True
                break
            else:
                logger.debug(f"Suggestion {i+1} does not match.")
        except Exception as e:
            logger.warning(f"Error processing suggestion {i+1}: {e}")
            continue # Try the next suggestion

    if not selected:
        error_msg = f"No matching suggestion found for address part '{tm_address_part}' on Relab."
        logger.error(error_msg)
        raise Exception(error_msg)

        # --- Wait for the property listing page to load using a more robust locator ---
    logger.info("Waiting for property listing page to load (checking for key data elements)...")
    try:
        # 1. Create a locator for all divs with class containing 'container'
        container_divs_locator = page.locator("div[class*='container']")
        
        # 2. Select the first one from that list of locators
        first_container_locator = container_divs_locator.first
        
        # 3. Wait for this first locator to become visible
        await first_container_locator.wait_for(state='attached', timeout=20000)
        
        logger.info("Property listing page loaded (first div[class*='container'] is visible).")
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for the first 'div[class*='container']'. The page might still be loading or the structure is different. Proceeding.")
    except Exception as e: # Catch other potential errors during locator creation/waiting
        logger.error(f"An error occurred while waiting for the container div: {e}")
    # --- End wait for listing page ---

async def extract_relab_property_data(page):
    """Extracts specific property data points from the Relab listing page."""
    logger.info("Extracting specific property data from Relab listing...")
    data = {
        "Land Title": None,
        "Land Area": None,
        "Floor Area": None,
        "Bedroom(s)": None,
        "Year Built": None,
        "Bathroom(s)": None,
        "extracted_at": datetime.now(timezone(timedelta(hours=12))).isoformat() + 'Z'
    }

    # --- Anti-Bot Measure: Delay before starting extraction ---
    await page.wait_for_timeout(random.uniform(500, 1500))

    # --- Extract Land Title and Land Area (Robust & Specific) ---
    try:
        # Find the specific div containing exactly "Land Title"
        land_title_label_div = page.locator("div", has_text="Land Title").first
        await land_title_label_div.wait_for(state='attached', timeout=5000)

        # --- Extract Land Title and Land Area ---
        # The value is expected to be in the next sibling element.
        # Expected format: "Freehold 1096 m²" within the sibling element's text.
        land_title_value_div = land_title_label_div.locator("xpath=following-sibling::*[1]") # Get the next sibling element (could be div, span, etc.)

        land_title_full_text = ""
        if await land_title_value_div.count() > 0 and await land_title_value_div.first.is_visible():
            # Get the text content of the sibling element
            land_title_full_text = (await land_title_value_div.first.text_content()).strip()
            logger.debug(f"Raw Land Title/Area text found: '{land_title_full_text}'")
        else:
            logger.warning("Could not find the sibling element containing Land Title and Area.")

        if land_title_full_text:
            # --- Parse Land Title and Land Area from the combined text ---
            # Expected format: "<Title> <Number> m²"
            # Known Titles: Freehold, Leasehold, Unit Title, Cross Lease

            # Create a regex pattern to match the known titles followed by the area
            # \s+ matches one or more whitespace characters
            # ([\d,]+) captures the digits (including commas) for the area
            # \s*m² matches the unit 'm²' with optional preceding space
            title_pattern = r"^(Freehold|Leasehold|Unit Title|Cross Lease)\s+([\d,]+)\s*m²$"
            match = re.search(title_pattern, land_title_full_text)

            if match:
                extracted_title = match.group(1)
                extracted_area_raw = match.group(2)
                # Remove any commas from the area string for numerical use if needed
                extracted_area = extracted_area_raw.replace(',', '')

                data["Land Title"] = extracted_title
                data["Land Area"] = extracted_area
                logger.info(f"Successfully extracted Land Title: {data['Land Title']}, Land Area: {data['Land Area']} m²")
            else:
                # If the format doesn't match exactly, log details for debugging
                logger.warning(f"Found Land Title/Area text '{land_title_full_text}' but it didn't match the expected format '<Title> <Number> m²' with known titles.")
                data["Land Title"] = "Parse Error"
                data["Land Area"] = "Parse Error"
        else:
            logger.warning("Land Title/Area text was empty or not found.")
            data["Land Title"] = "Not Found"
            data["Land Area"] = "Not Found"

    except Exception as e:
        logger.error(f"Error extracting Land Title and Land Area: {e}")
        # Set defaults on error to prevent missing keys
        if "Land Title" not in data:
            data["Land Title"] = "Error"
        if "Land Area" not in data:
            data["Land Area"] = "Error"
    # --- End Extract Land Title and Land Area (Robust & Specific) ---

    # --- Extract Floor Area (Robust - Corrected filter usage) ---
    try:
        # Find the specific div containing exactly "Floor Area"
        # Use 'predicate' keyword argument for the lambda function
        floor_area_label_div = page.locator("div", has_text="Floor Area").first

        # Wait for this specific div to be attached (or visible if you prefer and it becomes visible)
        await floor_area_label_div.wait_for(state='attached', timeout=5000)

        # Find the associated value span (adjust xpath if needed based on actual HTML structure)
        # Common pattern: <div>Floor Area</div><span>210 m2</span>
        floor_area_value_span = floor_area_label_div.locator("xpath=following-sibling::span")
        # Fallback pattern: <div>Floor Area</div><div><span>210 m2</span></div>
        # floor_area_value_span = floor_area_label_div.locator("xpath=following-sibling::div/span")

        floor_area_text = ""
        if await floor_area_value_span.count() > 0 and await floor_area_value_span.first.is_visible():
            floor_area_text = await floor_area_value_span.first.text_content()
            logger.debug(f"Found Floor Area text: '{floor_area_text}'")
        # Add else for fallback if needed, or log if not found
        # else:
        #     logger.warning("Could not find Floor Area value span using standard sibling locators.")

        if floor_area_text:
            # Extract the number (e.g., "210" from "210 m2")
            number_match = re.search(r"([\d.]+)", floor_area_text)
            if number_match:
                data["Floor Area"] = number_match.group(1)
                logger.info(f"Successfully extracted Floor Area: {data['Floor Area']} m2")
            else:
                logger.warning(f"Found Floor Area text '{floor_area_text}' but couldn't extract a number.")
        # else warning handled above or by default

    except Exception as e:
        logger.error(f"Error extracting Floor Area: {e}")
    # --- End Extract Floor Area (Robust - Corrected) ---


    # --- Extract Bedroom(s) (Robust) ---
    try:
        bedroom_label_div = page.locator("div", has_text="Bedroom(s)").first
        await bedroom_label_div.wait_for(state='attached', timeout=5000)

        # Find the value span (adjust xpath if needed based on actual HTML structure)
        bedroom_value_span = bedroom_label_div.locator("xpath=following-sibling::span")

        if await bedroom_value_span.count() > 0:
            bedroom_text = await bedroom_value_span.first.text_content()
            logger.debug(f"Found Bedroom(s) text: '{bedroom_text}'")
            # Bedrooms are usually whole numbers
            number_match = re.search(r"(\d+)", bedroom_text)
            if number_match:
                data["Bedroom(s)"] = number_match.group(1)
                logger.info(f"Successfully extracted Bedroom(s): {data['Bedroom(s)']}")
            else:
                logger.warning(f"Found Bedroom(s) text '{bedroom_text}' but couldn't extract a number.")
        else:
            logger.warning("Could not find Bedroom(s) value span.")

    except Exception as e:
        logger.error(f"Error extracting Bedroom(s): {e}")
    # --- End Extract Bedroom(s) (Robust) ---

    # --- Extract Year Built (Robust) ---
    try:
        # Find the specific div containing exactly "Year Built"
        year_built_label_div = page.locator("div", has_text="Year Built").first
        await year_built_label_div.wait_for(state='attached', timeout=5000)

        # Find the associated value span (adjust xpath if needed based on actual HTML structure)
        # Common pattern: <div>Year Built</div><span>1980</span>
        year_built_value_span = year_built_label_div.locator("xpath=following-sibling::span")
        # Fallback pattern: <div>Year Built</div><div><span>1980</span></div>
        # year_built_value_span = year_built_label_div.locator("xpath=following-sibling::div/span")

        year_built_text = ""
        if await year_built_value_span.count() > 0 and await year_built_value_span.first.is_visible():
            year_built_text = await year_built_value_span.first.text_content()
            logger.debug(f"Found Year Built text: '{year_built_text}'")
        # Add else for fallback if needed, or log if not found
        # else:
        #     logger.warning("Could not find Year Built value span using standard sibling locators.")

        if year_built_text:
            # Extract the 4-digit year (e.g., "1980" from "Year Built 1980" or just "1980")
            # Using \b to ensure word boundary if the text is directly in the span
            year_match = re.search(r"\b(19|20)\d{2}\b", year_built_text)
            if year_match:
                data["Year Built"] = year_match.group(0) # Get the full 4-digit year
                logger.info(f"Successfully extracted Year Built: {data['Year Built']}")
            else:
                logger.warning(f"Found Year Built text '{year_built_text}' but couldn't extract a valid 4-digit year (19XX or 20XX).")
        # else warning handled above or by default

    except Exception as e:
        logger.error(f"Error extracting Year Built: {e}")
    # --- End Extract Year Built (Robust) ---

    # --- Extract Bathroom(s) (Robust) ---
    try:
        # Find the specific div containing exactly "Bathroom(s)"
        bathroom_label_div = page.locator("div", has_text="Bathroom(s)").first
        await bathroom_label_div.wait_for(state='attached', timeout=5000)

        # Find the associated value span (adjust xpath if needed based on actual HTML structure)
        # Common pattern: <div>Bathroom(s)</div><span>2</span>
        bathroom_value_span = bathroom_label_div.locator("xpath=following-sibling::span")
        # Fallback pattern: <div>Bathroom(s)</div><div><span>2</span></div>
        # bathroom_value_span = bathroom_label_div.locator("xpath=following-sibling::div/span")

        bathroom_text = ""
        if await bathroom_value_span.count() > 0 and await bathroom_value_span.first.is_visible():
            bathroom_text = await bathroom_value_span.first.text_content()
            logger.debug(f"Found Bathroom(s) text: '{bathroom_text}'")
        # Add else for fallback if needed, or log if not found
        # else:
        #     logger.warning("Could not find Bathroom(s) value span using standard sibling locators.")

        if bathroom_text:
            # Extract the number (usually whole number, e.g., "2" from "2")
            number_match = re.search(r"(\d+)", bathroom_text)
            if number_match:
                data["Bathroom(s)"] = number_match.group(1)
                logger.info(f"Successfully extracted Bathroom(s): {data['Bathroom(s)']}")
            else:
                    logger.warning(f"Found Bathroom(s) text '{bathroom_text}' but couldn't extract a number.")
        # else warning handled above or by default

    except Exception as e:
        logger.error(f"Error extracting Bathroom(s): {e}")
    # --- End Extract Bathroom(s) (Robust) ---

# --- The main scraping task orchestrates these steps ---
async def run_playwright_task(address):
    """Main Playwright task to login, search, select, and extract data."""
    logger.info(f"Starting Playwright task for address: {address}")
    async with async_playwright() as p:
        # Launch browser (consider headless=False for debugging)
        # Use Firefox or Webkit if Chromium is detected/blocked
        browser = await p.chromium.launch(headless=False) 
        # --- Anti-Bot Measure: Configure a realistic context ---
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36", # Example realistic UA
            viewport={"width": 1280, "height": 800},
            locale="en-NZ", # Set appropriate locale
            timezone_id="Pacific/Auckland" # Set appropriate timezone
            # Consider adding extra headers if needed based on inspection
            # extra_http_headers={"Referer": "https://relab.co.nz/"}
        )
        page = await context.new_page()

        try:
            await login_to_relab(page)
            await search_and_select_property_in_relab(page, address)
            # --- Anti-Bot Measure: Delay after selection and before extraction ---
            await page.wait_for_timeout(random.uniform(1000, 2000))
            property_data = await extract_relab_property_data(page)
            
            # For now, return just the extracted property data
            # CMA logic would be implemented here or in a subsequent step
            logger.info("Playwright task completed successfully.")
            return {"success": True, "data": property_data, "screenshots": []} # Add screenshots if implemented
        except Exception as e:
            logger.error(f"Playwright task failed for {address}: {e}")
            # --- Debug: Save page content on failure ---
            try:
                failure_html_path = f"debug_relab_failure_{datetime.now(timezone(timedelta(hours=12))).strftime('%Y%m%d_%H%M%S')}.html"
                with open(failure_html_path, 'w', encoding='utf-8') as f:
                    f.write(await page.content())
                logger.info(f"Failure HTML saved to {failure_html_path}")
            except Exception as debug_e:
                logger.error(f"Failed to save debug HTML: {debug_e}")
            # --- End Debug ---
            return {"success": False, "error": str(e)}
        finally:
            await page.close()
            await context.close()
            await browser.close()

# --- Flask Routes ---
@app.route('/api/get_relab_data', methods=['POST'])
def get_relab_data():
    """API endpoint for the extension to request Relab data."""
    print("Flask route /api/get_relab_data was called with POST") # <-- Add this
    data = request.get_json()
    address = data.get('address')
    trademe_url = data.get('trademe_url') # Optional, for logging/context

    if not address:
        return jsonify({"success": False, "error": "Address is required"}), 400

    logger.info(f"Received request for Relab data: Address={address}, TM_URL={trademe_url}")

    # Run the Playwright task asynchronously
    # Flask isn't inherently async, so we run the coroutine directly.
    # For production, consider using Celery or making the Flask app async (Quart).
    try:
        # This runs the async function in the current event loop
        # If this causes issues, you might need to run it in a thread or subprocess
        result = asyncio.run(run_playwright_task(address))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error running Playwright task: {e}")
        return jsonify({"success": False, "error": "Internal server error during scraping"}), 500

@app.route('/api/save_to_watchlist', methods=['POST'])
def save_to_watchlist():
    """API endpoint to save property data to the watchlist."""
    data = request.get_json()
    property_info = data.get('property_info')
    if not property_info:
        return jsonify({"success": False, "error": "Property info is required"}), 400

    # Add to in-memory DB (demo)
    watchlist_db.append(property_info)
    logger.info(f"Saved property to watchlist: {property_info.get('address', 'Unknown')}")
    return jsonify({"success": True, "message": "Property saved to watchlist"})

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """API endpoint to retrieve the watchlist."""
    return jsonify({"success": True, "data": watchlist_db})

@app.route('/')
def index():
    return "Relab Integration Backend Server is running."

if __name__ == '__main__':
    logger.info("Starting Flask server...")
    app.run(host='127.0.0.1', port=PORT, debug=True)
