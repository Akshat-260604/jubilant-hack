from typing import Dict, List, Optional
from fastapi import HTTPException
from pydantic import BaseModel
from utils.document_handling.content_type import CONTENT_HIERARCHY
from services.s3host import current_s3_client
from models.images import image_repo

class ContentFlowQuestion(BaseModel):
    key: str
    question: str
    options: Optional[List[str]] = None
    upload_url: Optional[str] = None
    images: Optional[List[str]] = None

class ContentFlowManager:
    QUESTION_FLOW = [
        {
            "key": "content_format",
            "question": "What type of content do you want to create?",
            "options": list(CONTENT_HIERARCHY.keys())
        },
        {
            "key": "objective",
            "question": "What is your objective?"
        },
        {
            "key": "audience",
            "question": "Who is your target audience?"
        },
        {
            "key": "tone",
            "question": "What tone should the content have?"
        },
        {
            "key": "include_images",
            "question": "Include images from the document?",
            "options": ["Yes", "No"]
        }
    ]

    @staticmethod
    async def augment_question(question: Dict, current_state: Dict) -> ContentFlowQuestion:
        """Augment questions with dynamic options based on previous answers"""
        response = ContentFlowQuestion(
            key=question["key"],
            question=question["question"]
        )

        if question["key"] == "objective":
            content_format = current_state.get("content_format")
            if content_format and content_format in CONTENT_HIERARCHY:
                response.options = list(CONTENT_HIERARCHY[content_format].keys())

        elif question["key"] == "audience":
            content_format = current_state.get("content_format")
            objective = current_state.get("objective")
            if content_format and objective:
                response.options = list(CONTENT_HIERARCHY[content_format][objective].keys())

        elif question["key"] == "tone":
            content_format = current_state.get("content_format")
            objective = current_state.get("objective")
            audience = current_state.get("audience")
            if content_format and objective and audience:
                response.options = CONTENT_HIERARCHY[content_format][objective][audience]

        elif question["key"] == "include_images" and current_state.get("document_id"):
            document_id = current_state.get("document_id")
            if document_id:
                image_ids = await image_repo.get_image_by_document_id(document_id)
                images = []
                for image_id in image_ids:
                    url = await current_s3_client.get_presigned_view_url(f"images/{image_id}")
                    images.append(url)
                response.images = images

        if "options" in question:
            response.options = question["options"]

        return response

    @staticmethod
    async def get_next_question(current_state: Dict[str, str], step_index: Optional[int] = None) -> ContentFlowQuestion:
        """Get next question in the flow"""
        if step_index is not None:
            if 0 <= step_index < len(ContentFlowManager.QUESTION_FLOW):
                return await ContentFlowManager.augment_question(
                    ContentFlowManager.QUESTION_FLOW[step_index], 
                    current_state
                )
            raise HTTPException(status_code=400, detail="Invalid step index")

        # Find next unanswered question
        for question in ContentFlowManager.QUESTION_FLOW:
            if question["key"] not in current_state:
                return await ContentFlowManager.augment_question(question, current_state)

        raise HTTPException(status_code=400, detail="All questions answered")