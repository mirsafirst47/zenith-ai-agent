"""Real Twilio Service for phone calls and SMS"""
from app.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client
    from twilio.twiml.voice_response import VoiceResponse, Gather, Say
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

class TwilioService:
    def __init__(self):
        if TWILIO_AVAILABLE and settings.USE_REAL_TWILIO:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.phone_number = settings.TWILIO_PHONE_NUMBER
            logger.info("✅ Real Twilio Service initialized")
        else:
            self.client = None
            logger.info("📝 Using mock Twilio")
    
    def create_twiml_response(
        self,
        message: str,
        action_url: str,
        language: str = "en",
        gather_config: Optional[dict] = None
    ) -> str:
        """Create TwiML response for Twilio"""
        if not TWILIO_AVAILABLE:
            # Mock TwiML
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" timeout="3" action="{action_url}" method="POST">
        <Say>{message}</Say>
    </Gather>
</Response>"""
        
        response = VoiceResponse()
        
        if gather_config is None:
            gather_config = {
                "input": "speech",
                "timeout": 3,
                "speech_timeout": "auto",
                "language": self._get_twilio_language_code(language),
                "hints": self._get_language_hints(language)
            }
        
        gather = Gather(
            action=action_url,
            method="POST",
            **gather_config
        )
        
        say = Say(
            message,
            voice=self._get_voice(language),
            language=gather_config["language"]
        )
        gather.append(say)
        response.append(gather)
        
        # Fallback if no input
        no_input_msg = self._get_no_input_message(language)
        response.say(no_input_msg, voice=self._get_voice(language))
        response.redirect(action_url)
        
        return str(response)
    
    def create_forward_twiml(self, forward_number: str, message: Optional[str] = None) -> str:
        """Create TwiML to forward call to human"""
        if not TWILIO_AVAILABLE:
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{message or 'Transferring your call'}</Say>
    <Dial>{forward_number}</Dial>
</Response>"""
        
        response = VoiceResponse()
        if message:
            response.say(message, voice="Polly.Joanna")
        response.dial(forward_number)
        return str(response)
    
    def send_sms(self, to_number: str, message: str) -> dict:
        """Send SMS notification"""
        if not self.client:
            logger.info(f"📱 Mock SMS to {to_number}: {message}")
            return {"success": True, "sid": "mock_sms_id", "mock": True}
        
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
            )
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            logger.error(f"SMS error: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_twilio_language_code(self, language: str) -> str:
        """Map language codes to Twilio codes"""
        mapping = {
            "en": "en-US",
            "es": "es-ES",
            "zh": "zh-CN",
            "fr": "fr-FR",
            "ru": "ru-RU"
        }
        return mapping.get(language, "en-US")
    
    def _get_voice(self, language: str) -> str:
        """Get appropriate Polly voice for language"""
        voices = {
            "en": "Polly.Joanna",
            "es": "Polly.Lupe",
            "zh": "Polly.Zhiyu",
            "fr": "Polly.Celine",
            "ru": "Polly.Tatyana"
        }
        return voices.get(language, "Polly.Joanna")
    
    def _get_language_hints(self, language: str) -> str:
        """Provide hints to improve speech recognition"""
        hints_map = {
            "en": "reservation,booking,appointment,table,time,date",
            "es": "reserva,reservación,cita,mesa,hora,fecha",
            "zh": "预订,预约,桌子,时间,日期",
            "fr": "réservation,rendez-vous,table,heure,date",
            "ru": "бронирование,запись,стол,время,дата"
        }
        return hints_map.get(language, "")
    
    def _get_no_input_message(self, language: str) -> str:
        """No input message in each language"""
        messages = {
            "en": "I didn't catch that. Could you please repeat?",
            "es": "No escuché eso. ¿Puede repetir por favor?",
            "zh": "我没听清楚。请您再说一遍好吗？",
            "fr": "Je n'ai pas compris. Pouvez-vous répéter?",
            "ru": "Я не расслышал. Не могли бы вы повторить?"
        }
        return messages.get(language, messages["en"])

twilio_service = TwilioService()
