"""
UPDATED INTELLIGENT AGENT - Uses Claude instead of OpenAI
This patches the existing intelligent_agent to prefer Claude.
"""

from app.core.intelligent_agent import IntelligentAgent, intelligent_agent
from app.services.claude_service import claude_service
import os


def patch_intelligent_agent_for_claude():
    """Patch the intelligent agent to use Claude"""
    
    async def _generate_claude_response(self, context, user_text: str) -> str:
        """Generate response using Claude"""
        
        # Build system prompt
        system_prompt = claude_service.build_phone_agent_prompt(
            business_name=context.business_name or "our business",
            business_info=context.business_knowledge,
            customer_emotion=context.detected_emotion.value,
            preferred_tone=context.preferred_tone.value,
            detected_intent=context.detected_intent.value if context.detected_intent else "unknown",
            collected_entities=context.entities,
            language=context.language
        )
        
        # Get conversation history
        history = context.messages[-10:]  # Last 10 messages
        
        # Call Claude
        response = await claude_service.generate_response(
            user_message=user_text,
            conversation_history=history,
            system_prompt=system_prompt,
            language=context.language
        )
        
        if response:
            return response
        
        # Fallback to smart mock if Claude fails
        return await self._generate_smart_response(context, user_text)
    
    # Check if Claude is available
    if claude_service.is_available:
        # Patch the method
        intelligent_agent._generate_llm_response = lambda ctx, text: _generate_claude_response(intelligent_agent, ctx, text)
        intelligent_agent.use_real_llm = True
        print("✅ Intelligent Agent patched to use Claude")
    else:
        print("⚠️ Claude not available - using mock responses")


# Auto-patch on import if API key exists
if os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_API_KEY") != "mock":
    patch_intelligent_agent_for_claude()
