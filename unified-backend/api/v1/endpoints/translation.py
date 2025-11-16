from fastapi import APIRouter
from typing import List
from schemas.chat import TranslationRequest, TranslationResponse, LanguageResponse
from utils.chat.translation_func import RobustTranslator
from utils.chat.language_mapping import LANGUAGE_MAP
router = APIRouter()

@router.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest):
    translator = RobustTranslator(
        source_lang_name='English',
        target_lang_name=request.target_lang
    )
    translated = translator.translate_text(request.text)
    return TranslationResponse(translated_text=translated)

@router.get("/list_of_languages", response_model=List[str])
async def get_languages() -> List[str]:
    """Get list of supported languages"""
    return list(LANGUAGE_MAP.keys())