#!/usr/bin/env python3
"""Test script to verify the Playwright NotImplementedError fix."""

import requests
import json
import time


def test_copilot_endpoint():
    """Test the /v1/process/copilot endpoint to verify the fix."""

    url = "http://localhost:8000/v1/process/copilot"

    # Simple test prompt
    data = {"prompt": "Hello, what is 2+2?"}

    print("Testing Copilot endpoint...")
    print(f"URL: {url}")
    print(f"Prompt: {data['prompt']}")

    try:
        print("\nSending request...")
        start_time = time.time()

        response = requests.post(
            url,
            data=data,
            timeout=180,  # 3 minute timeout
        )

        duration = time.time() - start_time
        print(f"Request completed in {duration:.2f} seconds")
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n✓ SUCCESS: Request completed successfully!")
            print(
                f"Response message: {result.get('result', {}).get('message', 'No message')}"
            )
            return True
        else:
            print(f"\n✗ ERROR: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Error response: {response.text}")
            return False

    except requests.exceptions.ConnectRefused:
        print(
            "\n✗ ERROR: Cannot connect to server. Is the FastAPI app running on localhost:8000?"
        )
        return False
    except requests.exceptions.Timeout:
        print("\n✗ ERROR: Request timed out after 3 minutes")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: Unexpected error: {e}")
        return False


def test_health_endpoint():
    """Test the health endpoint first to verify server is running."""

    url = "http://localhost:8000/v1/health"

    try:
        print("Checking server health...")
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            print("[OK] Server is running and healthy")
            return True
        else:
            print(f"[ERROR] Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Health check failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Playwright NotImplementedError Fix Test")
    print("=" * 60)

    # First check if server is running
    if not test_health_endpoint():
        print("\nPlease start the FastAPI server first:")
        print(
            "conda activate python3.11 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
        )
        exit(1)

    print("\n" + "-" * 40)

    # Test the Copilot endpoint
    success = test_copilot_endpoint()

    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] FIX VERIFICATION: The NotImplementedError appears to be resolved!")
        print("The Windows event loop policy fix is working correctly.")
    else:
        print("[FAILED] FIX VERIFICATION: Issues still remain.")
        print("Check the server logs for more detailed error information.")
    print("=" * 60)
