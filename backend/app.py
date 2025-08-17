# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import logging
from playwright.async_api import async_playwright
import os
import json
from datetime import datetime
import re

# --- Configuration ---
RELAb_EMAIL = os.environ.get("RELAB_EMAIL", "your_email@example.com") # Use environment variables for credentials
RELAb_PASSWORD = os.environ.get("RELAB_PASSWORD", "your_password")
PORT = 5000
# --- End Configuration ---

app = Flask(__name__)
# Allow CORS for requests from the browser extension (adjust origin as needed)
CORS(app, origins=["chrome-extension://<YOUR_EXTENSION_ID>", "http://localhost:*"])

# In-memory storage for demo (use a real DB in production)
watchlist_db = []

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Playwright Logic ---
async def login_to_relab(page):
    """Logs into Relab."""
    logger.info("Logging into Relab...")
    await page.goto("https://relab.co.nz/login")
    await page.wait_for_selector("input#email", timeout=10000)
    await page.fill("input#email", RELAb_EMAIL)
    await page.fill("input#password", RELAb_PASSWORD)
    await page.click("button[type='submit']")
    # Wait for login to complete (adjust selector)
    await page.wait_for_selector("a[href='/dashboard']", timeout=30000)
    logger.info("Logged into Relab successfully.")

async def search_property_in_relab(page, address):
    """Searches for a property in Relab by address."""
    logger.info(f"Searching for property: {address}")
    # Navigate to search (adjust URL and selectors as needed)
    await page.goto("https://relab.co.nz/property-search")
    await page.wait_for_selector("input#address-search", timeout=10000)
    await page.fill("input#address-search", address)
    await page.click("button.search-button") # Adjust selector
    # Wait for search results or property page to load
    # This is tricky as Relab might show a list or go directly to the property
    # Let's assume it goes to a property page or a list page
    try:
        # Try waiting for a common property detail element
        await page.wait_for_selector("div.property-details-header", timeout=15000)
        logger.info("Found property page directly.")
        return True # Landed on property page
    except:
        logger.info("Did not land on property page directly, checking for list...")
        # If not on property page, might be on a list. Check for list items.
        # This logic needs refinement based on Relab's actual structure.
        # For demo, let's assume if we don't get the property page, we failed to find it uniquely.
        # A more robust solution would parse the list and select the best match.
        return False # Might need list handling

async def extract_relab_data(page):
    """Extracts key data and screenshots from the Relab property page."""
    logger.info("Extracting Relab data...")
    data = {
        "extracted_at": datetime.utcnow().isoformat() + 'Z',
        "screenshots": [],
        "key_points": {}
    }

    try:
        # --- Extract Key Due Diligence Points (Example) ---
        # These selectors are illustrative and need to be updated based on Relab's actual HTML
        try:
            data["key_points"]["title_status"] = await page.locator("div.title-status-section .status-value").text_content(timeout=5000)
        except: data["key_points"]["title_status"] = "Not Found"
        try:
            data["key_points"]["land_area"] = await page.locator("div.property-attributes .land-area").text_content(timeout=5000)
        except: data["key_points"]["land_area"] = "Not Found"
        try:
            data["key_points"]["floor_area"] = await page.locator("div.property-attributes .floor-area").text_content(timeout=5000)
        except: data["key_points"]["floor_area"] = "Not Found"
        try:
            data["key_points"]["build_era"] = await page.locator("div.property-attributes .build-era").text_content(timeout=5000)
        except: data["key_points"]["build_era"] = "Not Found"
        try:
            data["key_points"]["flood_risk"] = await page.locator("div.environmental-section .flood-risk").text_content(timeout=5000)
        except: data["key_points"]["flood_risk"] = "Not Found"

        logger.info(f"Extracted key points: {data['key_points']}")
    except Exception as e:
        logger.error(f"Error extracting key points: {e}")

    try:
        # --- Capture Screenshots (Example) ---
        # Define areas or elements to capture. For demo, capture full page or key sections.
        # You might want to scroll and capture multiple sections.
        screenshot_dir = "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        base_filename = f"relab_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Example: Capture a specific section like the map
        map_locator = page.locator("div#property-map") # Adjust selector
        if await map_locator.count() > 0:
            map_path = os.path.join(screenshot_dir, f"{base_filename}_map.png")
            await map_locator.screenshot(path=map_path, full_page=False)
            data["screenshots"].append(map_path)
            logger.info(f"Screenshot saved: {map_path}")

        # Example: Capture the main property details section
        details_locator = page.locator("div.property-details-main") # Adjust selector
        if await details_locator.count() > 0:
            details_path = os.path.join(screenshot_dir, f"{base_filename}_details.png")
            await details_locator.screenshot(path=details_path, full_page=False)
            data["screenshots"].append(details_path)
            logger.info(f"Screenshot saved: {details_path}")

        # Add more screenshots as needed for the 4 required views
        # ...

    except Exception as e:
        logger.error(f"Error capturing screenshots: {e}")

    return data

async def run_playwright_task(address):
    """Main Playwright task to login, search, and extract data."""
    logger.info(f"Starting Playwright task for address: {address}")
    async with async_playwright() as p:
        # Launch browser (consider headless=False for debugging)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            # Set a realistic user agent if needed
            # user_agent="Mozilla/5.0 ..."
        )
        page = await context.new_page()

        try:
            await login_to_relab(page)
            found = await search_property_in_relab(page, address)
            if found:
                relab_data = await extract_relab_data(page)
                logger.info("Playwright task completed successfully.")
                return {"success": True, "data": relab_data}
            else:
                logger.warning(f"Property not found uniquely in Relab for address: {address}")
                return {"success": False, "error": "Property not found in Relab"}
        except Exception as e:
            logger.error(f"Playwright task failed for {address}: {e}")
            # Save page content for debugging
            try:
                failure_html_path = f"debug_failure_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
                with open(failure_html_path, 'w', encoding='utf-8') as f:
                    f.write(await page.content())
                logger.info(f"Failure HTML saved to {failure_html_path}")
            except: pass
            return {"success": False, "error": str(e)}
        finally:
            await page.close()
            await context.close()
            await browser.close()

# --- Flask Routes ---
@app.route('/api/get_relab_data', methods=['POST'])
def get_relab_data():
    """API endpoint for the extension to request Relab data."""
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
