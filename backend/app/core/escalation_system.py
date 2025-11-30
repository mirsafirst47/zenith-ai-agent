"""
ZENITH AI AGENT - SMART ESCALATION SYSTEM
Determines when to transfer calls to human agents.
"""

from typing import Optional, Dict, List, Tuple
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field


class EscalationReason(Enum):
    CUSTOMER_REQUEST = "customer_requested"
    ANGER_THRESHOLD = "anger_threshold_exceeded"
    FRUSTRATION_ESCALATING = "frustration_escalating"
    CONVERSATION_STUCK = "conversation_going_in_circles"
    LEGAL_MENTION = "legal_or_media_threat"
    FINANCIAL_DISPUTE = "financial_dispute"
    SAFETY_CONCERN = "safety_concern"
    COMPLEX_COMPLAINT = "complex_complaint"


class EscalationUrgency(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EscalationContext:
    call_sid: str
    customer_phone: str
    reason: EscalationReason
    urgency: EscalationUrgency
    conversation_summary: str
    customer_emotion: str
    key_points: List[str] = field(default_factory=list)
    
    def to_agent_briefing(self) -> str:
        return f"""
=== ESCALATION BRIEFING ===
Reason: {self.reason.value}
Urgency: {self.urgency.name}
Customer: {self.customer_phone}
Emotion: {self.customer_emotion}

Summary: {self.conversation_summary}

Key Points:
{chr(10).join(f'• {p}' for p in self.key_points)}
===========================
"""


class SmartEscalationSystem:
    """Determines when to escalate to human"""
    
    # Explicit escalation phrases
    ESCALATION_PHRASES = [
        "speak to a human", "talk to someone", "real person",
        "manager", "supervisor", "not a robot", "actual person",
        "transfer me", "connect me", "not helping", "useless"
    ]
    
    # Legal/threat phrases
    THREAT_PHRASES = [
        "lawsuit", "sue you", "lawyer", "attorney", "legal action",
        "contact the media", "news", "social media", "yelp",
        "better business bureau", "bbb", "report you"
    ]
    
    # Financial dispute phrases
    FINANCIAL_PHRASES = [
        "refund", "money back", "charged twice", "overcharged",
        "wrong amount", "fraud", "dispute", "chargeback"
    ]
    
    # Safety phrases
    SAFETY_PHRASES = [
        "allergic reaction", "sick", "food poisoning", "hospital",
        "emergency", "hurt", "injured", "dangerous"
    ]
    
    def __init__(self):
        self.escalation_threshold = 0.6
    
    def evaluate(self, context: Dict) -> Tuple[bool, Optional[EscalationReason], EscalationUrgency, float]:
        """
        Evaluate if escalation is needed.
        Returns: (should_escalate, reason, urgency, confidence)
        """
        last_message = context.get("last_message", "").lower()
        all_messages = context.get("all_messages", "").lower()
        emotion = context.get("current_emotion", "neutral")
        trajectory = context.get("emotion_trajectory", "stable")
        turn_count = context.get("turn_count", 0)
        
        score = 0.0
        reason = None
        urgency = EscalationUrgency.LOW
        
        # Check explicit request (highest priority)
        if any(phrase in last_message for phrase in self.ESCALATION_PHRASES):
            return True, EscalationReason.CUSTOMER_REQUEST, EscalationUrgency.HIGH, 1.0
        
        # Check threats (critical)
        if any(phrase in all_messages for phrase in self.THREAT_PHRASES):
            return True, EscalationReason.LEGAL_MENTION, EscalationUrgency.CRITICAL, 1.0
        
        # Check safety (critical)
        if any(phrase in all_messages for phrase in self.SAFETY_PHRASES):
            return True, EscalationReason.SAFETY_CONCERN, EscalationUrgency.CRITICAL, 1.0
        
        # Check financial dispute
        if any(phrase in all_messages for phrase in self.FINANCIAL_PHRASES):
            score += 0.4
            reason = EscalationReason.FINANCIAL_DISPUTE
            urgency = EscalationUrgency.HIGH
        
        # Check emotion
        if emotion == "angry":
            score += 0.4
            reason = reason or EscalationReason.ANGER_THRESHOLD
            urgency = max(urgency, EscalationUrgency.HIGH)
        elif emotion == "frustrated":
            score += 0.2
            reason = reason or EscalationReason.FRUSTRATION_ESCALATING
        
        # Check trajectory
        if trajectory == "escalating":
            score += 0.3
            urgency = max(urgency, EscalationUrgency.MEDIUM)
        
        # Check conversation length (stuck?)
        if turn_count > 10:
            score += 0.2
            reason = reason or EscalationReason.CONVERSATION_STUCK
        
        should_escalate = score >= self.escalation_threshold
        return should_escalate, reason, urgency, min(score, 1.0)
    
    def get_escalation_message(self, reason: EscalationReason, language: str = "en") -> str:
        """Get message to tell customer during escalation"""
        messages = {
            "en": {
                EscalationReason.CUSTOMER_REQUEST: 
                    "I understand you'd like to speak with someone directly. Let me connect you with a team member right now. Please hold for just a moment.",
                EscalationReason.ANGER_THRESHOLD:
                    "I can hear this has been frustrating. Let me connect you with a manager who can help. One moment please.",
                EscalationReason.LEGAL_MENTION:
                    "I understand the seriousness of your concern. Let me connect you with management immediately. Please hold.",
                EscalationReason.FINANCIAL_DISPUTE:
                    "I want to make sure your payment concern is handled correctly. Let me connect you with our billing team.",
                EscalationReason.SAFETY_CONCERN:
                    "Your safety is our top priority. Let me immediately connect you with a manager.",
                EscalationReason.CONVERSATION_STUCK:
                    "I think this deserves personal attention. Let me connect you with someone who can help directly.",
                EscalationReason.COMPLEX_COMPLAINT:
                    "I want your concerns fully addressed. Let me connect you with someone who can give this proper attention.",
                EscalationReason.FRUSTRATION_ESCALATING:
                    "I can tell this hasn't been the experience you expected. Let me get you to someone who can help."
            },
            "es": {
                EscalationReason.CUSTOMER_REQUEST:
                    "Entiendo que desea hablar con alguien. Permítame conectarle con un miembro del equipo. Un momento por favor.",
                EscalationReason.ANGER_THRESHOLD:
                    "Entiendo su frustración. Permítame conectarle con un gerente. Un momento."
            }
        }
        
        lang_messages = messages.get(language, messages["en"])
        return lang_messages.get(reason, "Let me connect you with a team member. Please hold.")


# Singleton
escalation_system = SmartEscalationSystem()


def should_escalate(context: Dict) -> Tuple[bool, Optional[str], str]:
    """
    Simple interface to check escalation.
    Returns: (should_escalate, reason_string, escalation_message)
    """
    should, reason, urgency, score = escalation_system.evaluate(context)
    
    if should and reason:
        message = escalation_system.get_escalation_message(reason, context.get("language", "en"))
        return True, reason.value, message
    
    return False, None, ""
