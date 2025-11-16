from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.s3host import current_s3_client
from models.tables import table_repo
from services.document_encoder import DocumentEncoder
from schemas.base import ListTableIdsRequest
router = APIRouter()

@router.post("/get-document-tables")
async def get_document_tables(request: ListTableIdsRequest):
    """
    Fetch table URLs for a document saved in S3.
    
    Args:
        document_id (str): The document's unique identifier
        user_id (str): The user ID

    Returns:
        list: List of presigned URLs for tables
    """
    try:
        document_id = request.document_id
        user_id = request.user_id
        all_presigned_urls = []

        # Get tables from database
        tables = await table_repo.get_tables_by_document_id(document_id)
        
        # Generate presigned URLs for each table
        for table in tables:
            decode_user_id, document_name, _ = DocumentEncoder.decode_document_id(document_id)
            
            # Get presigned URL for each table
            presigned_url = await current_s3_client.get_presigned_view_url(table["id"])
            
            # Add metadata to the response
            table_info = {
                "url": presigned_url,
                "page_number": table["page_number"],
                "table_number": table["table_number"]
            }
            all_presigned_urls.append(table_info)

        return all_presigned_urls
    
    except Exception as e:
        raise HTTPException(
            status_code=404, 
            detail=f"Tables not found: {str(e)}"
        )