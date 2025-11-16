import asyncio
from utils.document_handling.logger import log

from http.client import HTTPException
from models.summary import SummaryModel
from models.doc import doc_repo 
from models.summary import summary_repo

async def save_document_outline_to_db(userId: str, document_id: str, document_outline: str, highlighted_images_ids:list):
    try:
        summary = {
            "text": document_outline,
            "highlighted_image_ids": highlighted_images_ids
            }
        await summary_repo.create_summary(
            SummaryModel(document_id=document_id,summary=summary)
        )
        
        log(f"Document {document_id}'s document outline has been saved")
    except Exception as e:
        message = "Error Saving document outline in the Document DB"
        log(f'{message}\n{e}')
        raise HTTPException(status_code=500, detail=message)


async def mark_doc_status_in_db(status: str, document_id: str, total_processing_time: str=''):
    try:
        await doc_repo.update_status(document_id= document_id, status=status)
        log(f"Document {document_id}'s status updated to {status}")
    except Exception as e:
        message = "Error Updating Status in the Document DB"
        log(f'{message}\n{e}')
        raise HTTPException(status_code=500, detail=message)
 