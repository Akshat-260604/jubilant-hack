from fastapi import APIRouter, HTTPException
from services.s3host import current_s3_client
from models.preview import preview_repo
from schemas.base import GetDocumentPreviewRequest

router = APIRouter()

@router.post("/get-document-previews")
async def get_document_previews(request: GetDocumentPreviewRequest):
    """
    Fetch preview image URLs for a document saved in S3.

    Args:
        document_id (str): The document's unique identifier
        user_id (str): The user ID

    Returns:
        list: List of presigned URLs for preview images
    """
    try:
        document_id = request.document_id
        user_id = request.user_id
        all_presigned_urls = []

        # Get previews from database
        previews = await preview_repo.get_previews_by_document_id(document_id)

        # Generate presigned URLs for each preview
        for preview in previews:
            presigned_url = await current_s3_client.get_presigned_view_url(preview["id"])
            preview_info = {
                "url": presigned_url,
                "page_number": preview.get("page_number"),
            }
            all_presigned_urls.append(preview_info)

        return all_presigned_urls

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Preview images not found: {str(e)}"
        )