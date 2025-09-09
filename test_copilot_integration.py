#!/usr/bin/env python3
"""Simple test script to verify the Copilot integration works."""

import asyncio
from app.services.copilot_client import copilot_client, CopilotClientError


async def test_copilot_integration():
    """Test the Copilot integration with a simple prompt."""
    try:
        print("Testing Copilot integration...")
        print(
            "Note: This requires Chrome to be installed and you to be logged into Copilot"
        )

        # Test with a simple prompt
        response = await copilot_client.send_prompt_and_get_response(
            "Hello, can you tell me what 2+2 equals?",
            timeout=30,  # Short timeout for testing
        )

        print(f"✅ Copilot responded: {response[:100]}...")
        return True

    except CopilotClientError as e:
        print(f"❌ Copilot error: {e}")
        if "login" in str(e).lower():
            print(
                "💡 Tip: Make sure you're logged into Microsoft 365 Copilot in Chrome"
            )
        elif "chrome" in str(e).lower():
            print("💡 Tip: Make sure Chrome is installed at the configured path")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Copilot Integration Test")
    print("=" * 50)

    # Run the test
    success = asyncio.run(test_copilot_integration())

    if success:
        print("\n🎉 Integration test passed!")
        print(
            "You can now use: curl -X POST 'http://localhost:8000/v1/process/copilot' -F 'prompt=Your question here'"
        )
    else:
        print("\n⚠️  Integration test failed - see error messages above")
        print("The echo service at /v1/process will still work fine")

    print("=" * 50)
