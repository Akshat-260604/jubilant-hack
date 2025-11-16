from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from pydantic import BaseModel
from utils.document_handling.content_generation import content_generator
from utils.document_handling.question_flow import ContentFlowManager, ContentFlowQuestion
from schemas.base import ContentGenerationRequest, ContentGenerationResponse
from utils.document_handling.logger import log

router = APIRouter()

class StateRequest(BaseModel):
    current_state: Dict[str, str]
    step_index: Optional[int] = None

@router.post("/content-flow", response_model=ContentFlowQuestion)
async def get_next_question(request: StateRequest):
    """Handle the content generation flow step by step"""
    try:
        return await ContentFlowManager.get_next_question(
            current_state=request.current_state,
            step_index=request.step_index
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        log(f"Error in content flow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-content", response_model=ContentGenerationResponse)
async def generate_content(request: ContentGenerationRequest):
    """
    Generate content based on the completed flow state.

    Args:
        request (ContentGenerationRequest): The request containing all necessary parameters for content generation.

    Returns:
        ContentGenerationResponse: The generated content and associated image paths.

    Raises:
        HTTPException: If content generation fails or an error occurs.
    """
    try:
        result = await content_generator.generate_content(
            content_format=request.content_format,
            objective=request.objective,
            audience=request.audience,
            tone=request.tone,
            text=request.text,
            image_paths=request.image_paths
        )

        return result 

    except HTTPException as e:
        raise e
    except Exception as e:
        log(f"Error in generate_content endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Content generation failed: {str(e)}"
        )