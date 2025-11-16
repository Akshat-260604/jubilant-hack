from typing import List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """
    Chat request model used by the `/chat` endpoint.

    This matches the schema expected by the frontend:
    - prompt: user question
    - userId: optional user identifier (backend can default if omitted)
    - document_ids: list of document IDs
    - context_id: optional conversation context ID
    """

    prompt: str
    # Make userId optional so clients don't have to send it.
    # If omitted, the backend will use a default anonymous ID.
    userId: Optional[str] = None
    document_ids: List[str]
    context_id: Optional[str] = None


class TranslationRequest(BaseModel):
    text: str
    target_lang: str


class TranslationResponse(BaseModel):
    translated_text: str


class LanguageResponse(BaseModel):
    List[str]


class RephraseRequest(BaseModel):
    text: str
    tone: str


class RephraseResponse(BaseModel):
    rephrased_text: str


class RewriteRequest(BaseModel):
    user_prompt: str


class RewriteResponse(BaseModel):
    enhanced_prompt: str


class ChatHighlightsRequest(BaseModel):
    # userId is not required by the API; kept optional for backward compatibility.
    userId: Optional[str] = None
    document_id: str
    page_number: int
    msg_id: str


class ChatHighlightsResponse(BaseModel):
    presigned_url: str


