from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from lib.hasher import hash_param
from models.doc import DocModel, doc_repo
from services.document_encoder import DocumentEncoder
from services.s3host import current_s3_client
from utils.document_handling.logger import log
from utils.document_handling.process_document import process_document
from utils.document_handling.save_document_data_to_DB import mark_doc_status_in_db


router = APIRouter()


async def _run_async_process(
    document_data: bytes,
    document_name: str,
    user_id: str,
    document_id: str,
) -> None:
    """
    Background task to process a newly uploaded document.
    Mirrors the behavior of the trigger_document_processing flow.
    """
    try:
        await process_document(document_data, document_name, user_id, document_id)
    except Exception as e:
        log(f"Error in async processing for uploaded document: {str(e)}")
        await mark_doc_status_in_db("error", document_id)


@router.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    userId: str = Form(...),
):
    """
    Direct document upload endpoint to support `/documents/upload` used in the frontend API client.

    This is a convenience wrapper around the existing S3 + processing pipeline:
    - Saves the uploaded PDF to S3
    - Kicks off the async processing pipeline
    - Creates a document record in MongoDB

    Returns a UUID compatible with the rest of the document APIs.
    """
    try:
        if not userId or not userId.strip():
            raise HTTPException(status_code=400, detail="userId is required")

        if not file.filename:
            raise HTTPException(status_code=400, detail="File name is required")

        # For now we only support PDF uploads in the processing pipeline
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only .pdf files are supported")

        # Hash the user ID to be consistent with the rest of the system
        hashed_user_id = await hash_param(userId)

        # Read file bytes
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        # Generate a document_id compatible with existing helpers
        document_id = DocumentEncoder.encode_document_id(
            userId=hashed_user_id,
            document_name=file.filename,
        )

        # Compute the S3 key where the original PDF should live
        s3_key = DocumentEncoder.get_original_document_file_key(document_id)

        # Save file to S3
        await current_s3_client.save_to_s3(file_bytes, s3_key)

        # Kick off async processing in the background
        document_stem = Path(file.filename).stem
        background_tasks.add_task(
            _run_async_process,
            file_bytes,
            document_stem,
            hashed_user_id,
            document_id,
        )

        # Create a document record in DB
        await doc_repo.create_doc(
            DocModel(
                _id=document_id,
                userId=hashed_user_id,
                filename=document_stem,
            )
        )
        log(f"New document uploaded and enqueued for processing via /documents/upload: {document_id}")

        return {
            "uuid": document_id,
            "status": "ok",
        }

    except HTTPException:
        raise
    except Exception as e:
        log(f"Error in /documents/upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload and process document")


