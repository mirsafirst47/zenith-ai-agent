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
from app.integrations.calendar_integration import reservation_manager, make_reservation, lookup_reservation


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
        
        if action == "gather_booking_info":
            return self._prompt_for_booking_info(entities)
        
        if action == "gather_order_info":
            return {"response": "What would you like to order?", "action": "continue", "data": {}}
        
        if action == "process_cancellation":
            return await self._handle_cancellation(session, entities)
        
        return {"response": result.get("response"), "action": "continue", "data": {}}
    
    async def _handle_booking(self, session: CallSession, entities: Dict) -> Dict[str, Any]:
        """Create a booking"""
        try:
            party_size = int(entities.get("party_size", 2))
            name = entities.get("name", "Guest")
            
            # Parse date
            date_str = entities.get("date", "today").lower()
            if date_str == "today":
                booking_date = datetime.now()
            elif date_str == "tomorrow":
                booking_date = datetime.now() + timedelta(days=1)
            else:
                booking_date = datetime.now()
            
            # Parse time
            time_str = entities.get("time", "7:00 PM").upper().replace(" ", "")
            try:
                if "PM" in time_str:
                    hour = int(time_str.replace("PM", "").split(":")[0])
                    if hour != 12:
                        hour += 12
                else:
                    hour = int(time_str.replace("AM", "").split(":")[0])
                minute = int(time_str.split(":")[1][:2]) if ":" in time_str else 0
                booking_time = dt_time(hour, minute)
            except:
                booking_time = dt_time(19, 0)
            
            # Create reservation
            result = await make_reservation(
                business_id=session.business_id,
                customer_phone=session.caller_number,
                customer_name=name,
                date=booking_date,
                time_slot=booking_time,
                party_size=party_size
            )
            
            if result["success"]:
                code = result["confirmation_code"]
                response = f"Wonderful! I've confirmed your reservation for {party_size} on {booking_date.strftime('%A, %B %d')} at {booking_time.strftime('%I:%M %p')} under {name}. Your confirmation number is {code}. Is there anything else?"
                return {"response": response, "action": "booking_confirmed", "data": result["reservation"]}
            else:
                return {"response": f"That time isn't available. {result['message']}. Would you like another time?", "action": "continue", "data": {}}
        
        except Exception as e:
            return {"response": "I'm having trouble with the reservation. What time would you like?", "action": "continue", "data": {"error": str(e)}}
    
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
    
    def _prompt_for_booking_info(self, entities: Dict) -> Dict[str, Any]:
        """Ask for missing booking info"""
        if "party_size" not in entities:
            return {"response": "I'd be happy to help with a reservation. How many people?", "action": "continue", "data": {}}
        if "date" not in entities:
            return {"response": f"Perfect, a table for {entities['party_size']}. What date?", "action": "continue", "data": {}}
        if "time" not in entities:
            return {"response": "Great! What time works best?", "action": "continue", "data": {}}
        if "name" not in entities:
            return {"response": "Wonderful! May I have a name for the reservation?", "action": "continue", "data": {}}
        
        return {"action": "create_booking", "data": entities}
    
    async def _handle_cancellation(self, session: CallSession, entities: Dict) -> Dict[str, Any]:
        """Cancel a reservation"""
        confirmation = entities.get("confirmation_code")
        
        reservation = lookup_reservation(
            confirmation_code=confirmation,
            phone=session.caller_number if not confirmation else None
        )
        
        if reservation:
            from app.integrations.calendar_integration import cancel_reservation
            result = await cancel_reservation(reservation["id"])
            
            if result["success"]:
                return {"response": "I've cancelled your reservation. Anything else I can help with?", "action": "continue", "data": {}}
        
        return {"response": "I couldn't find that reservation. Do you have the confirmation number?", "action": "continue", "data": {}}
    
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
