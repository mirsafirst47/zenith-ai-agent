"""Language detection from text and phone number"""
from typing import Optional
import phonenumbers

try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    print("⚠️  langdetect not installed - using basic detection")

class LanguageDetector:
    LANGUAGE_MAP = {
        "en": "English",
        "es": "Spanish",
        "zh": "Mandarin Chinese",
        "fr": "French",
        "ru": "Russian"
    }
    
    COUNTRY_LANGUAGE = {
        "US": "en", "CA": "en", "GB": "en", "AU": "en",
        "MX": "es", "ES": "es", "AR": "es", "CO": "es", "CL": "es",
        "DO": "es", "PR": "es", "CU": "es", "VE": "es", "PE": "es",
        "CN": "zh", "TW": "zh", "HK": "zh", "SG": "zh",
        "FR": "fr", "BE": "fr", "CH": "fr", "CA": "fr",
        "RU": "ru", "BY": "ru", "KZ": "ru"
    }
    
    # Simple keyword detection for when langdetect isn't available
    LANGUAGE_KEYWORDS = {
        "es": ["hola", "gracias", "por favor", "buenos", "señor", "quisiera"],
        "fr": ["bonjour", "merci", "s'il vous plaît", "madame", "monsieur"],
        "zh": ["你好", "谢谢", "请问", "先生", "女士"],
        "ru": ["здравствуйте", "спасибо", "пожалуйста"]
    }
    
    def __init__(self):
        self.supported_languages = ["en", "es", "zh", "fr", "ru"]
    
    def detect_from_text(self, text: str) -> Optional[str]:
        """Detect language from spoken text"""
        if not text or len(text) < 3:
            return None
        
        text_lower = text.lower()
        
        # Try langdetect if available
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text)
                if detected.startswith("zh"):
                    detected = "zh"
                if detected in self.supported_languages:
                    return detected
            except:
                pass
        
        # Fallback: keyword matching
        for lang, keywords in self.LANGUAGE_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                return lang
        
        # Default to English if no match
        return "en"
    
    def detect_from_phone(self, phone_number: str) -> Optional[str]:
        """Detect language from phone number country code"""
        try:
            parsed = phonenumbers.parse(phone_number, None)
            country = phonenumbers.region_code_for_number(parsed)
            return self.COUNTRY_LANGUAGE.get(country, "en")
        except:
            return "en"
    
    def detect_language(
        self, 
        text: Optional[str] = None, 
        phone_number: Optional[str] = None,
        business_default: str = "en"
    ) -> str:
        """Multi-strategy language detection"""
        if text:
            lang = self.detect_from_text(text)
            if lang:
                return lang
        
        if phone_number:
            lang = self.detect_from_phone(phone_number)
            if lang and lang in self.supported_languages:
                return lang
        
        return business_default if business_default in self.supported_languages else "en"

language_detector = LanguageDetector()
