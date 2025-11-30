#!/usr/bin/env python3
"""
Test script to verify language detection and Claude integration
Run this to diagnose issues with the test call system
"""

import os
import sys
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.language_detector import language_detector
from app.services.claude_service import claude_service
from app.core.intelligent_agent import IntelligentAgent


def test_language_detection():
    """Test language detection with various inputs"""
    print("\n" + "="*60)
    print("🌍 TESTING LANGUAGE DETECTION")
    print("="*60)

    test_cases = [
        ("Hello, I want to make a reservation", "en", "English test"),
        ("Hola, quiero hacer una reserva", "es", "Spanish test"),
        ("Bonjour, je voudrais réserver une table", "fr", "French test"),
        ("你好，我想预订一张桌子", "zh", "Chinese test"),
        ("Привет, я хотел бы зарезервировать стол", "ru", "Russian test"),
        ("+14155551234", "en", "US phone number"),
        ("+34912345678", "es", "Spain phone number"),
        ("+33123456789", "fr", "France phone number"),
    ]

    for text, expected_lang, description in test_cases:
        if text.startswith("+"):
            # Phone number test
            detected = language_detector.detect_from_phone(text)
        else:
            # Text test
            detected = language_detector.detect_from_text(text)

        status = "✅" if detected == expected_lang else "❌"
        print(f"{status} {description}")
        print(f"   Input: {text[:50]}...")
        print(f"   Expected: {expected_lang}, Got: {detected}")
        print()


def test_claude_availability():
    """Check if Claude is available"""
    print("\n" + "="*60)
    print("🤖 TESTING CLAUDE AVAILABILITY")
    print("="*60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    print(f"ANTHROPIC_API_KEY set: {bool(api_key)}")
    if api_key:
        print(f"API key value: {api_key[:20]}..." if len(api_key) > 20 else f"API key value: {api_key}")

    print(f"Claude service available: {claude_service.is_available}")

    if claude_service.is_available:
        print("✅ Claude is ready to use!")
    else:
        print("❌ Claude is not available")
        print("\nTo enable Claude:")
        print("1. Get an API key from https://console.anthropic.com")
        print("2. Set the environment variable: export ANTHROPIC_API_KEY='sk-...'")
        print("3. Install the anthropic package: pip install anthropic")


async def test_intelligent_agent():
    """Test intelligent agent with mock data"""
    print("\n" + "="*60)
    print("🧠 TESTING INTELLIGENT AGENT")
    print("="*60)

    agent = IntelligentAgent()

    print(f"Use Claude: {agent.use_claude}")
    print(f"Use real LLM: {agent.use_real_llm}")

    # Create a context
    call_sid = "TEST_123"
    user_text = "I want to make a reservation"

    try:
        context = agent.get_or_create_context(call_sid, language="en")
        print(f"\n✅ Created context for call: {call_sid}")

        # Simulate business data
        business_data = {
            "id": "rest_123",
            "name": "Test Restaurant",
            "phone_number": "+15551234567",
            "description": "A great restaurant",
            "services": ["Dining", "Takeout"],
            "hours_of_operation": "9am-10pm"
        }

        print(f"✅ Processing test input...")
        result = await agent.process_input(call_sid, user_text, business_data)

        print(f"\nResult:")
        print(f"  Emotion: {result.get('emotion')}")
        print(f"  Intent: {result.get('intent')}")
        print(f"  Tone: {result.get('tone_used')}")
        print(f"  Response: {result.get('response')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("\n")
    print("🔍 ZENITH AI AGENT - SYSTEM TEST")
    print("="*60)

    # Test language detection
    test_language_detection()

    # Test Claude
    test_claude_availability()

    # Test intelligent agent
    asyncio.run(test_intelligent_agent())

    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
