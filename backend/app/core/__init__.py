"""ZENITH AI AGENT - CORE MODULES"""

from .language_detector import language_detector
from .intelligent_agent import intelligent_agent, get_intelligent_response
from .knowledge_base import knowledge_manager, create_sample_knowledge_base
from .conversation_manager import (
    conversation_manager, start_conversation,
    add_to_conversation, get_conversation_context, end_conversation
)
from .escalation_system import escalation_system, should_escalate
from .unified_orchestrator import (
    unified_orchestrator, handle_incoming_call,
    process_speech, end_call
)

__all__ = [
    "language_detector",
    "intelligent_agent", "get_intelligent_response",
    "knowledge_manager", "create_sample_knowledge_base",
    "conversation_manager", "start_conversation",
    "add_to_conversation", "get_conversation_context", "end_conversation",
    "escalation_system", "should_escalate",
    "unified_orchestrator", "handle_incoming_call", "process_speech", "end_call"
]
