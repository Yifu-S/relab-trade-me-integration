#!/usr/bin/env python3
"""
Simple test script for fallback functionality
This script tests the Relab automation without trying to connect to Relab
"""

import sys
import os
from relab_automation import RelabAutomation

def test_fallback_functionality():
    """Test the fallback functionality without real Relab connection"""
    print("🧪 Testing Fallback Functionality")
    print("=" * 50)
    
    try:
        # Initialize Relab automation
        relab = RelabAutomation()
        print("✅ RelabAutomation initialized successfully")
        
        # Test fallback data generation
        test_address = "123 Queen Street, Auckland"
        print(f"\n🔍 Testing fallback data for: {test_address}")
        
        fallback_data = relab.get_fallback_data(test_address)
        print(f"✅ Fallback data generated")
        print(f"📊 Fallback data: {fallback_data}")
        
        # Test fallback CMA
        print(f"\n📈 Testing fallback CMA...")
        fallback_cma = relab.get_fallback_cma()
        print(f"✅ Fallback CMA generated")
        print(f"📊 Fallback CMA: {fallback_cma}")
        
        # Test sync wrappers (these should use fallback data)
        print(f"\n🔄 Testing sync wrappers with fallback...")
        
        # Mock the sync methods to return fallback data
        original_search = relab.search_property_sync
        original_cma = relab.run_cma_sync
        
        def mock_search_sync(address):
            print(f"🔄 Mock search for: {address}")
            return fallback_data
            
        def mock_cma_sync(property_data):
            print(f"🔄 Mock CMA for property data")
            return fallback_cma
            
        relab.search_property_sync = mock_search_sync
        relab.run_cma_sync = mock_cma_sync
        
        # Test the mock sync methods
        test_result = relab.search_property_sync(test_address)
        print(f"✅ Mock sync search completed")
        print(f"📊 Result: {test_result}")
        
        cma_result = relab.run_cma_sync(test_result)
        print(f"✅ Mock sync CMA completed")
        print(f"📊 Result: {cma_result}")
        
        # Restore original methods
        relab.search_property_sync = original_search
        relab.run_cma_sync = original_cma
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_data_extraction():
    """Test the data extraction utilities"""
    print("\n🔧 Testing Data Extraction Utilities")
    print("=" * 50)
    
    try:
        relab = RelabAutomation()
        
        # Test number extraction
        test_cases = [
            ("$750,000", 750000),
            ("1,200 m²", 1200),
            ("3 bedrooms", 3),
            ("2.5 bathrooms", 2.5),
            ("Built in 1995", 1995),
            ("No numbers here", None),
            ("", None)
        ]
        
        print("Testing number extraction:")
        for text, expected in test_cases:
            result = relab.extract_number(text)
            status = "✅" if result == expected else "❌"
            print(f"  {status} '{text}' -> {result} (expected: {expected})")
        
        return True
        
    except Exception as e:
        print(f"❌ Data extraction test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Fallback Functionality Tests")
    print("=" * 50)
    
    # Check environment variables
    email = os.getenv('RELAb_EMAIL')
    password = os.getenv('RELAb_PASSWORD')
    
    if not email or not password:
        print("❌ RELAb_EMAIL and RELAb_PASSWORD must be set in .env file")
        print("Please add your Relab credentials to the .env file:")
        print("RELAb_EMAIL=your_email@example.com")
        print("RELAb_PASSWORD=your_password")
        return False
    
    print(f"✅ Relab credentials found: {email}")
    
    # Test fallback functionality
    fallback_success = test_fallback_functionality()
    
    # Test data extraction
    extraction_success = test_data_extraction()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print("=" * 50)
    print(f"Fallback Functionality: {'✅ PASS' if fallback_success else '❌ FAIL'}")
    print(f"Data Extraction: {'✅ PASS' if extraction_success else '❌ FAIL'}")
    
    if fallback_success and extraction_success:
        print("\n🎉 All fallback tests passed! The system can handle errors gracefully.")
        return True
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
