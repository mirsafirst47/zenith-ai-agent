"""
ZENITH AI AGENT - CLAUDE (ANTHROPIC) INTEGRATION
Use Claude instead of OpenAI for intelligent responses.
"""

import os
from typing import Optional, Dict, List, Any

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ anthropic package not installed. Run: pip install anthropic")


class ClaudeService:
    """Claude API integration for conversation responses"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.model = "claude-sonnet-4-20250514"  # Fast & capable
        # Alternative: "claude-opus-4-1-20250414" for highest quality
        
        if self.api_key and ANTHROPIC_AVAILABLE and self.api_key != "mock":
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    @property
    def is_available(self) -> bool:
        return self.client is not None
    
    async def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        system_prompt: str,
        language: str = "en",
        max_tokens: int = 300
    ) -> str:
        """
        Generate a response using Claude.
        
        Args:
            user_message: The latest user input
            conversation_history: List of {"role": "user/assistant", "content": "..."}
            system_prompt: Instructions for Claude's behavior
            language: Target response language
            max_tokens: Maximum response length
        
        Returns:
            Claude's response text
        """
        if not self.is_available:
            return None
        
        # Build messages for Claude API
        messages = []
        
        # Add conversation history (Claude format)
        for msg in conversation_history[-10:]:  # Last 10 turns
            role = msg.get("role", "user")
            if role in ["user", "assistant"]:
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })
        
        # Add current user message if not already in history
        if not messages or messages[-1].get("content") != user_message:
            messages.append({
                "role": "user",
                "content": user_message
            })
        
        # Ensure messages alternate correctly (Claude requirement)
        messages = self._ensure_alternating_roles(messages)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages
            )
            
            return response.content[0].text
            
        except anthropic.APIError as e:
            print(f"Claude API error: {e}")
            return None
        except Exception as e:
            print(f"Claude error: {e}")
            return None
    
    def _ensure_alternating_roles(self, messages: List[Dict]) -> List[Dict]:
        """Ensure messages alternate between user and assistant"""
        if not messages:
            return messages
        
        cleaned = []
        last_role = None
        
        for msg in messages:
            role = msg.get("role")
            if role != last_role:
                cleaned.append(msg)
                last_role = role
            else:
                # Merge consecutive same-role messages
                if cleaned:
                    cleaned[-1]["content"] += "\n" + msg.get("content", "")
        
        # Claude requires first message to be from user
        if cleaned and cleaned[0].get("role") != "user":
            cleaned = cleaned[1:]
        
        return cleaned
    
    def build_phone_agent_prompt(
        self,
        business_name: str,
        business_info: Dict[str, Any],
        customer_emotion: str,
        preferred_tone: str,
        detected_intent: str,
        collected_entities: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """Build a system prompt optimized for phone agent behavior"""
        
        language_instructions = {
            "en": "Respond in English.",
            "es": "Responde en español. (Respond in Spanish)",
            "fr": "Répondez en français. (Respond in French)",
            "zh": "请用中文回复。(Respond in Mandarin Chinese)",
            "ru": "Отвечайте на русском языке. (Respond in Russian)"
        }
        
        tone_guidance = {
            "empathetic": "Be genuinely understanding. Validate their feelings before solving the problem.",
            "calm": "Stay steady and reassuring. Don't match frustration with frustration.",
            "efficient": "Be concise and action-oriented. They're in a hurry.",
            "enthusiastic": "Be warm and excited to help. Mirror their positive energy.",
            "apologetic": "Sincerely apologize and focus on making things right.",
            "reassuring": "Provide comfort and certainty. Walk them through each step.",
            "professional": "Maintain a courteous, helpful demeanor.",
            "warm": "Be friendly and personable while remaining professional."
        }
        
        prompt = f"""You are a phone agent for {business_name}. You are having a LIVE PHONE CONVERSATION.

CRITICAL RULES:
1. {language_instructions.get(language, language_instructions["en"])}
2. Keep responses SHORT (2-3 sentences max) - this is a phone call, not an essay
3. Sound NATURAL - use conversational language, not formal/robotic
4. NEVER say "I'm an AI" or "As an AI" unless directly asked
5. Ask for ONE piece of information at a time
6. Confirm important details before taking action

CURRENT CONTEXT:
- Customer emotion: {customer_emotion}
- Required tone: {preferred_tone}
- Tone guidance: {tone_guidance.get(preferred_tone, tone_guidance["professional"])}
- Customer intent: {detected_intent}
- Information gathered: {collected_entities if collected_entities else "None yet"}

BUSINESS INFO:
{self._format_business_info(business_info)}

RESPONSE STYLE:
- Start with acknowledgment if customer is frustrated/angry
- Be proactive - suggest relevant options
- Use the customer's name if known
- For bookings: confirm date, time, party size, name before finalizing
- For complaints: empathize first, then solve

Remember: You're speaking to someone on the phone. Be human, warm, and helpful."""
        
        return prompt
    
    def _format_business_info(self, info: Dict) -> str:
        """Format business info for the prompt"""
        if not info:
            return "No specific business information available."
        
        parts = []
        if info.get("hours"):
            parts.append(f"Hours: {info['hours']}")
        if info.get("services"):
            parts.append(f"Services: {', '.join(info['services'][:5])}")
        if info.get("description"):
            parts.append(f"About: {info['description']}")
        if info.get("specials"):
            parts.append(f"Current specials: {info['specials']}")
        
        return "\n".join(parts) if parts else "General business"


# Singleton
claude_service = ClaudeService()


# Convenience function
async def get_claude_response(
    user_message: str,
    conversation_history: List[Dict],
    system_prompt: str,
    language: str = "en"
) -> Optional[str]:
    """Quick function to get Claude response"""
    return await claude_service.generate_response(
        user_message=user_message,
        conversation_history=conversation_history,
        system_prompt=system_prompt,
        language=language
    )
