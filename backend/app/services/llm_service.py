"""Real OpenAI LLM Service - Activates when USE_REAL_OPENAI=true"""
from typing import Dict, List, Optional
from app.config import settings
from app.prompts.system_prompts import get_system_prompt
import json
import logging

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed - using mock service")

class LLMService:
    def __init__(self):
        if OPENAI_AVAILABLE and settings.USE_REAL_OPENAI:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "gpt-4-turbo-preview"
            logger.info("✅ Real OpenAI LLM Service initialized")
        else:
            self.client = None
            logger.info("📝 Using mock LLM responses")
    
    async def generate_response(
        self,
        conversation_history: List[Dict],
        business_context: Dict,
        language: str = "en",
        intent: Optional[str] = None
    ) -> Dict:
        """Generate AI response"""
        
        # If not using real OpenAI, use mock
        if not self.client:
            from app.services.mock_llm import mock_llm_service
            return await mock_llm_service.generate_response(
                conversation_history, business_context, language, intent
            )
        
        try:
            system_prompt = get_system_prompt(
                business_context=business_context,
                language=language,
                intent=intent
            )
            
            messages = [
                {"role": "system", "content": system_prompt}
            ] + conversation_history
            
            # Call OpenAI with function calling
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "extract_intent_and_action",
                            "description": "Extract user intent and required action",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "intent": {
                                        "type": "string",
                                        "enum": ["booking", "inquiry", "complaint", "cancellation", "modification", "general"]
                                    },
                                    "action": {
                                        "type": "string",
                                        "enum": ["book_appointment", "answer_question", "escalate", "cancel_booking", "modify_booking", "continue_conversation"]
                                    },
                                    "entities": {"type": "object"},
                                    "confidence": {"type": "number"}
                                },
                                "required": ["intent", "action", "confidence"]
                            }
                        }
                    }
                ]
            )
            
            message = response.choices[0].message
            
            # Check if function was called
            if message.tool_calls:
                function_args = json.loads(message.tool_calls[0].function.arguments)
                return {
                    "text": message.content or "",
                    "intent": function_args.get("intent"),
                    "action": function_args.get("action"),
                    "entities": function_args.get("entities", {}),
                    "confidence": function_args.get("confidence", 0.8)
                }
            
            return {
                "text": message.content,
                "intent": intent or "general",
                "action": "continue_conversation",
                "confidence": 0.7
            }
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            # Fallback to mock
            from app.services.mock_llm import mock_llm_service
            return await mock_llm_service.generate_response(
                conversation_history, business_context, language, intent
            )

llm_service = LLMService()
