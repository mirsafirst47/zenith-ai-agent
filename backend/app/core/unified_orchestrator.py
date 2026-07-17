"""
ZENITH AI AGENT - UNIFIED ORCHESTRATOR
Ties together all components into one system.
"""

from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta, time as dt_time
from dataclasses import dataclass

from app.core.intelligent_agent import intelligent_agent, get_intelligent_response
from app.core.knowledge_base import knowledge_manager
from app.core.conversation_manager import (
    conversation_manager, start_conversation,
    add_to_conversation, get_conversation_context, end_conversation
)
from app.core.escalation_system import should_escalate
from app.core.language_detector import language_detector
from app.integrations.pos_integration import pos_manager, create_order
from app.db.client import service_client
from app.services.booking_service import create_booking, find_active_booking
from app.services.queue_service import join_queue


@dataclass
class CallSession:
    call_sid: str
    business_id: str
    caller_number: str
    language: str = "en"
    business_data: Dict = None
    is_active: bool = True


class UnifiedAgentOrchestrator:
    """The main orchestrator handling all phone calls"""
    
    def __init__(self):
        self._sessions: Dict[str, CallSession] = {}
    
    async def handle_incoming_call(self, call_sid: str, caller_number: str,
                                    business_phone: str, business_data: Dict = None) -> Tuple[str, str]:
        """Handle new incoming call. Returns (greeting, language)"""
        
        # Detect initial language from phone
        initial_lang = language_detector.detect_from_phone(caller_number)
        print(f"📞 Incoming call from {caller_number} - Initial language: {initial_lang}")
        
        # Get business info
        business_id = business_data.get("id", "default") if business_data else "default"
        
        if business_data:
            knowledge_manager.create_knowledge_base(business_id, business_data)
        
        # Create session
        session = CallSession(
            call_sid=call_sid,
            business_id=business_id,
            caller_number=caller_number,
            language=initial_lang,
            business_data=business_data
        )
        self._sessions[call_sid] = session
        
        # Start conversation tracking
        start_conversation(call_sid, business_id, caller_number, initial_lang)
        
        # Get personalized greeting
        business_name = business_data.get("name", "our business") if business_data else "our business"
        greeting = conversation_manager.get_personalized_greeting(caller_number, business_name, initial_lang)
        
        add_to_conversation(call_sid, "assistant", greeting)
        
        return greeting, initial_lang
    
    async def process_user_input(self, call_sid: str, user_text: str) -> Dict[str, Any]:
        """Process user speech and generate response"""
        
        session = self._sessions.get(call_sid)
        if not session:
            return {
                "response": "I'm sorry, there seems to be a connection issue. Please call back.",
                "action": "end", "data": {}
            }
        
        # Update language detection from speech
        detected_lang = language_detector.detect_from_text(user_text)
        if detected_lang and detected_lang != session.language:
            print(f"📍 Language detected: {session.language} → {detected_lang}")
            print(f"📍 User text: '{user_text}'")
            session.language = detected_lang
        
        # Get intelligent response
        result = await get_intelligent_response(
            call_sid, user_text, session.business_data, session.language
        )
        
        # Add to conversation
        add_to_conversation(
            call_sid, "user", user_text,
            emotion=result.get("emotion"),
            intent=result.get("intent"),
            entities=result.get("entities")
        )
        
        # Check for escalation
        context = get_conversation_context(call_sid)
        should_esc, esc_reason, esc_message = should_escalate({
            "last_message": user_text,
            "all_messages": " ".join(t.get("content", "") for t in context.get("turns", [])),
            "current_emotion": result.get("emotion"),
            "emotion_trajectory": result.get("emotion_trajectory"),
            "turn_count": result.get("turn_count"),
            "messages": context.get("turns", [])
        })
        
        if should_esc:
            return {
                "response": esc_message,
                "action": "escalate",
                "data": {"reason": esc_reason},
                "emotion": result.get("emotion"),
                "intent": result.get("intent")
            }
        
        # Handle specific actions
        action = result.get("suggested_action", "continue_conversation")
        action_result = await self._handle_action(call_sid, action, context, result, session)
        
        response = action_result.get("response", result.get("response"))
        add_to_conversation(call_sid, "assistant", response)
        
        return {
            "response": response,
            "action": action_result.get("action", "continue"),
            "data": action_result.get("data", {}),
            "emotion": result.get("emotion"),
            "intent": result.get("intent")
        }
    
    async def _handle_action(self, call_sid: str, action: str, context: Dict,
                              result: Dict, session: CallSession) -> Dict[str, Any]:
        """Handle specific actions like booking, ordering"""
        
        entities = result.get("entities", {})
        
        if action == "create_booking":
            return await self._handle_booking(session, entities)

        if action == "create_order":
            return await self._handle_order(session, entities)

        if action == "create_queue_hold":
            return await self._handle_queue_hold(session)

        if action == "gather_booking_info":
            return self._prompt_for_booking_info(session, entities)
        
        if action == "gather_order_info":
            return {"response": "What would you like to order?", "action": "continue", "data": {}}
        
        if action == "process_cancellation":
            return await self._handle_cancellation(session, entities)
        
        return {"response": result.get("response"), "action": "continue", "data": {}}
    
    def _parse_scheduled_at(self, entities: Dict) -> datetime:
        """Combine the extracted date/time entities into a datetime."""
        date_str = str(entities.get("date", "today")).lower()
        if date_str == "tomorrow":
            booking_date = datetime.now() + timedelta(days=1)
        else:  # today / tonight / unparsed weekday phrases fall back to today
            booking_date = datetime.now()

        time_str = str(entities.get("time", "7:00 PM")).upper().replace(" ", "")
        try:
            if "PM" in time_str:
                hour = int(time_str.replace("PM", "").split(":")[0])
                if hour != 12:
                    hour += 12
            else:
                hour = int(time_str.replace("AM", "").split(":")[0])
            minute = int(time_str.split(":")[1][:2]) if ":" in time_str else 0
            booking_time = dt_time(hour, minute)
        except Exception:
            booking_time = dt_time(19, 0)

        return datetime.combine(booking_date.date(), booking_time)

    def _match_service_from_conversation(self, session: CallSession, call_sid: str) -> Optional[str]:
        """Find which catalog service the caller mentioned, if any."""
        kb = knowledge_manager.get_knowledge_base(session.business_id)
        if not kb or not kb.catalog:
            return None
        context = get_conversation_context(call_sid)
        spoken = " ".join(
            t.get("content", "")
            for t in context.get("turns", [])
            if t.get("role") == "user"
        )
        item = kb.find_item(spoken)
        return item.name if item else None

    async def _handle_booking(self, session: CallSession, entities: Dict) -> Dict[str, Any]:
        """Create and persist a booking"""
        try:
            name = entities.get("name", "Guest")
            scheduled_at = self._parse_scheduled_at(entities)
            service_type = self._match_service_from_conversation(session, session.call_sid)

            # Capacity: verticals have finite bays/chairs/rooms/tables
            kb = knowledge_manager.get_knowledge_base(session.business_id)
            duration = 60
            if kb:
                item = kb.catalog.get(kb._slug(service_type)) if service_type else None
                if item and item.duration_minutes:
                    duration = item.duration_minutes
                from app.db import repos as _repos
                overlapping = await _repos.count_overlapping_bookings(
                    service_client(),
                    session.business_id,
                    scheduled_at.isoformat(),
                    (scheduled_at + timedelta(minutes=duration)).isoformat(),
                )
                if overlapping >= kb.capacity.max_concurrent:
                    when = scheduled_at.strftime("%I:%M %p")
                    return {
                        "response": (
                            f"I'm sorry, we're fully booked around {when}. "
                            "Is there another time that could work for you?"
                        ),
                        "action": "continue",
                        "data": {"reason": "capacity_full"},
                    }

            is_restaurant = (session.business_data or {}).get("business_type") == "restaurant"
            metadata = {}
            if "party_size" in entities:
                metadata["party_size"] = int(entities["party_size"])

            booking = await create_booking(
                service_client(),
                business_id=session.business_id,
                customer_name=name,
                customer_phone=session.caller_number,
                scheduled_at=scheduled_at.isoformat(),
                service_type=service_type,
                duration_minutes=duration,
                status="confirmed",  # confirmed verbally on the call
                booking_metadata=metadata,
            )
            booking_data = {
                "id": booking["id"],
                "confirmation_code": booking["confirmation_code"],
                "scheduled_at": booking["scheduled_at"],
                "service_type": booking["service_type"],
                "status": booking["status"],
            }

            when = f"{scheduled_at.strftime('%A, %B %d')} at {scheduled_at.strftime('%I:%M %p')}"
            code = booking_data["confirmation_code"]
            if is_restaurant and "party_size" in metadata:
                what = f"your reservation for {metadata['party_size']}"
            elif service_type:
                what = f"your {service_type} appointment"
            else:
                what = "your appointment"
            response = (
                f"Wonderful! I've confirmed {what} on {when} under {name}. "
                f"Your confirmation number is {code}. Is there anything else?"
            )
            return {"response": response, "action": "booking_confirmed", "data": booking_data}

        except Exception as e:
            print(f"⚠️ Booking persistence failed: {e}")
            return {"response": "I'm having trouble with the booking. What time would you like?", "action": "continue", "data": {"error": str(e)}}

    async def _handle_queue_hold(self, session: CallSession) -> Dict[str, Any]:
        """Hold the caller's place in line and let them hang up"""
        try:
            hold, created = await join_queue(service_client(), session.business_id, session.caller_number)
            hold_data = {"id": hold["id"], "position": hold["position"], "status": hold["status"]}

            if created:
                response = (
                    f"You're all set — I've held your place in line. You're number {hold_data['position']}. "
                    "We'll text you at this number when it's your turn, so feel free to hang up."
                )
            else:
                response = (
                    f"You're already in line — still number {hold_data['position']}. "
                    "We'll text you when it's your turn."
                )
            return {"response": response, "action": "queue_hold_created", "data": hold_data}

        except Exception as e:
            print(f"⚠️ Queue hold failed: {e}")
            return {"response": "I'm sorry, I couldn't hold your place just now. Would you like to stay on the line?", "action": "continue", "data": {"error": str(e)}}
    
    async def _handle_order(self, session: CallSession, entities: Dict) -> Dict[str, Any]:
        """Create an order"""
        items = entities.get("items", [])
        
        if not items:
            return {"response": "What would you like to order?", "action": "continue", "data": {}}
        
        try:
            result = await create_order(
                business_id=session.business_id,
                items=items,
                customer_phone=session.caller_number,
                order_type=entities.get("order_type", "pickup")
            )
            
            response = f"Great! Your order total is {result['total_formatted']}. It should be ready in about 20 minutes. Anything else?"
            return {"response": response, "action": "order_confirmed", "data": result}
        
        except Exception as e:
            return {"response": "I'm having trouble with that order. Let me connect you with someone.", "action": "escalate", "data": {}}
    
    def _prompt_for_booking_info(self, session: CallSession, entities: Dict) -> Dict[str, Any]:
        """Ask for missing booking info — one field at a time, in the
        order the business's config asks for them."""
        is_restaurant = (session.business_data or {}).get("business_type") == "restaurant"
        noun = "reservation" if is_restaurant else "appointment"

        kb = knowledge_manager.get_knowledge_base(session.business_id)
        required = kb.booking_fields if kb and kb.booking_fields else ["date", "time", "name"]
        prompts = {
            "party_size": f"I'd be happy to help with a {noun}. How many people?",
            "date": f"I can help with that {noun}. What day works for you?",
            "time": "Great! What time works best?",
            "name": f"Wonderful! May I have a name for the {noun}?",
            "service_type": "Of course — which service would you like to book?",
            "vehicle": "Sure — what's the year, make, and model of your vehicle?",
        }
        for field in required:
            if field not in entities:
                message = prompts.get(field, f"Could I get the {field.replace('_', ' ')} for the {noun}?")
                return {"response": message, "action": "continue", "data": {}}

        return {"action": "create_booking", "data": entities}

    async def _handle_cancellation(self, session: CallSession, entities: Dict) -> Dict[str, Any]:
        """Cancel a persisted booking"""
        confirmation = entities.get("confirmation_code")

        db = service_client()
        booking = await find_active_booking(
            db,
            business_id=session.business_id,
            confirmation_code=confirmation,
            customer_phone=session.caller_number if not confirmation else None,
        )
        if booking:
            from app.db import repos
            await repos.update_booking(db, booking["id"], {"status": "cancelled"})
            return {
                "response": "I've cancelled your booking. Anything else I can help with?",
                "action": "continue",
                "data": {"cancelled_booking_id": booking["id"]},
            }

        return {"response": "I couldn't find that booking. Do you have the confirmation number?", "action": "continue", "data": {}}
    
    async def handle_call_end(self, call_sid: str, outcome: str = "completed"):
        """Handle call ending"""
        session = self._sessions.get(call_sid)
        if not session:
            return
        
        end_conversation(call_sid, outcome)
        intelligent_agent.cleanup_context(call_sid)
        
        if call_sid in self._sessions:
            del self._sessions[call_sid]
    
    def get_session(self, call_sid: str) -> Optional[CallSession]:
        return self._sessions.get(call_sid)


# Singleton
unified_orchestrator = UnifiedAgentOrchestrator()


# Convenience functions
async def handle_incoming_call(call_sid: str, caller_number: str,
                               business_phone: str, business_data: Dict = None) -> Tuple[str, str]:
    return await unified_orchestrator.handle_incoming_call(call_sid, caller_number, business_phone, business_data)


async def process_speech(call_sid: str, user_text: str) -> Dict[str, Any]:
    return await unified_orchestrator.process_user_input(call_sid, user_text)


async def end_call(call_sid: str, outcome: str = "completed"):
    await unified_orchestrator.handle_call_end(call_sid, outcome)
