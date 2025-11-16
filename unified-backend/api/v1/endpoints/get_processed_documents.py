from typing import List
from lib.hasher import hash_param
from utils.document_handling.logger import log
#from services.authentication import verify_api_key
from fastapi import APIRouter, Depends, HTTPException
from schemas.base import GetProcessedDocumentsResponse, GetProcessedDocumentsRequest
from models.doc import doc_repo

router = APIRouter()

@router.post("/list-my-self-uploaded-documents", response_model=List[GetProcessedDocumentsResponse])
async def list_my_self_uploaded_documents(request: GetProcessedDocumentsRequest, 
):
    
    try:
        userId = request.userId

        if userId.strip() == "" or userId is None:
            raise HTTPException(status_code=400, detail="userId is required")
        
        userId = await hash_param(userId)
        
        log('Getting list of processed docs from DB')
        return await doc_repo.get_docs_by_user(userId=userId) 
    
    except HTTPException as e:
        raise e
    except Exception as e:
        message = f"Error returning processed documents of the user"
        log(f"{message} | {e}")
        raise HTTPException(status_code=500, detail=message)