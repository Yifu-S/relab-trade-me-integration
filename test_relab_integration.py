#!/usr/bin/env python3
"""
Test script for real Relab integration
This script tests the actual Playwright automation with Relab
"""

import asyncio
import sys
import os
from relab_automation import RelabAutomation

async def test_relab_integration():
    """Test the real Relab integration"""
    print("🧪 Testing Real Relab Integration")
    print("=" * 50)
    
    # Initialize Relab automation
    try:
        relab = RelabAutomation()
        print("✅ RelabAutomation initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize RelabAutomation: {e}")
        return False
    
    # Test property search
    test_address = "123 Queen Street, Auckland"
    print(f"\n🔍 Testing property search for: {test_address}")
    
    try:
        # Initialize browser (non-headless for debugging) with timeout
        print("🔄 Initializing browser (this may take up to 60 seconds)...")
        await asyncio.wait_for(relab.init_browser(headless=False), timeout=60.0)
        print("✅ Browser initialized and logged in")
        
        # Search for property with timeout
        print("🔄 Searching for property (this may take up to 60 seconds)...")
        property_data = await asyncio.wait_for(relab.search_property(test_address), timeout=60.0)
        print(f"✅ Property search completed")
        print(f"📊 Extracted data: {property_data}")
        
        # Test CMA analysis with timeout
        print(f"\n📈 Testing CMA analysis (this may take up to 60 seconds)...")
        cma_results = await asyncio.wait_for(relab.run_cma(property_data), timeout=60.0)
        print(f"✅ CMA analysis completed")
        print(f"📊 CMA results: {cma_results}")
        
        # Close browser
        await relab.close()
        print("✅ Browser closed successfully")
        
        return True
        
    except asyncio.TimeoutError:
        print("❌ Test timed out after 60 seconds")
        try:
            await relab.close()
        except:
            pass
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        try:
            await relab.close()
        except:
            pass
        return False

def test_sync_wrappers():
    """Test the synchronous wrappers"""
    print("\n🔄 Testing Synchronous Wrappers")
    print("=" * 50)
    
    try:
        relab = RelabAutomation()
        print("✅ RelabAutomation initialized")
        
        # Test sync property search
        test_address = "456 Ponsonby Road, Auckland"
        print(f"\n🔍 Testing sync property search for: {test_address}")
        
        # Add timeout for sync operations
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Sync operation timed out")
        
        # Set timeout for sync operations (30 seconds)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            property_data = relab.search_property_sync(test_address)
            signal.alarm(0)  # Cancel the alarm
            print(f"✅ Sync property search completed")
            print(f"📊 Extracted data: {property_data}")
            
            # Test sync CMA analysis
            print(f"\n📈 Testing sync CMA analysis...")
            signal.alarm(30)  # Set timeout for CMA
            cma_results = relab.run_cma_sync(property_data)
            signal.alarm(0)  # Cancel the alarm
            print(f"✅ Sync CMA analysis completed")
            print(f"📊 CMA results: {cma_results}")
            
            return True
            
        except TimeoutError:
            signal.alarm(0)  # Cancel the alarm
            print("❌ Sync operation timed out after 30 seconds")
            return False
        
    except Exception as e:
        print(f"❌ Sync test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Relab Integration Tests")
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
    
    # Test async integration
    async_success = asyncio.run(test_relab_integration())
    
    # Test sync wrappers
    sync_success = test_sync_wrappers()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print("=" * 50)
    print(f"Async Integration: {'✅ PASS' if async_success else '❌ FAIL'}")
    print(f"Sync Wrappers: {'✅ PASS' if sync_success else '❌ FAIL'}")
    
    if async_success and sync_success:
        print("\n🎉 All tests passed! Real Relab integration is working.")
        return True
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
