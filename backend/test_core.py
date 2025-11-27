"""Test core services"""
import asyncio
from app.core.language_detector import language_detector
from app.core.conversation_state import conversation_state
from app.models.database import SessionLocal
from app.models.business import Business

async def test_language_detection():
    print("Testing Language Detection...")
    
    # Test English
    lang = language_detector.detect_from_text("Hello, I would like to make a reservation")
    print(f"✅ English: {lang}")
    
    # Test Spanish
    lang = language_detector.detect_from_text("Hola, quisiera hacer una reserva")
    print(f"✅ Spanish: {lang}")
    
    # Test phone
    lang = language_detector.detect_from_phone("+14155551234")
    print(f"✅ US Phone: {lang}")

async def test_conversation_state():
    print("\nTesting Conversation State...")
    
    # Create session
    session = await conversation_state.create_session(
        call_sid="test_call_123",
        business_id="business_1",
        caller_number="+14155551234"
    )
    print(f"✅ Session created: {session['call_sid']}")
    
    # Add message
    await conversation_state.add_message(
        "test_call_123",
        "user",
        "I want to book a table"
    )
    print("✅ Message added")
    
    # Retrieve session
    retrieved = await conversation_state.get_session("test_call_123")
    print(f"✅ Retrieved {len(retrieved['conversation_history'])} messages")
    
    # Cleanup
    await conversation_state.delete_session("test_call_123")
    print("✅ Session cleaned up")

async def main():
    test_language_detection()
    await test_conversation_state()
    print("\n🎉 All core services working!")

if __name__ == "__main__":
    asyncio.run(main())
