#!/usr/bin/env python3
"""
Test the simulate call endpoint to debug failures
"""

import sys
import os
import asyncio
import traceback

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.models.database import Base, engine, SessionLocal
from app.models.business import Business
from app.models.call import Call


async def test_simulate_call():
    """Test the simulate call flow"""
    print("\n" + "="*60)
    print("🧪 TESTING SIMULATE CALL ENDPOINT")
    print("="*60 + "\n")

    try:
        # Create tables
        print("1️⃣ Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("   ✅ Tables created\n")

        # Get a database session
        db = SessionLocal()

        # Check if a business exists, create one if not
        print("2️⃣ Checking for test business...")
        business = db.query(Business).first()
        if not business:
            print("   Creating test business...")
            business = Business(
                name="Test Restaurant",
                phone_number="+15551234567",
                description="A test restaurant",
                services=["Dining", "Takeout"]
            )
            db.add(business)
            db.commit()
            print(f"   ✅ Business created: {business.name} ({business.phone_number})\n")
        else:
            print(f"   ✅ Found business: {business.name} ({business.phone_number})\n")

        # Import and test the simulate_call function
        print("3️⃣ Testing simulate_call function...")
        from app.api.routes.voice import simulate_call
        from fastapi import Form

        try:
            # Call the simulate_call function
            result = await simulate_call(
                business_phone=business.phone_number,
                caller_number="+14155551234",
                message="I want to make a reservation",
                db=db
            )

            print("   ✅ simulate_call completed\n")
            print("4️⃣ Result:")
            print(f"   Call SID: {result.get('call_sid')}")
            print(f"   Language: {result.get('language')}")
            print(f"   Emotion: {result.get('emotion')}")
            print(f"   Intent: {result.get('intent')}")
            print(f"   Response: {result.get('conversation', [{}])[-1].get('content', 'N/A')[:100]}...\n")

            # Check if call was saved to database
            print("5️⃣ Verifying call was saved...")
            saved_call = db.query(Call).filter(Call.call_sid == result.get('call_sid')).first()
            if saved_call:
                print(f"   ✅ Call found in database")
                print(f"      ID: {saved_call.id}")
                print(f"      Language: {saved_call.detected_language}")
                print(f"      Sentiment: {saved_call.sentiment}")
                print(f"      Intent: {saved_call.intent}")
                print(f"      Business ID: {saved_call.business_id}\n")
            else:
                print("   ❌ Call NOT found in database\n")

            # Check analytics
            print("6️⃣ Checking analytics...")
            from app.api.routes.analytics import get_summary
            analytics = get_summary(db=db, business_id=str(business.id))
            print(f"   ✅ Analytics retrieved")
            print(f"      Total calls: {analytics['total_calls']}")
            print(f"      By language: {analytics['by_language']}")
            print(f"      By intent: {analytics['by_intent']}\n")

            print("="*60)
            print("✅ ALL TESTS PASSED")
            print("="*60 + "\n")

        except Exception as e:
            print(f"   ❌ Error in simulate_call: {e}")
            print(f"\n   Traceback:")
            traceback.print_exc()
            print()

    except Exception as e:
        print(f"❌ Error during setup: {e}")
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_simulate_call())
