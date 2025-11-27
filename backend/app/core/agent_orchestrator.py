"""Main orchestrator for AI agent logic"""
from typing import Dict, Optional, Tuple
from app.core.conversation_state import conversation_state, ConversationPhase
from app.core.language_detector import language_detector
from app.prompts.system_prompts import get_system_prompt
from app.models.database import get_db
from app.models.business import Business
from sqlalchemy.orm import Session
from app.config import settings

# Import appropriate LLM service
if settings.USE_REAL_OPENAI:
    try:
        from app.services.llm_service import llm_service
    except ImportError:
        from app.services.mock_llm import mock_llm_service as llm_service
else:
    from app.services.mock_llm import mock_llm_service as llm_service

class AgentOrchestrator:
    """Main orchestrator for AI agent logic"""
    
    def __init__(self):
        self.escalation_keywords = [
            # English
            "manager", "supervisor", "human", "person", "representative",
            "speak to someone", "talk to someone", "real person",
            # Spanish
            "gerente", "supervisor", "humano", "persona", "representante",
            # French
            "responsable", "superviseur", "humain", "personne",
            # Chinese
            "经理", "主管", "人工", "真人",
            # Russian
            "менеджер", "руководитель", "человек", "оператор"
        ]
    
    async def handle_incoming_call(
        self,
        call_sid: str,
        caller_number: str,
        business_phone: str,
        db: Session
    ) -> Tuple[str, str]:
        """Handle new incoming call"""
        business = db.query(Business).filter(
            Business.phone_number == business_phone
        ).first()
        
        if not business or not business.is_active:
            return ("We're sorry, this number is not available at the moment.", "en")
        
        # Create conversation session
        await conversation_state.create_session(call_sid, str(business.id), caller_number)
        
        # Detect initial language from phone number
        initial_language = language_detector.detect_from_phone(caller_number)
        await conversation_state.set_language(call_sid, initial_language)
        
        # Get greeting
        greeting = self._get_greeting(business, initial_language)
        
        # Add to history
        await conversation_state.add_message(call_sid, "assistant", greeting)
        
        return (greeting, initial_language)
    
    async def process_user_speech(
        self,
        call_sid: str,
        speech_text: str,
        db: Session
    ) -> Tuple[str, Optional[str]]:
        """Process user's speech and generate response"""
        session = await conversation_state.get_session(call_sid)
        if not session:
            return ("I'm sorry, I lost our conversation context. Can you repeat that?", None)
        
        # Detect/confirm language
        detected_lang = language_detector.detect_from_text(speech_text)
        if detected_lang and detected_lang != session.get("detected_language"):
            await conversation_state.set_language(call_sid, detected_lang)
            session["detected_language"] = detected_lang
        
        current_language = session.get("detected_language", "en")
        
        # Add user message to history
        await conversation_state.add_message(call_sid, "user", speech_text)
        
        # Check for escalation keywords
        if self._should_escalate(speech_text):
            await conversation_state.flag_escalation(call_sid, "user_requested_human")
            return (self._get_escalation_message(current_language), "escalate")
        
        # Get business context
        business = db.query(Business).filter(
            Business.id == session["business_id"]
        ).first()
        
        business_context = self._build_business_context(business)
        
        # Get conversation history
        history = await conversation_state.get_conversation_history(call_sid)
        
        # Generate AI response
        llm_response = await llm_service.generate_response(
            conversation_history=history,
            business_context=business_context,
            language=current_language,
            intent=session.get("intent")
        )
        
        # Update intent if detected
        if llm_response["intent"] and llm_response["intent"] != "general":
            await conversation_state.set_intent(
                call_sid, 
                llm_response["intent"],
                llm_response["confidence"]
            )
        
        # Add AI response to history
        await conversation_state.add_message(
            call_sid, 
            "assistant", 
            llm_response["text"],
            metadata={
                "intent": llm_response["intent"],
                "action": llm_response["action"],
                "confidence": llm_response["confidence"]
            }
        )
        
        # Determine action
        action = None
        if llm_response["action"] == "escalate":
            action = "escalate"
        elif llm_response["action"] == "book_appointment":
            action = "book"
        elif llm_response["action"] == "cancel_booking":
            action = "cancel"
        
        return (llm_response["text"], action)
    
    def _get_greeting(self, business: Business, language: str) -> str:
        """Get appropriate greeting based on language"""
        greetings = business.greeting_message or {}
        
        default_greetings = {
            "en": f"Thank you for calling {business.name}. How may I help you today?",
            "es": f"Gracias por llamar a {business.name}. ¿Cómo puedo ayudarle hoy?",
            "zh": f"感谢致电{business.name}。我能为您做什么？",
            "fr": f"Merci d'avoir appelé {business.name}. Comment puis-je vous aider?",
            "ru": f"Спасибо за звонок в {business.name}. Как я могу вам помочь?"
        }
        
        return greetings.get(language, default_greetings.get(language, default_greetings["en"]))
    
    def _should_escalate(self, text: str) -> bool:
        """Check if text contains escalation keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.escalation_keywords)
    
    def _get_escalation_message(self, language: str) -> str:
        """Get escalation message in appropriate language"""
        messages = {
            "en": "Of course, let me connect you with someone who can help. Please hold for just a moment.",
            "es": "Por supuesto, permítame conectarlo con alguien que pueda ayudarle. Por favor espere un momento.",
            "zh": "当然，让我为您转接可以帮助您的人。请稍等片刻。",
            "fr": "Bien sûr, laissez-moi vous mettre en relation avec quelqu'un qui peut vous aider.",
            "ru": "Конечно, позвольте мне соединить вас с тем, кто может помочь."
        }
        return messages.get(language, messages["en"])
    
    def _build_business_context(self, business: Business) -> Dict:
        """Build business context for LLM"""
        return {
            "name": business.name,
            "description": business.description,
            "hours_of_operation": business.hours_of_operation or {},
            "services": business.services or [],
            "faq": business.faq or [],
            "phone_number": business.phone_number
        }

agent_orchestrator = AgentOrchestrator()
