import asyncio
from models.doc import DocModel
from lib.hasher import hash_param
from fastapi import APIRouter, HTTPException, BackgroundTasks
from utils.document_handling.save_document_data_to_DB import doc_repo
from utils.document_handling.logger import log
from services.s3host import current_s3_client
from utils.document_handling.process_document import process_document
from services.document_encoder import DocumentEncoder
from schemas.base import TriggerProcessingRequest, TriggerProcessingResponse
from utils.document_handling.save_document_data_to_DB import mark_doc_status_in_db

router = APIRouter()

async def run_async_process(document_data: bytes, document_name: str, userId: str, document_id: str):
    """
    Function to run an async document processing task
    """
    try:
        await process_document(document_data, document_name, userId, document_id)
    except Exception as e:
        log(f"Error in async processing: {str(e)}")
        await mark_doc_status_in_db("error", document_id)

@router.post("/trigger-document-processing", response_model=TriggerProcessingResponse)
async def trigger_document_processing(request: TriggerProcessingRequest, background_tasks: BackgroundTasks):
    document_id = request.uuid
    userId = request.userId

    try:
        if not document_id.strip() or not userId.strip():
            raise HTTPException(status_code=400, detail="Both userId and uuid are required fields")

        userId = await hash_param(userId)
        user_id, _, upload_timestamp = DocumentEncoder.decode_document_id(document_id)
        if user_id != userId:
            message = "Not Authorized to access this document"
            log(message)
            raise HTTPException(status_code=403, detail=message)
        
        document_exists = await current_s3_client.check_document_exists(document_id=document_id)
        if not document_exists:
            message = "No document found in S3"
            log(message)
            raise HTTPException(status_code=404, detail=message)

        # Get document from S3
        document_data, document_name = await current_s3_client.get_document(document_id=document_id)

        background_tasks.add_task(run_async_process, document_data, document_name, userId, document_id)

        # Save document entry in DB
        await doc_repo.create_doc(DocModel(_id=document_id, userId=userId,filename=document_name))
        log(f'New document with {document_id} added to DB')

        return TriggerProcessingResponse(status="ok")

    except HTTPException as e:
        await mark_doc_status_in_db("error", document_id)
        raise e
    except Exception as e:
        message = f"Error processing document: {str(e)}"
        log(message)
        await mark_doc_status_in_db("error", document_id)
        raise HTTPException(status_code=500, detail=message)
