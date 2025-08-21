#!/usr/bin/env python3
"""
Demo script for Relab Trade Me Integration
This script demonstrates the core functionality without requiring the browser extension.
"""

import asyncio
import json
from cma_analyzer import CMAAnalyzer
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def demo_trademe_data():
    """Demo Trade Me data (from Phase I)"""
    print("🏠 Demo: Trade Me Data (Phase I - Already Implemented)")
    print("=" * 50)

    # Mock Trade Me data (from Phase I implementation)
    mock_trademe_data = {
        "address": "123 Demo Street, Auckland",
        "price": 850000,
        "bedrooms": 3,
        "bathrooms": 2,
        "land_area": 600,
        "floor_area": 120,
        "year_built": 1995,
        "land_title": "Freehold",
        "listing_date": "2024-01-15",
        "description": "Beautiful family home in prime location with great potential for development.",
    }

    print("✅ Trade Me Data (from Phase I):")
    for key, value in mock_trademe_data.items():
        if key == "price":
            print(f"  {key}: ${value:,}")
        elif key in ["land_area", "floor_area"]:
            print(f"  {key}: {value} m²")
        else:
            print(f"  {key}: {value}")

    return mock_trademe_data


def demo_relab_data():
    """Demo Relab data extraction"""
    print("\n📊 Demo: Relab Data Extraction")
    print("=" * 50)

    # Mock Relab data
    mock_relab_data = {
        "land_title": "Freehold",
        "land_area": 600,
        "floor_area": 120,
        "year_built": 1995,
        "bedrooms": 3,
        "bathrooms": 2,
        "cv": 750000,
    }

    print("✅ Extracted Relab Data:")
    for key, value in mock_relab_data.items():
        if key == "cv":
            print(f"  {key}: ${value:,}")
        elif key in ["land_area", "floor_area"]:
            print(f"  {key}: {value} m²")
        else:
            print(f"  {key}: {value}")

    return mock_relab_data


def demo_cma_analysis(property_data):
    """Demo CMA analysis"""
    print("\n📈 Demo: Comparative Market Analysis")
    print("=" * 50)

    analyzer = CMAAnalyzer()

    # Run CMA analysis
    cma_results = analyzer.run_cma_analysis(property_data)

    if "error" in cma_results:
        print(f"❌ Error: {cma_results['error']}")
        return

    # Display results
    print("✅ CMA Analysis Results:")

    # Valuation range
    valuation = cma_results["valuation_range"]["overall_range"]
    print(f"  Valuation Range: ${valuation['low']:,} - ${valuation['high']:,}")
    print(f"  Mid-Point: ${valuation['mid']:,}")

    # Benchmarks
    benchmarks = cma_results["benchmarks"]
    print(f"  Sale/CV Ratio: {benchmarks['avg_sale_cv_ratio']}")
    print(f"  Floor Rate: ${benchmarks['avg_floor_rate']:,}/m²")
    print(f"  Land Rate: ${benchmarks['avg_land_rate']:,}/m²")

    # Analysis summary
    summary = cma_results["analysis_summary"]
    print(f"  Confidence Level: {summary['confidence_level']}")
    print(f"  Market Volatility: {summary['market_volatility']}")
    print(f"  Recommendation: {summary['recommendation']}")

    # Comparable sales
    comparables = cma_results["comparable_sales"]
    print(f"\n  Comparable Sales ({len(comparables)} properties):")
    for i, sale in enumerate(comparables[:3], 1):  # Show first 3
        print(
            f"    {i}. {sale['address']} - ${sale['sale_price']:,} (CV: ${sale['cv']:,})"
        )

    return cma_results


def demo_combined_analysis():
    """Demo the complete analysis workflow"""
    print("\n🎯 Demo: Complete Analysis Workflow")
    print("=" * 50)

    # Step 1: Get Trade Me data (from Phase I)
    trademe_data = demo_trademe_data()

    # Step 2: Extract Relab data
    relab_data = demo_relab_data()

    # Step 3: Run CMA analysis (using Relab data as base)
    cma_results = demo_cma_analysis(relab_data)

    # Step 4: Combine results
    combined_data = {
        "trademe_data": trademe_data,
        "relab_data": relab_data,
        "cma_analysis": cma_results,
    }

    print("\n✅ Combined Analysis Complete!")
    print("=" * 50)

    # Summary
    print("📋 Summary:")
    print(f"  Property: {trademe_data['address']}")
    print(f"  Trade Me Price: ${trademe_data['price']:,}")
    print(f"  Relab CV: ${relab_data['cv']:,}")

    if cma_results and "valuation_range" in cma_results:
        valuation = cma_results["valuation_range"]["overall_range"]
        print(
            f"  CMA Valuation: ${valuation['mid']:,} (${valuation['low']:,} - ${valuation['high']:,})"
        )

        # Calculate price vs valuation
        price = trademe_data["price"]
        mid_val = valuation["mid"]
        diff_pct = ((price - mid_val) / mid_val) * 100

        if diff_pct > 10:
            print(f"  💡 Analysis: Property appears overpriced by {abs(diff_pct):.1f}%")
        elif diff_pct < -10:
            print(
                f"  💡 Analysis: Property appears underpriced by {abs(diff_pct):.1f}%"
            )
        else:
            print(f"  💡 Analysis: Property appears fairly priced ({diff_pct:+.1f}%)")

    return combined_data


def demo_api_endpoints():
    """Demo the API endpoints"""
    print("\n🌐 Demo: API Endpoints")
    print("=" * 50)

    print("Available endpoints:")
    print("  POST /api/property/analyze")
    print("    - Analyzes property from Trade Me URL")
    print("    - Returns combined Trade Me + Relab + CMA data")
    print()
    print("  POST /api/property/save")
    print("    - Saves property to watchlist")
    print("    - Returns success message")
    print()
    print("  POST /api/property/report")
    print("    - Generates AI property report")
    print("    - Returns investment recommendations")
    print()
    print("  GET /")
    print("    - Main dashboard page")
    print("    - Web interface for property analysis")


def main():
    """Main demo function"""
    print("🚀 Relab Trade Me Integration - Phase II Demo")
    print("=" * 60)
    print("This demo showcases the core functionality of the integration.")
    print(
        "For full functionality, start the Flask server and install the Chrome extension."
    )
    print()

    try:
        # Run complete demo
        combined_data = demo_combined_analysis()

        # Demo API endpoints
        demo_api_endpoints()

        print("\n" + "=" * 60)
        print("🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Create .env file with your Relab credentials")
        print("2. Run: python app.py")
        print("3. Install Chrome extension from extension/ folder")
        print("4. Visit a Trade Me property page and click 'Get Relab Data'")
        print("\n🎯 Phase II Focus:")
        print("- Relab automation and data extraction")
        print("- CMA (Comparative Market Analysis)")
        print("- Split-screen property analysis")
        print("- Investment recommendations")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("Please check your setup and try again.")


if __name__ == "__main__":
    main()
