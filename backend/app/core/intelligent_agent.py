"""
ZENITH AI AGENT - INTELLIGENT AGENT BRAIN
The core intelligence for natural, empathetic conversations.
"""

import json
import re
import random
import os
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Try to import Claude service
try:
    from app.services.claude_service import claude_service
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False


class EmotionState(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    CONFUSED = "confused"
    ANXIOUS = "anxious"
    RUSHED = "rushed"
    FRIENDLY = "friendly"
    DISAPPOINTED = "disappointed"
    GRATEFUL = "grateful"


class ConversationTone(Enum):
    PROFESSIONAL = "professional"
    WARM = "warm"
    EMPATHETIC = "empathetic"
    APOLOGETIC = "apologetic"
    ENTHUSIASTIC = "enthusiastic"
    CALM = "calm"
    REASSURING = "reassuring"
    EFFICIENT = "efficient"


class IntentCategory(Enum):
    BOOKING = "booking"
    INQUIRY = "inquiry"
    ORDER = "order"
    COMPLAINT = "complaint"
    MODIFICATION = "modification"
    CANCELLATION = "cancellation"
    GENERAL = "general"
    ESCALATION = "escalation"
    PAYMENT = "payment"
    FEEDBACK = "feedback"


@dataclass
class ConversationContext:
    call_sid: str
    business_id: str
    caller_number: str
    language: str = "en"
    messages: List[Dict[str, str]] = field(default_factory=list)
    detected_intent: Optional[IntentCategory] = None
    detected_emotion: EmotionState = EmotionState.NEUTRAL
    emotion_history: List[EmotionState] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    turn_count: int = 0
    business_name: str = ""
    business_knowledge: Dict[str, Any] = field(default_factory=dict)
    preferred_tone: ConversationTone = ConversationTone.PROFESSIONAL
    started_at: datetime = field(default_factory=datetime.utcnow)


class EmotionDetector:
    """Detects caller emotion from speech"""
    
    EMOTION_INDICATORS = {
        "en": {
            EmotionState.FRUSTRATED: [
                "frustrated", "annoying", "ridiculous", "unacceptable", "terrible",
                "waited", "waiting", "forever", "already told", "how many times"
            ],
            EmotionState.ANGRY: [
                "furious", "angry", "unbelievable", "outrageous", "sue",
                "manager", "supervisor", "complaint", "worst", "never again"
            ],
            EmotionState.CONFUSED: [
                "confused", "don't understand", "what do you mean", "unclear",
                "lost", "huh", "wait what", "i'm not sure"
            ],
            EmotionState.ANXIOUS: [
                "worried", "nervous", "concerned", "urgent", "emergency",
                "asap", "right away", "immediately"
            ],
            EmotionState.RUSHED: [
                "hurry", "quick", "fast", "running late", "no time",
                "just need", "quickly", "brief"
            ],
            EmotionState.HAPPY: [
                "wonderful", "great", "amazing", "perfect", "excellent",
                "thank you so much", "fantastic", "love"
            ],
            EmotionState.GRATEFUL: [
                "thank you", "thanks", "appreciate", "helpful", "grateful"
            ]
        },
        "es": {
            EmotionState.FRUSTRATED: ["frustrado", "molesto", "ridículo", "inaceptable"],
            EmotionState.ANGRY: ["furioso", "enojado", "queja", "gerente"],
            EmotionState.HAPPY: ["maravilloso", "excelente", "perfecto", "gracias"]
        }
    }
    
    def detect(self, text: str, language: str = "en") -> Tuple[EmotionState, float]:
        if not text:
            return EmotionState.NEUTRAL, 0.5
        
        text_lower = text.lower()
        indicators = self.EMOTION_INDICATORS.get(language, self.EMOTION_INDICATORS["en"])
        
        emotion_scores = {}
        for emotion, keywords in indicators.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                emotion_scores[emotion] = score
        
        if not emotion_scores:
            return EmotionState.NEUTRAL, 0.6
        
        top_emotion = max(emotion_scores, key=emotion_scores.get)
        confidence = min(0.95, 0.5 + (emotion_scores[top_emotion] * 0.15))
        
        return top_emotion, confidence
    
    def get_trajectory(self, history: List[EmotionState]) -> str:
        if len(history) < 2:
            return "stable"
        
        weights = {
            EmotionState.ANGRY: 5, EmotionState.FRUSTRATED: 4,
            EmotionState.ANXIOUS: 3, EmotionState.DISAPPOINTED: 2,
            EmotionState.NEUTRAL: 1, EmotionState.HAPPY: 0
        }
        
        recent = history[-3:] if len(history) >= 3 else history
        scores = [weights.get(e, 1) for e in recent]
        
        if scores[-1] < scores[0]:
            return "calming"
        elif scores[-1] > scores[0]:
            return "escalating"
        return "stable"


class ToneAdapter:
    """Adapts response tone based on emotion"""
    
    EMOTION_TO_TONE = {
        EmotionState.ANGRY: ConversationTone.CALM,
        EmotionState.FRUSTRATED: ConversationTone.EMPATHETIC,
        EmotionState.ANXIOUS: ConversationTone.REASSURING,
        EmotionState.RUSHED: ConversationTone.EFFICIENT,
        EmotionState.CONFUSED: ConversationTone.WARM,
        EmotionState.DISAPPOINTED: ConversationTone.APOLOGETIC,
        EmotionState.HAPPY: ConversationTone.ENTHUSIASTIC,
        EmotionState.GRATEFUL: ConversationTone.WARM,
        EmotionState.NEUTRAL: ConversationTone.PROFESSIONAL
    }
    
    TONE_PHRASES = {
        "en": {
            ConversationTone.EMPATHETIC: {
                "ack": ["I completely understand your frustration.", "I can hear that this has been difficult."],
                "trans": ["Let me help make this right.", "I'm going to do everything I can to help."]
            },
            ConversationTone.CALM: {
                "ack": ["I hear you, and I want to help.", "I understand this is upsetting."],
                "trans": ["Here's what we can do.", "Let me take care of this."]
            },
            ConversationTone.REASSURING: {
                "ack": ["Don't worry, we'll get this sorted out.", "Everything is going to be fine."],
                "trans": ["Let me walk you through this.", "I'll make sure this gets handled."]
            },
            ConversationTone.EFFICIENT: {
                "ack": ["Got it.", "Understood."],
                "trans": ["Let me quickly help you with that.", "This will just take a moment."]
            },
            ConversationTone.ENTHUSIASTIC: {
                "ack": ["That's wonderful!", "Fantastic!"],
                "trans": ["I'd be delighted to help!", "Let's make this happen!"]
            },
            ConversationTone.APOLOGETIC: {
                "ack": ["I sincerely apologize.", "I'm truly sorry this happened."],
                "trans": ["Let me see what I can do to make this right."]
            }
        }
    }
    
    def get_tone(self, emotion: EmotionState) -> ConversationTone:
        return self.EMOTION_TO_TONE.get(emotion, ConversationTone.PROFESSIONAL)
    
    def get_acknowledgment(self, tone: ConversationTone, lang: str = "en") -> str:
        phrases = self.TONE_PHRASES.get(lang, self.TONE_PHRASES["en"])
        tone_data = phrases.get(tone, {})
        acks = tone_data.get("ack", ["I understand."])
        return random.choice(acks)
    
    def get_transition(self, tone: ConversationTone, lang: str = "en") -> str:
        phrases = self.TONE_PHRASES.get(lang, self.TONE_PHRASES["en"])
        tone_data = phrases.get(tone, {})
        trans = tone_data.get("trans", ["Let me help you with that."])
        return random.choice(trans)


class EntityExtractor:
    """Extracts structured info from conversation"""
    
    PATTERNS = {
        "party_size": [
            r"(?:for\s+)?(\d+)\s*(?:people|persons|guests|of us)",
            r"table\s+(?:for\s+)?(\d+)",
            r"party\s+of\s+(\d+)"
        ],
        "time": [
            r"(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))",
            r"at\s+(\d{1,2}(?::\d{2})?)"
        ],
        "date": [
            r"(today|tomorrow|tonight)",
            r"(this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
            r"(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))"
        ],
        "name": [
            r"(?:name\s+is|i'm|this\s+is|under)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
        ]
    }
    
    def extract_all(self, text: str) -> Dict[str, Any]:
        entities = {}
        for entity_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities[entity_type] = match.group(1)
                    break
        return entities


class IntelligentAgent:
    """Main intelligent agent orchestrating all components"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.emotion_detector = EmotionDetector()
        self.tone_adapter = ToneAdapter()
        self.entity_extractor = EntityExtractor()
        self.contexts: Dict[str, ConversationContext] = {}

        self.openai_client = None
        self.claude_service = None
        self.use_real_llm = False
        self.use_claude = False

        # Try Claude first
        if CLAUDE_AVAILABLE and claude_service.is_available:
            self.claude_service = claude_service
            self.use_real_llm = True
            self.use_claude = True
            print("✅ IntelligentAgent initialized with Claude")
        # Fallback to OpenAI
        elif openai_api_key and OPENAI_AVAILABLE and openai_api_key != "mock":
            self.openai_client = AsyncOpenAI(api_key=openai_api_key)
            self.use_real_llm = True
            print("✅ IntelligentAgent initialized with OpenAI")
        else:
            print("⚠️  IntelligentAgent will use mock responses (no LLM available)")
    
    def get_or_create_context(self, call_sid: str, business_id: str = "", 
                              caller_number: str = "", language: str = "en") -> ConversationContext:
        if call_sid not in self.contexts:
            self.contexts[call_sid] = ConversationContext(
                call_sid=call_sid, business_id=business_id,
                caller_number=caller_number, language=language
            )
        return self.contexts[call_sid]
    
    def update_context_with_business(self, context: ConversationContext, business_data: Dict):
        context.business_name = business_data.get("name", "")
        context.business_knowledge = {
            "hours": business_data.get("hours_of_operation", {}),
            "services": business_data.get("services", []),
            "description": business_data.get("description", "")
        }
    
    async def process_input(self, call_sid: str, user_text: str,
                           business_data: Optional[Dict] = None) -> Dict[str, Any]:
        context = self.get_or_create_context(call_sid)
        
        if business_data:
            self.update_context_with_business(context, business_data)
        
        # Detect emotion
        emotion, confidence = self.emotion_detector.detect(user_text, context.language)
        context.detected_emotion = emotion
        context.emotion_history.append(emotion)
        
        # Extract entities
        new_entities = self.entity_extractor.extract_all(user_text)
        context.entities.update(new_entities)
        
        # Detect intent
        intent = self._detect_intent(user_text, context)
        context.detected_intent = intent
        
        # Get tone
        tone = self.tone_adapter.get_tone(emotion)
        context.preferred_tone = tone
        
        # Add to history
        context.messages.append({"role": "user", "content": user_text})
        context.turn_count += 1
        
        # Generate response
        if self.use_real_llm:
            response = await self._generate_llm_response(context, user_text)
        else:
            response = await self._generate_smart_response(context, user_text)
        
        context.messages.append({"role": "assistant", "content": response})
        
        # Determine action
        action = self._determine_action(context, intent)
        follow_up = self._get_follow_up_needs(context, intent)
        
        return {
            "response": response,
            "emotion": emotion.value,
            "emotion_confidence": confidence,
            "emotion_trajectory": self.emotion_detector.get_trajectory(context.emotion_history),
            "intent": intent.value if intent else "unknown",
            "entities": context.entities,
            "suggested_action": action,
            "follow_up_needed": follow_up,
            "tone_used": tone.value,
            "turn_count": context.turn_count
        }
    
    def _detect_intent(self, text: str, context: ConversationContext) -> IntentCategory:
        text_lower = text.lower()
        
        signals = {
            IntentCategory.BOOKING: ["reservation", "book", "table", "reserve", "appointment"],
            IntentCategory.ORDER: ["order", "want", "like to have", "can i get", "i'll have"],
            IntentCategory.CANCELLATION: ["cancel", "don't need", "remove"],
            IntentCategory.MODIFICATION: ["change", "modify", "update", "reschedule"],
            IntentCategory.COMPLAINT: ["complaint", "problem", "issue", "wrong", "bad"],
            IntentCategory.INQUIRY: ["what time", "when", "where", "how much", "hours", "menu"],
            IntentCategory.ESCALATION: ["manager", "supervisor", "speak to someone", "real person"]
        }
        
        for intent, keywords in signals.items():
            if any(kw in text_lower for kw in keywords):
                return intent
        
        return context.detected_intent or IntentCategory.GENERAL
    
    def _get_follow_up_needs(self, context: ConversationContext, intent: IntentCategory) -> List[str]:
        if intent == IntentCategory.BOOKING:
            required = ["party_size", "date", "time", "name"]
            return [f for f in required if f not in context.entities]
        return []
    
    def _determine_action(self, context: ConversationContext, intent: IntentCategory) -> str:
        if intent == IntentCategory.ESCALATION:
            return "escalate_to_human"
        
        if intent == IntentCategory.BOOKING:
            required = ["party_size", "date", "time", "name"]
            if all(k in context.entities for k in required):
                return "create_booking"
            return "gather_booking_info"
        
        if intent == IntentCategory.ORDER:
            return "gather_order_info" if "items" not in context.entities else "create_order"
        
        if intent == IntentCategory.CANCELLATION:
            return "process_cancellation"
        
        return "continue_conversation"
    
    async def _generate_llm_response(self, context: ConversationContext, user_text: str) -> str:
        # Try Claude first
        if self.use_claude and self.claude_service:
            print(f"🤖 Claude: Generating response for language '{context.language}'")
            system_prompt = claude_service.build_phone_agent_prompt(
                business_name=context.business_name or "our business",
                business_info=context.business_knowledge,
                customer_emotion=context.detected_emotion.value,
                preferred_tone=context.preferred_tone.value,
                detected_intent=context.detected_intent.value if context.detected_intent else "unknown",
                collected_entities=context.entities,
                language=context.language
            )

            response = await self.claude_service.generate_response(
                user_message=user_text,
                conversation_history=context.messages[-10:],
                system_prompt=system_prompt,
                language=context.language
            )

            if response:
                print(f"✅ Claude response generated: {response[:100]}...")
                return response
            else:
                print("⚠️ Claude returned empty response, falling back")

        # Fallback to OpenAI
        if self.openai_client:
            system_prompt = self._build_system_prompt(context)
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(context.messages[-10:])

            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    max_tokens=250,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"OpenAI error: {e}")
                return await self._generate_smart_response(context, user_text)

        # Fallback to mock responses
        return await self._generate_smart_response(context, user_text)
    
    def _build_system_prompt(self, context: ConversationContext) -> str:
        return f"""You are a phone agent for {context.business_name or 'a business'}.

EMOTION: Customer is {context.detected_emotion.value}. Use {context.preferred_tone.value} tone.
INTENT: {context.detected_intent.value if context.detected_intent else 'unknown'}
INFO GATHERED: {json.dumps(context.entities) if context.entities else 'None'}

RULES:
- Never say you're an AI unless asked
- Be natural, warm, efficient
- Ask for ONE piece of info at a time
- Keep responses brief (2-3 sentences for phone)
- Confirm before finalizing actions"""
    
    async def _generate_smart_response(self, context: ConversationContext, user_text: str) -> str:
        tone = context.preferred_tone
        lang = context.language
        intent = context.detected_intent
        response_parts = []
        
        # Add acknowledgment for negative emotions
        if context.detected_emotion in [EmotionState.ANGRY, EmotionState.FRUSTRATED]:
            response_parts.append(self.tone_adapter.get_acknowledgment(tone, lang))
            response_parts.append(self.tone_adapter.get_transition(tone, lang))
        
        # Intent-specific response
        if intent == IntentCategory.BOOKING:
            response_parts.append(self._booking_response(context))
        elif intent == IntentCategory.ORDER:
            response_parts.append("I can help you place an order. What would you like to have?")
        elif intent == IntentCategory.INQUIRY:
            response_parts.append(self._inquiry_response(context, user_text))
        elif intent == IntentCategory.CANCELLATION:
            response_parts.append("I can help with that cancellation. Could you provide the name or confirmation number?")
        elif intent == IntentCategory.COMPLAINT:
            response_parts.append("I'm sorry to hear that. I want to make this right. Could you tell me more?")
        elif intent == IntentCategory.ESCALATION:
            response_parts.append("I understand. Let me connect you with a manager right away. Please hold.")
        else:
            response_parts.append("I'd be happy to help you. How can I assist you today?")
        
        return " ".join(filter(None, response_parts))
    
    def _booking_response(self, context: ConversationContext) -> str:
        e = context.entities
        
        if "party_size" not in e:
            return "I'd be happy to help with a reservation. How many people will be in your party?"
        if "date" not in e:
            return f"Perfect, a table for {e['party_size']}. What date were you thinking?"
        if "time" not in e:
            return f"Great! And what time works best for you?"
        if "name" not in e:
            return "Wonderful! May I have a name for the reservation?"
        
        return f"Let me confirm: {e['party_size']} guests on {e['date']} at {e['time']} under {e['name']}. Is that correct?"
    
    def _inquiry_response(self, context: ConversationContext, text: str) -> str:
        text_lower = text.lower()
        kb = context.business_knowledge
        
        if any(w in text_lower for w in ["hour", "open", "close"]):
            hours = kb.get("hours", {})
            if hours:
                return f"We're open during our regular hours. Is there a specific day you'd like to know about?"
            return "Let me check our hours for you."
        
        if any(w in text_lower for w in ["menu", "serve", "food"]):
            return "We have a great selection. What type of dish are you in the mood for?"
        
        return "I'd be happy to help with that. Could you tell me more about what you're looking for?"
    
    def cleanup_context(self, call_sid: str):
        if call_sid in self.contexts:
            del self.contexts[call_sid]


# Singleton
intelligent_agent = IntelligentAgent()


async def get_intelligent_response(call_sid: str, user_text: str,
                                   business_data: Optional[Dict] = None,
                                   language: str = "en") -> Dict[str, Any]:
    context = intelligent_agent.get_or_create_context(call_sid, language=language)
    return await intelligent_agent.process_input(call_sid, user_text, business_data)
