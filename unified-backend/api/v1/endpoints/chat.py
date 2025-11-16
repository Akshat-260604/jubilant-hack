from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from utils.chat.logger import log
from utils.chat.single_doc_rag_chain import run_single_document_rag_chain
from schemas.chat import ChatRequest
from models.doc import doc_repo

router = APIRouter()


@router.post("/chat")
async def chat_with_document(
    request: ChatRequest,
) -> StreamingResponse:
    """
    Endpoint for streaming chat responses based on document context.
    Args:
        request (ChatRequest): The chat request containing document IDs, prompt, and other parameters
        api_key (str): API key for authentication
    Returns:
        StreamingResponse: Server-sent events stream of response chunks
    """
    try:
        prompt = request.prompt
        userId = request.userId or "anonymous"
        document_ids = request.document_ids
        context_id = request.context_id

        if prompt is None or prompt.strip() == "":
            message = "prompt is a required field"
            log(message)
            raise HTTPException(status_code=400, detail=message)

        if not document_ids or len(document_ids) == 0:
            message = "At least one document ID is required"
            log(message)
            raise HTTPException(status_code=400, detail=message)

        # Basic validation for document IDs; we no longer enforce per-user authorization
        for document_id in document_ids:
            if document_id is None or document_id.strip() == "":
                message = "document_id in list can't be null or empty string"
                log(message)
                raise HTTPException(status_code=400, detail=message)

        return StreamingResponse(
            run_single_document_rag_chain(
                document_ids=document_ids,
                userId=userId,
                user_query=prompt,
                context_id=context_id,
            ),
            media_type="text/event-stream",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        message = f"Error in chat endpoint: {str(e)}"
        log(message)
        raise HTTPException(status_code=500, detail=message)