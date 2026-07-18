"""Persistent session store for live calls.

The conversational core keeps its fast in-memory objects (CallSession,
ConversationContext, ConversationManager threads) — this module
write-throughs their combined state to the agent_sessions table after
every turn and hydrates them back on a cache miss, so:

- a backend restart mid-call loses nothing,
- webhook requests can land on any instance (no sticky sessions).

Serialization is explicit field-by-field: enums stored by value,
datetimes as ISO strings. If hydration ever fails we fall back to a
fresh session rather than crash a live call.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db.client import service_client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def serialize_state(session, context, conversation: Optional[Dict] = None) -> Dict[str, Any]:
    """Combine orchestrator session + agent context (+ manager thread)
    into one JSON-safe dict."""
    return {
        "session": {
            "call_sid": session.call_sid,
            "business_id": session.business_id,
            "caller_number": session.caller_number,
            "language": session.language,
            "business_data": session.business_data,
            "is_active": session.is_active,
        },
        "context": {
            "language": context.language,
            "messages": context.messages,
            "detected_intent": context.detected_intent.value if context.detected_intent else None,
            "detected_emotion": context.detected_emotion.value,
            "emotion_history": [e.value for e in context.emotion_history],
            "entities": context.entities,
            "turn_count": context.turn_count,
            "business_name": context.business_name,
            "business_type": context.business_type,
            "business_knowledge": context.business_knowledge,
            "preferred_tone": context.preferred_tone.value,
            "started_at": context.started_at.isoformat(),
        },
        "conversation": conversation or {},
    }


async def save(call_sid: str, business_id: Optional[str], state: Dict[str, Any]) -> None:
    """Upsert this call's state. Failures are logged, never raised —
    persistence must not take down a live call."""
    try:
        db = service_client()
        await db.from_("agent_sessions").upsert(
            {
                "call_sid": call_sid,
                "business_id": business_id or None,
                "state": state,
            },
            on_conflict="call_sid",
        ).execute()
    except Exception as e:
        print(f"⚠️ Session persist failed for {call_sid}: {e}")


async def load(call_sid: str) -> Optional[Dict[str, Any]]:
    """Fetch a call's persisted state, honoring expiry."""
    try:
        db = service_client()
        res = (
            await db.from_("agent_sessions")
            .select("state,expires_at")
            .eq("call_sid", call_sid)
            .gt("expires_at", _now_iso())
            .execute()
        )
        return res.data[0]["state"] if res.data else None
    except Exception as e:
        print(f"⚠️ Session load failed for {call_sid}: {e}")
        return None


async def delete(call_sid: str) -> None:
    try:
        db = service_client()
        await db.from_("agent_sessions").delete().eq("call_sid", call_sid).execute()
    except Exception as e:
        print(f"⚠️ Session delete failed for {call_sid}: {e}")


def hydrate_into_memory(call_sid: str, state: Dict[str, Any]):
    """Rebuild the in-memory objects from persisted state. Returns the
    rebuilt CallSession or None if the payload is unusable."""
    try:
        from app.core.unified_orchestrator import CallSession, unified_orchestrator
        from app.core.intelligent_agent import (
            ConversationContext, ConversationTone, EmotionState, IntentCategory,
            intelligent_agent,
        )

        s = state.get("session") or {}
        c = state.get("context") or {}
        if not s.get("call_sid"):
            return None

        session = CallSession(
            call_sid=s["call_sid"],
            business_id=s.get("business_id", ""),
            caller_number=s.get("caller_number", ""),
            language=s.get("language", "en"),
            business_data=s.get("business_data"),
            is_active=s.get("is_active", True),
        )
        unified_orchestrator._sessions[call_sid] = session

        context = ConversationContext(
            call_sid=call_sid,
            business_id=s.get("business_id", ""),
            caller_number=s.get("caller_number", ""),
            language=c.get("language", session.language),
        )
        context.messages = c.get("messages", [])
        context.detected_intent = IntentCategory(c["detected_intent"]) if c.get("detected_intent") else None
        context.detected_emotion = EmotionState(c.get("detected_emotion", "neutral"))
        context.emotion_history = [EmotionState(e) for e in c.get("emotion_history", [])]
        context.entities = c.get("entities", {})
        context.turn_count = c.get("turn_count", 0)
        context.business_name = c.get("business_name", "")
        context.business_type = c.get("business_type", "")
        context.business_knowledge = c.get("business_knowledge", {})
        context.preferred_tone = ConversationTone(c.get("preferred_tone", "professional"))
        if c.get("started_at"):
            try:
                context.started_at = datetime.fromisoformat(c["started_at"])
            except ValueError:
                pass
        intelligent_agent.contexts[call_sid] = context

        # Rebuild the knowledge base for this business on this instance
        if session.business_data:
            from app.core.knowledge_base import knowledge_manager
            if not knowledge_manager.get_knowledge_base(session.business_id):
                knowledge_manager.create_knowledge_base(session.business_id, session.business_data)

        return session
    except Exception as e:
        print(f"⚠️ Session hydrate failed for {call_sid}: {e}")
        return None
