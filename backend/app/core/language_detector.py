"""Language detection from text and phone number"""
from typing import Optional, Tuple

try:
    import phonenumbers
    PHONENUMBERS_AVAILABLE = True
except ImportError:
    PHONENUMBERS_AVAILABLE = False

try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


class LanguageDetector:
    SUPPORTED = ["en", "es", "zh", "fr", "ru"]
    
    COUNTRY_LANGUAGE = {
        "US": "en", "CA": "en", "GB": "en", "AU": "en",
        "MX": "es", "ES": "es", "AR": "es", "CO": "es", "CL": "es",
        "DO": "es", "PR": "es", "CU": "es", "VE": "es", "PE": "es",
        "CN": "zh", "TW": "zh", "HK": "zh", "SG": "zh",
        "FR": "fr", "BE": "fr", "CH": "fr",
        "RU": "ru", "BY": "ru", "KZ": "ru"
    }
    
    LANGUAGE_KEYWORDS = {
        "es": ["hola", "gracias", "por favor", "buenos", "señor", "quisiera", "quiero", "necesito"],
        "fr": ["bonjour", "merci", "s'il vous plaît", "madame", "monsieur", "je voudrais"],
        "zh": ["你好", "谢谢", "请问", "先生", "女士", "我想"],
        "ru": ["здравствуйте", "спасибо", "пожалуйста", "хочу", "мне нужно"]
    }
    
    def detect_from_phone(self, phone: str) -> str:
        """Detect language from phone number country code"""
        if not PHONENUMBERS_AVAILABLE or not phone:
            return "en"
        
        try:
            parsed = phonenumbers.parse(phone, None)
            country = phonenumbers.region_code_for_number(parsed)
            return self.COUNTRY_LANGUAGE.get(country, "en")
        except:
            return "en"
    
    def detect_from_text(self, text: str) -> Optional[str]:
        """Detect language from spoken text"""
        if not text or len(text) < 3:
            return None
        
        text_lower = text.lower()
        
        # Check keywords first
        for lang, keywords in self.LANGUAGE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return lang
        
        # Use langdetect if available
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text)
                if detected in self.SUPPORTED:
                    return detected
                # Map variants
                if detected.startswith("zh"):
                    return "zh"
            except:
                pass
        
        return "en"
    
    def get_language_name(self, code: str) -> str:
        """Get full language name"""
        names = {
            "en": "English",
            "es": "Spanish", 
            "zh": "Mandarin Chinese",
            "fr": "French",
            "ru": "Russian"
        }
        return names.get(code, "English")


# Singleton
language_detector = LanguageDetector()
