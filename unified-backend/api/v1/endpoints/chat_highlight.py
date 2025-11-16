from utils.chat.logger import log
from services.s3host import current_s3_client
from models.conversation import conversation_repo
from fastapi import APIRouter, HTTPException
from schemas.chat import ChatHighlightsRequest, ChatHighlightsResponse
from services.document_encoder import DocumentEncoder
import asyncio

router = APIRouter()


@router.post("/chat-highlights", response_model=ChatHighlightsResponse)
async def get_chat_highlights(
    request: ChatHighlightsRequest,
):
    try:
        document_id = request.document_id
        page_number = request.page_number
        msg_id = request.msg_id

        if document_id is None or document_id.strip() == "" or page_number <= 0 or msg_id is None or msg_id.strip() == "":
            message = "document_id, page_number and msg_id are all required fields"
            log(message)
            raise HTTPException(status_code=400, detail=message)

        # Derive document name from encoded document_id; no userId check required.
        _, document_name, _ = DocumentEncoder.decode_document_id(document_id)

        try_count = 0
        status = "pending"
        while status == "pending" and try_count < 30:
            try_count += 1
            status = await conversation_repo.get_highlight_status(request.msg_id, request.document_id, request.page_number)
            log(f'status for {document_name} is {status}')
            if status == "pending":
                await asyncio.sleep(5)

        if status == "done":
            try:
                TARGET_KEY = f"ChatHighlights/{msg_id}/{document_name}/Page_{page_number}.png"
                presigned_url = await current_s3_client.get_presigned_view_url(TARGET_KEY)
                return ChatHighlightsResponse(presigned_url=presigned_url)
            except Exception as e:
                message = f"Error while fetching highlights: {str(e)}"
                log(message)
                raise HTTPException(status_code=500, detail=message)
        else:
            message = "Were not able to generate highlights"
            log(message)
            raise HTTPException(status_code=500, detail=message)

    except HTTPException as e:
        raise e
    except Exception as e:
        message = f"Error while fetching highlights: {str(e)}"
        log(message)
        raise HTTPException(status_code=500, detail=message)