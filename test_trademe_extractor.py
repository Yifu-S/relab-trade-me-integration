#!/usr/bin/env python3
"""
Test script for Trade Me extractor
"""

import requests
from bs4 import BeautifulSoup
import re


def test_trademe_extraction():
    url = "https://www.trademe.co.nz/a/property/residential/sale/auckland/auckland-city/grey-lynn/listing/5483955887"

    print(f"Testing URL: {url}")

    # Create session with headers
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    )

    try:
        # Fetch the page
        print("Fetching page...")
        response = session.get(url, timeout=10)
        response.raise_for_status()

        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")

        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")

        print(f"Page title: {soup.title.string if soup.title else 'No title'}")

        # Try to find address in different ways
        print("\n=== Testing address extraction ===")

        # Method 1: Look for h1 tags
        h1_tags = soup.find_all("h1")
        print(f"Found {len(h1_tags)} h1 tags:")
        for i, h1 in enumerate(h1_tags):
            print(f"  H1 {i+1}: {h1.get_text(strip=True)}")

        # Method 2: Look for address-related classes
        address_selectors = [
            '[data-testid="address"]',
            ".address",
            ".property-address",
            'h1[class*="address"]',
            '[class*="address"]',
            '[data-testid="listing-title"]',
            ".listing-title",
            ".property-title",
        ]

        print("\nTesting address selectors:")
        for selector in address_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"  {selector}: {len(elements)} elements found")
                for elem in elements:
                    text = elem.get_text(strip=True)
                    print(f"    Text: {text}")

        # Method 3: Look for address patterns in page text
        page_text = soup.get_text()
        print(f"\nPage text length: {len(page_text)} characters")

        # Look for address patterns
        address_patterns = [
            r"(\d+[A-Za-z]?\s+[A-Za-z\s]+,\s+[A-Za-z\s]+,\s+[A-Za-z\s]+)",
            r"(\d+[A-Za-z]?\s+[A-Za-z\s]+,\s+[A-Za-z\s]+)",
            r"(\d+[A-Za-z]?\s+[A-Za-z\s]+)",
        ]

        print("\nTesting address patterns:")
        for pattern in address_patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                print(f"  Pattern {pattern}: {len(matches)} matches")
                for match in matches[:5]:  # Show first 5 matches
                    print(f"    Match: {match}")

        # Method 4: Look for specific text that might contain the address
        print("\nSearching for specific address text:")
        search_terms = ["3A Gilbert Avenue", "Gilbert Avenue", "Grey Lynn"]
        for term in search_terms:
            if term in page_text:
                print(f"  Found '{term}' in page text")
                # Find context around the term
                index = page_text.find(term)
                start = max(0, index - 50)
                end = min(len(page_text), index + len(term) + 50)
                context = page_text[start:end]
                print(f"    Context: ...{context}...")

        # Method 5: Check if page is blocked or requires JavaScript
        if (
            "javascript" in page_text.lower()
            or "enable javascript" in page_text.lower()
        ):
            print("\n⚠️  Page might require JavaScript to load content")

        if "blocked" in page_text.lower() or "access denied" in page_text.lower():
            print("\n⚠️  Page access might be blocked")

        # Save a sample of the HTML for inspection
        with open("trademe_page_sample.html", "w", encoding="utf-8") as f:
            f.write(str(soup)[:10000])  # First 10k characters
        print("\nSaved first 10k characters of HTML to 'trademe_page_sample.html'")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_trademe_extraction()
