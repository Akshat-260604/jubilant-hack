import asyncio
from services.s3host import current_s3_client
from utils.chat.context_handling import retrieve_context
from utils.chat.logger import log
from utils.chat.stream_final_answer import stream_final_answer
from models.conversation import conversation_repo
from asyncio import sleep

async def run_single_document_rag_chain(
    document_ids: list[str],
    user_query: str,
    context_id,
    userId
):
    """
    Run a RAG (Retrieval Augmented Generation) chain for single or multiple documents.

    Args:
        document_ids (list[str]): List of document IDs to process
        user_query (str): The user's query text
        context_id (str): Conversation context ID (optional)
        userId (str): ID of the user making the request
        content_format (str): Desired format of the response
        objective (str): The objective or purpose of the query

    Yields:
        str: Generated response chunks, streamed one at a time
    """
    async def fetch_document(document_id, client):
        """
        Fetch document data from S3 storage.

        Args:
            document_id (str): ID of the document to fetch
            client: S3 client instance

        Returns:
            dict: Dictionary containing:
                - document_id (str): ID of the document
                - pdf_name (str): Name of the PDF file
                - pdf_data: Raw PDF data
        """
        pdf_data, pdf_name = await current_s3_client.get_document(document_id)
        return {
            "document_id": document_id,
            "pdf_name": pdf_name,
            "pdf_data": pdf_data
        }

    
    revamped_context, _ =await retrieve_context(query=user_query, document_ids=document_ids)

  
    revamped_context = revamped_context


    pdf_datas = await asyncio.gather(
        *[fetch_document(doc_id, current_s3_client) for doc_id in document_ids]
    )

    if not context_id or context_id == "":  
        context_id = await conversation_repo.create_conversation(document_ids)

    async for chunk in stream_final_answer(
        context_id=context_id,
        userId=userId,
        document_ids=document_ids,
        context=revamped_context,
        pdf_datas=pdf_datas,
        pdf_count=len(document_ids),
        user_query=user_query
    ):
        if "[DONE]" not in chunk:
            yield chunk
            await sleep(0.05)