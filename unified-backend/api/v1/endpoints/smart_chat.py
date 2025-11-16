from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from lib.hasher import hash_param
from utils.chat.logger import log
from utils.chat.smart_rag_chain import run_smart_rag_chain, search_and_preview_sources
from services.unified_search import unified_search_service

router = APIRouter()

class SmartChatRequest(BaseModel):
    """
    Request model for smart chat with auto-discovery.
    No document_ids needed - system automatically finds relevant documents.
    """
    prompt: str
    userId: str
    context_id: Optional[str] = None
    max_documents: int = 5
    relevance_threshold: float = 0.6

class SearchPreviewRequest(BaseModel):
    """Request model for document search preview."""
    query: str
    userId: str
    max_results: int = 10
    score_threshold: float = 0.6

@router.post("/chat/smart")
async def smart_chat_with_auto_discovery(
    request: SmartChatRequest
) -> StreamingResponse:
    """
    Enhanced chat endpoint with intelligent document auto-discovery.

    Automatically finds and uses relevant documents from both uploaded files
    and Google Drive without requiring users to specify document IDs.

    Args:
        request (SmartChatRequest): Chat request with query and parameters

    Returns:
        StreamingResponse: Streaming chat response with mixed citations
    """
    try:
        prompt = request.prompt
        userId = request.userId
        context_id = request.context_id
        max_documents = request.max_documents
        relevance_threshold = request.relevance_threshold

        # Validate required fields
        if not prompt or not prompt.strip():
            raise HTTPException(status_code=400, detail="prompt is required and cannot be empty")

        if not userId or not userId.strip():
            raise HTTPException(status_code=400, detail="userId is required and cannot be empty")

        # Validate parameters
        if max_documents <= 0 or max_documents > 20:
            raise HTTPException(status_code=400, detail="max_documents must be between 1 and 20")

        if relevance_threshold < 0.0 or relevance_threshold > 1.0:
            raise HTTPException(status_code=400, detail="relevance_threshold must be between 0.0 and 1.0")

        # Hash userId for consistency with existing system
        userId = await hash_param(userId)

        log(f"Smart chat request - User: {userId}, Query: '{prompt[:50]}...', Max docs: {max_documents}")

        # Run smart RAG chain with auto-discovery
        return StreamingResponse(
            run_smart_rag_chain(
                user_query=prompt,
                userId=userId,
                context_id=context_id,
                max_documents=max_documents,
                relevance_threshold=relevance_threshold
            ),
            media_type="text/event-stream"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        error_msg = f"Error in smart chat endpoint: {str(e)}"
        log(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/search/preview")
async def preview_document_sources(request: SearchPreviewRequest):
    """
    Preview what documents would be discovered for a query.

    Useful for debugging and transparency - shows which documents
    the system would use without actually running the full RAG chain.

    Args:
        request (SearchPreviewRequest): Search preview parameters

    Returns:
        dict: Preview of discoverable documents from all sources
    """
    try:
        query = request.query
        userId = request.userId
        max_results = request.max_results
        score_threshold = request.score_threshold

        # Validate required fields
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="query is required and cannot be empty")

        if not userId or not userId.strip():
            raise HTTPException(status_code=400, detail="userId is required and cannot be empty")

        # Validate parameters
        if max_results <= 0 or max_results > 50:
            raise HTTPException(status_code=400, detail="max_results must be between 1 and 50")

        if score_threshold < 0.0 or score_threshold > 1.0:
            raise HTTPException(status_code=400, detail="score_threshold must be between 0.0 and 1.0")

        # Hash userId for consistency
        userId = await hash_param(userId)

        log(f"Search preview request - User: {userId}, Query: '{query[:50]}...', Max results: {max_results}")

        # Get preview of discoverable sources
        preview_data = await search_and_preview_sources(
            query=query,
            max_results=max_results,
            score_threshold=score_threshold
        )

        return {
            "success": True,
            "preview": preview_data,
            "total_sources": preview_data.get("total_found", 0),
            "uploaded_count": preview_data.get("uploaded_documents", {}).get("count", 0),
            "drive_count": preview_data.get("google_drive_documents", {}).get("count", 0)
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        error_msg = f"Error in search preview endpoint: {str(e)}"
        log(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/search/unified")
async def unified_search_endpoint(request: SearchPreviewRequest):
    """
    Direct unified search across all document sources.

    Args:
        request (SearchPreviewRequest): Search parameters

    Returns:
        dict: Detailed search results from all sources
    """
    try:
        query = request.query
        userId = request.userId
        max_results = request.max_results
        score_threshold = request.score_threshold

        # Validate required fields
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="query is required and cannot be empty")

        if not userId or not userId.strip():
            raise HTTPException(status_code=400, detail="userId is required and cannot be empty")

        # Hash userId for consistency
        userId = await hash_param(userId)

        log(f"Unified search request - User: {userId}, Query: '{query[:50]}...', Max results: {max_results}")

        # Perform unified search
        search_results = await unified_search_service.search_all_sources(
            query=query,
            max_results=max_results,
            score_threshold=score_threshold
        )

        # Convert results to serializable format
        serialized_results = [result.to_dict() for result in search_results]

        return {
            "success": True,
            "query": query,
            "total_results": len(serialized_results),
            "score_threshold": score_threshold,
            "results": serialized_results,
            "sources_summary": {
                "uploaded": len([r for r in search_results if r.source_type.value == "uploaded"]),
                "google_drive": len([r for r in search_results if r.source_type.value == "google_drive"])
            }
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        error_msg = f"Error in unified search endpoint: {str(e)}"
        log(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/search/health")
async def unified_search_health():
    """
    Health check for unified search system.

    Returns:
        dict: Health status of unified search components
    """
    try:
        health_status = await unified_search_service.health_check()

        return {
            "success": True,
            "timestamp": "2024-11-13T12:00:00Z",
            "unified_search_status": health_status
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": "2024-11-13T12:00:00Z"
        }