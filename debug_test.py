#!/usr/bin/env python3
"""
Debug test script to identify infinite loops
"""

import sys
import os
import time
from relab_automation import RelabAutomation


def debug_test():
    """Debug test with detailed logging"""
    print("🔍 DEBUG TEST STARTING")
    print("=" * 50)

    try:
        print("Step 1: Import successful")

        # Test 1: Initialize RelabAutomation
        print("\nStep 2: Initializing RelabAutomation...")
        start_time = time.time()
        relab = RelabAutomation()
        print(f"✅ RelabAutomation initialized in {time.time() - start_time:.2f}s")

        # Test 2: Test fallback data
        print("\nStep 3: Testing fallback data...")
        start_time = time.time()
        fallback_data = relab.get_fallback_data("test address")
        print(f"✅ Fallback data generated in {time.time() - start_time:.2f}s")
        print(f"📊 Data: {fallback_data}")

        # Test 3: Test fallback CMA
        print("\nStep 4: Testing fallback CMA...")
        start_time = time.time()
        fallback_cma = relab.get_fallback_cma()
        print(f"✅ Fallback CMA generated in {time.time() - start_time:.2f}s")
        print(f"📊 CMA: {fallback_cma}")

        # Test 4: Test sync wrapper (this is where it might get stuck)
        print("\nStep 5: Testing sync wrapper...")
        start_time = time.time()
        print("  - About to call search_property_sync...")
        result = relab.search_property_sync("test address")
        print(f"✅ Sync search completed in {time.time() - start_time:.2f}s")
        print(f"📊 Result: {result}")

        # Test 5: Test CMA sync wrapper
        print("\nStep 6: Testing CMA sync wrapper...")
        start_time = time.time()
        print("  - About to call run_cma_sync...")
        cma_result = relab.run_cma_sync(result)
        print(f"✅ Sync CMA completed in {time.time() - start_time:.2f}s")
        print(f"📊 Result: {cma_result}")

        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        return True

    except Exception as e:
        print(f"\n❌ ERROR OCCURRED: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main debug function"""
    print("🚀 Starting Debug Test")
    print("=" * 50)

    # Check environment variables
    email = os.getenv("RELAb_EMAIL")
    password = os.getenv("RELAb_PASSWORD")

    if not email or not password:
        print("❌ RELAb_EMAIL and RELAb_PASSWORD must be set in .env file")
        return False

    print(f"✅ Relab credentials found: {email}")

    # Run debug test
    success = debug_test()

    if success:
        print("\n🎉 Debug test completed successfully!")
    else:
        print("\n⚠️ Debug test failed!")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
