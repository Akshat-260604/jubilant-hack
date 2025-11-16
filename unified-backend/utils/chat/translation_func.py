from deep_translator import MyMemoryTranslator, GoogleTranslator
from .language_mapping import LANGUAGE_MAP

class RobustTranslator:
    """A robust translation class that attempts multiple translation services.
    
    This class provides fallback mechanisms between different translation services
    to ensure more reliable translation results.
    """
    
    def __init__(self, source_lang_name: str = 'English', target_lang_name: str = 'Italian'):
        """Initialize the translator with source and target languages.
        
        Args:
            source_lang_name (str): Name of the source language (default: 'English')
            target_lang_name (str): Name of the target language (default: 'Italian')
        """
        self.source_lang = LANGUAGE_MAP.get(source_lang_name, 'en-us')
        self.target_lang = LANGUAGE_MAP.get(target_lang_name, 'it-IT')

    def translate_text(self, text: str) -> str:
        """Translate the given text using multiple translation services.
        
        Args:
            text (str): The text to translate
            
        Returns:
            str: The translated text if successful, error message if all services fail
            
        Note:
            Attempts translation first with MyMemoryTranslator, then falls back to
            GoogleTranslator if the first attempt fails.
        """
        # Try MyMemoryTranslator as primary service
        try:
            return MyMemoryTranslator(source=self.source_lang, target=self.target_lang).translate(text)
        except Exception as e:
            print(f"⚠️ MyMemory failed: {e}")

        # Fallback to GoogleTranslator with base language codes
        try:
            source_base = get_base_lang_code(self.source_lang)
            target_base = get_base_lang_code(self.target_lang)
            return GoogleTranslator(source=source_base, target=target_base).translate(text)
        except Exception as e:
            print(f"⚠️ GoogleTranslator failed: {e}")

        return "❌ All translators failed."

def get_base_lang_code(lang_code: str) -> str:
    """Extract the base language code from a locale-specific code.
    
    Args:
        lang_code (str): The language code (e.g., 'en-US', 'pt-BR')
        
    Returns:
        str: The base language code (e.g., 'en', 'pt')
        
    Example:
        >>> get_base_lang_code('en-US')
        'en'
    """
    return lang_code.split('-')[0]
