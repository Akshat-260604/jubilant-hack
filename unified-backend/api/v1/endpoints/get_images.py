from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from services.s3host import current_s3_client
from models.images import image_repo
from services.document_encoder import DocumentEncoder
import json

router = APIRouter()
class ListImageIdsRequest(BaseModel):
    document_id:str
    user_id: str

@router.post("/get-document-images")
async def get_document_images(request:ListImageIdsRequest):
    """
    Fetch image URLs for a document saved in S3.
    
    Args:
        user_id (str): The user ID
        document_name (str): The name of the PDF (e.g., "report.pdf")

    Returns:
        JSON with image URLs or error
    """
    try:
        print("Hello world")
        document_id=request.document_id
        user_id=request.user_id
        all_presigned_urls=[]

        image_ids=await image_repo.get_image_by_document_id(document_id)
        for image_id in image_ids:
            decode_user_id, document_name, upload_timestamp=DocumentEncoder.decode_document_id(document_id)
            splited_id=image_id.split("_")

            image_name=f'{splited_id[-2]}_{splited_id[-1]}'
            image_key=f"DB/USERS/{decode_user_id}/document_images/{document_name}/{image_name}"
            presigned_url=await current_s3_client.get_presigned_view_url(image_key)
            all_presigned_urls.append(presigned_url)

        return all_presigned_urls
    
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Images not found: {str(e)}")
