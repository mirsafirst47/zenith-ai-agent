from app.services.mock_redis import mock_redis_client
from app.config import settings
from datetime import datetime
from enum import Enum
import json

class ConversationPhase(Enum):
    GREETING = "greeting"
    INTENT_DETECTION = "intent_detection"
    INFORMATION_GATHERING = "information_gathering"
    ACTION_EXECUTION = "action_execution"
    CONFIRMATION = "confirmation"
    CLOSING = "closing"

class ConversationState:
    def __init__(self):
        self.client = mock_redis_client
        self.ttl = 3600
    
    async def create_session(self, call_sid, business_id, caller_number):
        session = {
            "call_sid": call_sid,
            "business_id": business_id,
            "caller_number": caller_number,
            "phase": ConversationPhase.GREETING.value,
            "detected_language": "en",
            "intent": None,
            "entities": {},
            "conversation_history": [],
            "created_at": datetime.utcnow().isoformat()
        }
        await self.client.setex(f"conv:{call_sid}", self.ttl, json.dumps(session))
        return session
    
    async def get_session(self, call_sid):
        data = await self.client.get(f"conv:{call_sid}")
        return json.loads(data) if data else None
    
    async def update_session(self, call_sid, updates):
        session = await self.get_session(call_sid)
        if session:
            session.update(updates)
            await self.client.setex(f"conv:{call_sid}", self.ttl, json.dumps(session))
        return session
    
    async def add_message(self, call_sid, role, content, metadata=None):
        session = await self.get_session(call_sid)
        if session:
            session["conversation_history"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            })
            await self.client.setex(f"conv:{call_sid}", self.ttl, json.dumps(session))
        return session
    
    async def set_language(self, call_sid, language):
        return await self.update_session(call_sid, {"detected_language": language})
    
    async def set_intent(self, call_sid, intent, confidence):
        return await self.update_session(call_sid, {"intent": intent, "intent_confidence": confidence})
    
    async def get_conversation_history(self, call_sid):
        session = await self.get_session(call_sid)
        if not session:
            return []
        history = session.get("conversation_history", [])
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]
    
    async def delete_session(self, call_sid):
        await self.client.delete(f"conv:{call_sid}")

conversation_state = ConversationState()
