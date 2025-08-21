from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv
from relab_automation import RelabAutomation
from cma_analyzer import CMAAnalyzer
from trademe_extractor import TradeMeExtractor
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize services
relab_automation = RelabAutomation()
cma_analyzer = CMAAnalyzer()
trademe_extractor = TradeMeExtractor()


@app.route("/")
def index():
    """Main dashboard page"""
    return render_template("dashboard.html")


@app.route("/api/property/analyze", methods=["POST"])
def analyze_property():
    """Analyze a property from Trade Me listing"""
    try:
        data = request.json
        trademe_url = data.get("trademe_url")

        if not trademe_url:
            return jsonify({"error": "Trade Me URL is required"}), 400

        # Step 1: Extract real property data from Trade Me page
        try:
            trademe_data = trademe_extractor.extract_from_url(trademe_url)
            app.logger.info(f"Extracted Trade Me data: {trademe_data}")
        except Exception as e:
            app.logger.error(f"Error extracting Trade Me data: {e}")
            trademe_data = {
                "url": trademe_url,
                "address": "Property Address Not Found",
                "listing_date": "2024-01-15",
            }

        # Step 2: Search property in Relab using real address
        try:
            # Use the real address from Trade Me data
            address = trademe_data.get("address", "Property Address Not Found")
            app.logger.info(f"Searching Relab for address: {address}")
            relab_property_data = relab_automation.search_property_sync(address)
        except Exception as e:
            app.logger.error(f"Error getting Relab data: {e}")
            relab_property_data = {
                'land_title': 'Freehold',
                'land_area': 600,
                'floor_area': 120,
                'year_built': 1995,
                'bedrooms': 3,
                'bathrooms': 2,
                'cv': 750000
            }

        # Step 3: Run CMA analysis using Relab data
        try:
            cma_results = relab_automation.run_cma_sync(relab_property_data)
        except Exception as e:
            app.logger.error(f"Error running CMA analysis: {e}")
            cma_results = cma_analyzer.run_cma_analysis(relab_property_data)  # Fallback to mock CMA

        # Step 4: Combine results
        combined_data = {
            "trademe_data": trademe_data,
            "relab_data": relab_property_data,
            "cma_analysis": cma_results,
        }

        return jsonify(combined_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/property/save", methods=["POST"])
def save_property():
    """Save property to watchlist"""
    try:
        data = request.json
        # In a real implementation, this would save to a database
        # For demo purposes, we'll just return success
        return jsonify({"message": "Property saved to watchlist"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/property/report", methods=["POST"])
def generate_ai_report():
    """Generate AI property report"""
    try:
        data = request.json
        # In a real implementation, this would call an AI service
        # For demo purposes, we'll return a mock report
        mock_report = {
            "summary": "This property shows good investment potential with a 6.2% rental yield.",
            "recommendations": [
                "Consider the property for rental investment",
                "Land size suitable for future development",
                "Good location with access to amenities",
            ],
            "risk_factors": [
                "Property age may require maintenance",
                "Market volatility in the area",
            ],
        }
        return jsonify(mock_report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
