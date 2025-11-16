from lib.hasher import hash_param
from fastapi import APIRouter, HTTPException
from utils.document_handling.logger import log
from services.s3host import current_s3_client

from schemas.base import (
    GetPresignedUploadUrlRequest,
    GetPresignedUploadUrlResponse,
)

router = APIRouter()


@router.post(
    "/get-presigned-upload-url", response_model=GetPresignedUploadUrlResponse
)
async def get_presigned_upload_url(request: GetPresignedUploadUrlRequest, ):
    try:
        userId = request.userId
        fileName = request.fileName

        if userId.strip() == "" or fileName.strip() == "" or userId is None or fileName is None:
            raise HTTPException(status_code=400, detail="userId and fileName are required")
        
        if not fileName.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only .pdf files are allowed")

        userId = await hash_param(userId)

        presigned_url, document_id =await current_s3_client.get_presigned_upload_url(
            complete_pdf_name=fileName, userId=userId
        )

        return GetPresignedUploadUrlResponse(presigned_url=presigned_url, uuid=document_id)

    except HTTPException as e:
        raise e
    except Exception as e:
        message = f"Error getting presigned upload URL"
        log(f"{message} {e}")
        raise HTTPException(status_code=500, detail=message)
