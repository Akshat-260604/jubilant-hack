from fastapi import APIRouter, HTTPException
from utils.chat.text_rephraser import rephrase_text
from schemas.chat import RephraseRequest, RephraseResponse

router = APIRouter()

@router.post("/rephrase",response_model=RephraseResponse)
async def rephrase_endpoint(request: RephraseRequest):
    try:
        rephrased_text = await rephrase_text(
            text=request.text,
            tone=request.tone
        )
        return {"rephrased_text": rephrased_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))