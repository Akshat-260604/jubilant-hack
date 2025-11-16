from fastapi import APIRouter, HTTPException
from schemas.base import PromptHeadingResponse, PromptListResponse
from utils.document_handling.prompt_library import PROMPT_LIBRARY

router = APIRouter()



@router.get("/prompt-library/", response_model=PromptHeadingResponse, tags=["Prompt Library"])
def get_prompt_headings():
    return {"headings": list(PROMPT_LIBRARY.keys())}


@router.get("/prompt-library/{heading}", response_model=PromptListResponse, tags=["Prompt Library"])
def get_prompts_for_heading(heading: str):
    if heading not in PROMPT_LIBRARY:
        raise HTTPException(status_code=404, detail="Heading not found.")
    return {
        "heading": heading,
        "prompts": PROMPT_LIBRARY[heading]
    }
