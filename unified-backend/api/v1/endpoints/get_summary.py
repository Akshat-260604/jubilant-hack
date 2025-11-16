from fastapi import APIRouter, HTTPException
from schemas.base import GenerateSummaryRequest
from models.doc import doc_repo
from models.summary import SummaryRepository
from schemas.base import GetMyDocumentDetailsRequest ,GetMyDocumentDetailsResponse
from lib.hasher import hash_param
from utils.document_handling.logger import log
from models.doc import doc_repo
from services.document_db import get_database

router = APIRouter()

@router.post("/get-my-document-details", response_model=GetMyDocumentDetailsResponse)
async def get_my_document_summaries(request: GetMyDocumentDetailsRequest):
    
    try:
        userId = request.userId
        id=request.id

        if userId.strip() == "" or userId is None:
            raise HTTPException(status_code=400, detail="userId is required")
        
        userId = await hash_param(userId)
        
        details= await doc_repo.get_doc_by_id(id)
        
        if not details:
             raise HTTPException(status_code=404, detail="Document not found")
        return details
    
    except HTTPException as e:
        raise e
    except Exception as e:
        message = f"Error returning document summaries of the user"
        log(f"{message} | {e}")
        raise HTTPException(status_code=500, detail=message)    