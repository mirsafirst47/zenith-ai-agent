"""Mock LLM responses for development"""
from typing import Dict, List
import random

class MockLLMService:
    def __init__(self):
        self.responses = {
            "en": [
                "I'd be happy to help you with that. Could you tell me more?",
                "Let me check that information for you.",
                "Of course! What date works best for you?",
                "I understand. Let me assist you with your request."
            ],
            "es": [
                "Con gusto le ayudo con eso. ¿Puede darme más información?",
                "Déjeme verificar esa información para usted.",
                "¡Por supuesto! ¿Qué fecha le conviene?",
                "Entiendo. Permítame ayudarle con su solicitud."
            ]
        }
    
    async def generate_response(
        self,
        conversation_history: List[Dict],
        business_context: Dict,
        language: str = "en",
        intent: str = None
    ) -> Dict:
        """Generate mock AI response"""
        
        # Get last user message
        last_user_msg = ""
        for msg in reversed(conversation_history):
            if msg["role"] == "user":
                last_user_msg = msg["content"].lower()
                break
        
        # Simple intent detection
        detected_intent = "general"
        if any(word in last_user_msg for word in ["book", "reservation", "appointment", "table"]):
            detected_intent = "booking"
        elif any(word in last_user_msg for word in ["cancel", "change"]):
            detected_intent = "cancellation"
        elif any(word in last_user_msg for word in ["complaint", "problem", "issue"]):
            detected_intent = "complaint"
        
        # Generate response
        responses = self.responses.get(language, self.responses["en"])
        response_text = random.choice(responses)
        
        return {
            "text": response_text,
            "intent": detected_intent,
            "action": "continue_conversation",
            "entities": {},
            "confidence": 0.85
        }

mock_llm_service = MockLLMService()
