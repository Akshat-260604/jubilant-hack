from fastapi import APIRouter, HTTPException
from schemas.chat import RewriteRequest, RewriteResponse
from utils.chat.ai_rewrite import enhance_user_query

router = APIRouter()


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_user_prompt(request: RewriteRequest):
    """
    Endpoint to enhance (rewrite) a user prompt using LLM.
    """
    try:
        enhanced_prompt = await enhance_user_query(request.user_prompt)
        return RewriteResponse(enhanced_prompt=enhanced_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))