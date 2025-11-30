"""
ZENITH AI AGENT - ADVANCED CONVERSATION MANAGER
Long-term memory, preference learning, multi-call context.
"""

import json
import hashlib
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class CustomerTier(Enum):
    NEW = "new"
    RETURNING = "returning"
    REGULAR = "regular"
    VIP = "vip"


@dataclass
class CustomerPreference:
    category: str  # dietary, seating, timing
    preference: str
    confidence: float
    learned_from: str
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CustomerProfile:
    """Long-term customer profile"""
    phone_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    tier: CustomerTier = CustomerTier.NEW
    first_contact: datetime = field(default_factory=datetime.utcnow)
    last_contact: datetime = field(default_factory=datetime.utcnow)
    total_calls: int = 0
    total_bookings: int = 0
    total_orders: int = 0
    preferences: List[CustomerPreference] = field(default_factory=list)
    preferred_language: str = "en"
    past_interactions: List[Dict] = field(default_factory=list)
    special_notes: List[str] = field(default_factory=list)
    
    def add_preference(self, category: str, preference: str, confidence: float, call_sid: str):
        for pref in self.preferences:
            if pref.category == category:
                if confidence >= pref.confidence:
                    pref.preference = preference
                    pref.confidence = confidence
                    pref.learned_from = call_sid
                    pref.last_updated = datetime.utcnow()
                return
        
        self.preferences.append(CustomerPreference(
            category=category, preference=preference,
            confidence=confidence, learned_from=call_sid
        ))
    
    def get_preference(self, category: str) -> Optional[str]:
        for pref in self.preferences:
            if pref.category == category and pref.confidence >= 0.5:
                return pref.preference
        return None
    
    def update_tier(self):
        if self.total_bookings >= 10 or self.total_orders >= 20:
            self.tier = CustomerTier.VIP
        elif self.total_bookings >= 3 or self.total_orders >= 5:
            self.tier = CustomerTier.REGULAR
        elif self.total_calls >= 2:
            self.tier = CustomerTier.RETURNING
    
    def add_interaction(self, interaction_type: str, summary: str, outcome: str):
        self.past_interactions.append({
            "date": datetime.utcnow().isoformat(),
            "type": interaction_type,
            "summary": summary,
            "outcome": outcome
        })
        self.past_interactions = self.past_interactions[-20:]
        self.last_contact = datetime.utcnow()
        self.total_calls += 1
    
    def to_summary(self) -> str:
        parts = []
        if self.name:
            parts.append(f"Name: {self.name}")
        parts.append(f"Tier: {self.tier.value}")
        parts.append(f"Interactions: {self.total_calls}")
        
        if self.preferences:
            prefs = [f"{p.category}: {p.preference}" for p in self.preferences[:3]]
            parts.append(f"Preferences: {', '.join(prefs)}")
        
        return " | ".join(parts)


@dataclass
class ConversationTurn:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    emotion: Optional[str] = None
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    
    def to_message(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ConversationThread:
    """Conversation with intelligent context management"""
    call_sid: str
    business_id: str
    customer_phone: str
    language: str = "en"
    
    turns: List[ConversationTurn] = field(default_factory=list)
    context_summary: str = ""
    
    current_intent: Optional[str] = None
    current_emotion: str = "neutral"
    emotion_history: List[str] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    key_points: List[str] = field(default_factory=list)
    
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    context_window_size: int = 10
    
    def add_turn(self, role: str, content: str, emotion: str = None,
                 intent: str = None, entities: Dict = None):
        turn = ConversationTurn(
            role=role, content=content, emotion=emotion,
            intent=intent, entities=entities or {}
        )
        self.turns.append(turn)
        self.last_activity = datetime.utcnow()
        
        if emotion:
            self.current_emotion = emotion
            self.emotion_history.append(emotion)
        if intent:
            self.current_intent = intent
        if entities:
            self.entities.update(entities)
        
        if role == "user":
            self._extract_key_points(content)
        
        if len(self.turns) > self.context_window_size * 2:
            self._summarize_old_turns()
    
    def _extract_key_points(self, content: str):
        content_lower = content.lower()
        
        if any(w in content_lower for w in ["want", "need", "looking for"]):
            self.key_points.append(f"Request: {content[:50]}")
        if any(w in content_lower for w in ["problem", "issue", "wrong"]):
            self.key_points.append(f"Issue: {content[:50]}")
        
        self.key_points = self.key_points[-10:]
    
    def _summarize_old_turns(self):
        if len(self.turns) <= self.context_window_size:
            return
        
        old_turns = self.turns[:-self.context_window_size]
        intents = list(set(t.intent for t in old_turns if t.intent))
        
        if intents:
            self.context_summary = f"Topics: {', '.join(intents)}"
        
        self.turns = self.turns[-self.context_window_size:]
    
    def get_context_for_llm(self) -> List[Dict[str, str]]:
        messages = []
        if self.context_summary:
            messages.append({"role": "system", "content": f"Previous context: {self.context_summary}"})
        messages.extend([t.to_message() for t in self.turns[-self.context_window_size:]])
        return messages
    
    def get_missing_info(self) -> List[str]:
        if self.current_intent == "booking":
            required = ["party_size", "date", "time", "name"]
            return [f for f in required if f not in self.entities]
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_sid": self.call_sid,
            "business_id": self.business_id,
            "customer_phone": self.customer_phone,
            "turns": [{"role": t.role, "content": t.content, "emotion": t.emotion} for t in self.turns],
            "context_summary": self.context_summary,
            "current_intent": self.current_intent,
            "current_emotion": self.current_emotion,
            "emotion_history": self.emotion_history,
            "entities": self.entities,
            "key_points": self.key_points
        }


class PreferenceLearner:
    """Learns preferences from conversation"""
    
    DIETARY = {
        "vegetarian": ["vegetarian", "no meat", "meatless"],
        "vegan": ["vegan", "no animal", "plant-based"],
        "gluten-free": ["gluten-free", "no gluten", "celiac"],
        "halal": ["halal"],
        "kosher": ["kosher"]
    }
    
    SEATING = {
        "booth": ["booth", "private"],
        "outdoor": ["outside", "outdoor", "patio"],
        "quiet": ["quiet", "peaceful"],
        "window": ["window", "view"]
    }
    
    def learn_from_message(self, message: str, call_sid: str) -> List[Tuple[str, str, float]]:
        learned = []
        msg_lower = message.lower()
        
        for pref, patterns in self.DIETARY.items():
            if any(p in msg_lower for p in patterns):
                learned.append(("dietary", pref, 0.9))
                break
        
        for pref, patterns in self.SEATING.items():
            if any(p in msg_lower for p in patterns):
                learned.append(("seating", pref, 0.7))
                break
        
        return learned


class AdvancedConversationManager:
    """Central manager for conversations and customer memory"""
    
    def __init__(self):
        self._threads: Dict[str, ConversationThread] = {}
        self._profiles: Dict[str, CustomerProfile] = {}
        self.preference_learner = PreferenceLearner()
    
    def _get_profile_key(self, phone: str) -> str:
        return hashlib.md5(phone.encode()).hexdigest()
    
    def get_or_create_thread(self, call_sid: str, business_id: str,
                             customer_phone: str, language: str = "en") -> ConversationThread:
        if call_sid not in self._threads:
            self._threads[call_sid] = ConversationThread(
                call_sid=call_sid, business_id=business_id,
                customer_phone=customer_phone, language=language
            )
        return self._threads[call_sid]
    
    def get_thread(self, call_sid: str) -> Optional[ConversationThread]:
        return self._threads.get(call_sid)
    
    def get_or_create_profile(self, phone: str) -> CustomerProfile:
        key = self._get_profile_key(phone)
        if key not in self._profiles:
            self._profiles[key] = CustomerProfile(phone_number=phone)
        return self._profiles[key]
    
    def get_profile(self, phone: str) -> Optional[CustomerProfile]:
        return self._profiles.get(self._get_profile_key(phone))
    
    def add_message(self, call_sid: str, role: str, content: str,
                    emotion: str = None, intent: str = None, entities: Dict = None):
        thread = self._threads.get(call_sid)
        if not thread:
            return
        
        thread.add_turn(role, content, emotion, intent, entities)
        
        if role == "user":
            learned = self.preference_learner.learn_from_message(content, call_sid)
            profile = self.get_or_create_profile(thread.customer_phone)
            for category, preference, confidence in learned:
                profile.add_preference(category, preference, confidence, call_sid)
    
    def get_full_context(self, call_sid: str) -> Dict[str, Any]:
        thread = self._threads.get(call_sid)
        if not thread:
            return {}
        
        context = thread.to_dict()
        profile = self.get_profile(thread.customer_phone)
        
        if profile:
            context["customer_profile"] = {
                "name": profile.name,
                "tier": profile.tier.value,
                "preferences": [{"category": p.category, "preference": p.preference} for p in profile.preferences],
                "total_interactions": profile.total_calls,
                "summary": profile.to_summary()
            }
        
        return context
    
    def end_conversation(self, call_sid: str, outcome: str):
        thread = self._threads.get(call_sid)
        if not thread:
            return
        
        profile = self.get_or_create_profile(thread.customer_phone)
        
        if "name" in thread.entities and not profile.name:
            profile.name = thread.entities["name"]
        
        summary = thread.current_intent or "general inquiry"
        profile.add_interaction("call", summary, outcome)
        profile.update_tier()
        
        if thread.current_intent == "booking" and outcome == "completed":
            profile.total_bookings += 1
        elif thread.current_intent == "order" and outcome == "completed":
            profile.total_orders += 1
        
        if call_sid in self._threads:
            del self._threads[call_sid]
    
    def get_personalized_greeting(self, phone: str, business_name: str, language: str = "en") -> str:
        profile = self.get_profile(phone)
        
        greetings = {
            "en": {
                "new": f"Thank you for calling {business_name}. How can I help you today?",
                "returning": f"Welcome back to {business_name}! Great to hear from you again. How can I help?",
                "regular": f"Hello! Welcome back to {business_name}. How can I assist you today?",
                "vip": f"Hello! Wonderful to hear from one of our valued guests. How can I help at {business_name}?",
                "named": "Hello {name}! Welcome back to " + business_name + ". How can I help?"
            },
            "es": {
                "new": f"Gracias por llamar a {business_name}. ¿En qué puedo ayudarle?",
                "returning": f"¡Bienvenido de nuevo a {business_name}! ¿En qué puedo ayudarle?"
            }
        }
        
        lang_greetings = greetings.get(language, greetings["en"])
        
        if not profile:
            return lang_greetings["new"]
        
        if profile.name and profile.tier in [CustomerTier.REGULAR, CustomerTier.VIP]:
            return lang_greetings.get("named", lang_greetings["returning"]).format(name=profile.name)
        
        return lang_greetings.get(profile.tier.value, lang_greetings["new"])


# Singleton
conversation_manager = AdvancedConversationManager()


# Convenience functions
def start_conversation(call_sid: str, business_id: str, customer_phone: str, 
                       language: str = "en") -> ConversationThread:
    return conversation_manager.get_or_create_thread(call_sid, business_id, customer_phone, language)


def add_to_conversation(call_sid: str, role: str, content: str, **kwargs):
    conversation_manager.add_message(call_sid, role, content, **kwargs)


def get_conversation_context(call_sid: str) -> Dict[str, Any]:
    return conversation_manager.get_full_context(call_sid)


def end_conversation(call_sid: str, outcome: str = "completed"):
    conversation_manager.end_conversation(call_sid, outcome)
