import asyncio
from typing import List, Dict, Optional, AsyncGenerator
import logging
from time import time

from services.unified_search import unified_search_service, DocumentSource
from services.s3host import current_s3_client
from utils.chat.stream_final_answer import stream_final_answer
from utils.chat.logger import log
from models.conversation import conversation_repo

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_smart_rag_chain(
    user_query: str,
    userId: str,
    context_id: Optional[str] = None,
    max_documents: int = 5,
    relevance_threshold: float = 0.6
) -> AsyncGenerator[str, None]:
    """
    Run an intelligent RAG chain that automatically discovers relevant documents
    from both uploaded files and Google Drive without user specification.

    Args:
        user_query (str): The user's question
        userId (str): User identifier
        context_id (Optional[str]): Conversation context ID
        max_documents (int): Maximum number of documents to auto-discover
        relevance_threshold (float): Minimum relevance score for document selection

    Yields:
        str: Streamed response chunks with mixed citations
    """
    start_time = time()

    try:
        log(f"Starting smart RAG for query: '{user_query[:100]}...'")

        # Step 1: Auto-discover relevant documents from all sources
        uploaded_doc_ids, drive_doc_ids = await unified_search_service.get_relevant_document_ids(
            query=user_query,
            max_docs=max_documents,
            score_threshold=relevance_threshold
        )

        all_document_ids = uploaded_doc_ids + drive_doc_ids

        if not all_document_ids:
            # If no documents found, yield a helpful message
            yield "I couldn't find any relevant documents in your uploaded files or Google Drive that relate to your question. Please ensure you have uploaded relevant documents or check that the Google Drive integration is properly configured."
            return

        log(f"Auto-discovered {len(uploaded_doc_ids)} uploaded docs and {len(drive_doc_ids)} Drive docs")

        # Step 2: Get mixed context from both sources
        mixed_context = await unified_search_service.format_mixed_context(
            query=user_query,
            max_chunks=20,
            score_threshold=relevance_threshold
        )

        if not mixed_context.strip():
            yield "While I found some potentially relevant documents, I couldn't extract sufficient context to answer your question. Please try rephrasing your question or check if the documents contain the information you're looking for."
            return

        # Step 3: Prepare document data for processing (including Drive documents)
        pdf_datas = await _prepare_mixed_document_data(uploaded_doc_ids, drive_doc_ids)

        # Step 4: Handle conversation context
        if not context_id or context_id == "":
            context_id = await conversation_repo.create_conversation(all_document_ids)

        # Step 5: Stream the enhanced response with mixed citations
        log(f"Streaming smart RAG response with {len(all_document_ids)} documents")

        async for chunk in stream_final_answer(
            context_id=context_id,
            userId=userId,
            document_ids=all_document_ids,
            context=mixed_context,
            pdf_datas=pdf_datas,
            pdf_count=len(all_document_ids),
            user_query=user_query
        ):
            if "[DONE]" not in chunk:
                yield chunk
                await asyncio.sleep(0.05)

        elapsed_time = time() - start_time
        log(f"Smart RAG completed in {elapsed_time:.2f} seconds")

    except Exception as e:
        error_msg = f"Error in smart RAG chain: {str(e)}"
        log(error_msg)
        logger.error(error_msg)
        yield f"I encountered an error while processing your question: {str(e)}. Please try again or contact support if the issue persists."

async def _prepare_mixed_document_data(uploaded_doc_ids: List[str], drive_doc_ids: List[str]) -> List[Dict]:
    """
    Prepare document data from both uploaded files and Google Drive documents.

    Args:
        uploaded_doc_ids (List[str]): IDs of uploaded documents
        drive_doc_ids (List[str]): IDs of Google Drive documents

    Returns:
        List[Dict]: Combined document data for processing
    """
    pdf_datas = []

    # Prepare uploaded documents (existing functionality)
    for doc_id in uploaded_doc_ids:
        try:
            pdf_data, pdf_name = await current_s3_client.get_document(document_id=doc_id)
            pdf_datas.append({
                "document_id": doc_id,
                "pdf_name": pdf_name,
                "pdf_data": pdf_data,
                "source_type": "uploaded"
            })
        except Exception as e:
            logger.error(f"Error loading uploaded document {doc_id}: {str(e)}")

    # Google Drive documents are now processed and stored in unified collection
    # We can get their metadata from the search results instead of re-downloading
    for doc_id in drive_doc_ids:
        try:
            # Since Google Drive docs are in unified collection, we can reference them
            # but don't need to download content (already processed and embedded)
            pdf_datas.append({
                "document_id": doc_id,
                "pdf_name": f"Google Drive Document {doc_id}",
                "pdf_data": b"",  # Content already in vector store
                "source_type": "google_drive",
                "file_id": doc_id.replace("drive_", "") if doc_id.startswith("drive_") else doc_id,
                "shareable_link": None  # Can be added via unified search results if needed
            })
            logger.info(f"Added Google Drive document {doc_id} for context")

        except Exception as e:
            logger.error(f"Error processing Google Drive document {doc_id}: {str(e)}")

    log(f"Prepared {len(pdf_datas)} documents for processing ({len(uploaded_doc_ids)} uploaded, {len(drive_doc_ids)} Drive)")
    return pdf_datas

async def search_and_preview_sources(
    query: str,
    max_results: int = 10,
    score_threshold: float = 0.6
) -> Dict:
    """
    Preview what documents would be used for a query without running full RAG.
    Useful for debugging and user transparency.

    Args:
        query (str): Search query
        max_results (int): Maximum results to return
        score_threshold (float): Minimum relevance score

    Returns:
        Dict: Preview information about discoverable sources
    """
    try:
        # Get search results from all sources
        results = await unified_search_service.search_all_sources(
            query=query,
            max_results=max_results,
            score_threshold=score_threshold
        )

        # Group by source type
        uploaded_docs = []
        drive_docs = []

        for result in results:
            doc_info = {
                "document_id": result.document_id,
                "document_name": result.document_name,
                "score": result.score,
                "preview": result.content[:200] + "..." if len(result.content) > 200 else result.content
            }

            if result.source_type == DocumentSource.UPLOADED:
                uploaded_docs.append(doc_info)
            elif result.source_type == DocumentSource.GOOGLE_DRIVE:
                doc_info["shareable_link"] = result.shareable_link
                drive_docs.append(doc_info)

        return {
            "query": query,
            "total_found": len(results),
            "uploaded_documents": {
                "count": len(uploaded_docs),
                "documents": uploaded_docs
            },
            "google_drive_documents": {
                "count": len(drive_docs),
                "documents": drive_docs
            },
            "score_threshold": score_threshold
        }

    except Exception as e:
        logger.error(f"Error in search preview: {str(e)}")
        return {
            "query": query,
            "error": str(e),
            "total_found": 0,
            "uploaded_documents": {"count": 0, "documents": []},
            "google_drive_documents": {"count": 0, "documents": []}
        }