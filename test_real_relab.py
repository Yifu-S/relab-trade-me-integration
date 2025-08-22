#!/usr/bin/env python3
"""
Test script for real Relab automation
"""

import asyncio
import signal
import sys
from relab_automation import RelabAutomation

def timeout_handler(signum, frame):
    print("⏰ Timeout reached! Exiting...")
    sys.exit(1)

def test_real_relab():
    """Test real Relab automation with timeout"""
    print("🚀 Testing Real Relab Automation...")
    
    # Set timeout for the entire test
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(300)  # 5 minutes timeout
    
    try:
        # Test address
        test_address = "3A Gilbert Avenue, Grey Lynn, Auckland City, Auckland"
        
        # Initialize Relab automation
        relab = RelabAutomation()
        
        print(f"🔍 Testing property search for: {test_address}")
        
        # Test property search
        property_data = relab.search_property_sync(test_address)
        print(f"✅ Property data retrieved: {property_data}")
        
        # Test CMA analysis
        print("📊 Testing CMA analysis...")
        cma_results = relab.run_cma_sync(property_data)
        print(f"✅ CMA results: {cma_results}")
        
        print("🎉 Real Relab automation test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during real Relab automation test: {e}")
        return False
    finally:
        signal.alarm(0)  # Cancel timeout
    
    return True

if __name__ == "__main__":
    success = test_real_relab()
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed!")
        sys.exit(1)
