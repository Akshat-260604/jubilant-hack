from datetime import datetime, timezone
from typing import Literal, List, Dict, Optional
from pydantic import BaseModel, Field
from services.document_db import get_database
from services.document_encoder import DocumentEncoder
from models.summary import summary_repo  

class DocModel(BaseModel):
    id: str = Field(..., alias="_id")
    userId: str = Field(...)
    filename:str
    status: Literal['pending', 'done', 'error'] = Field(default='pending')
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime =Field(default_factory=lambda: datetime.now(timezone.utc))

class DocRepository:
    def __init__(self, database):
        self.collection = database['docs']

    async def create_doc(self, doc_data: DocModel) -> str:
        result = await self.collection.insert_one(doc_data.model_dump(by_alias=True))
        return str(result.inserted_id)

    async def get_docs_by_user(self, userId: str) -> List[Dict]:
        docs_cursor = self.collection.find({"userId": userId}, {"userId": 0})
        docs = await docs_cursor.to_list(length=None)
        
        constructed_docs = []
        for doc in docs:
            userId, document_name, createdAt = DocumentEncoder.decode_document_id(doc["_id"])
            
            if(doc["status"] == "pending"):
            # Check the current timestamp - use timezone-aware datetime
                current_time = datetime.now(timezone.utc)
                # Parse the ISO timestamp which includes timezone info
                doc_time = datetime.fromisoformat(createdAt)
                
                # Convert doc_time to UTC for consistent comparison
                doc_time_utc = doc_time.astimezone(timezone.utc)
                
                # Calculate time difference in minutes
                time_difference = (current_time - doc_time_utc).total_seconds() / 60
                
                # If difference is more than 30 minutes, update status to error
                if time_difference > 30:
                    await self.update_status(doc["_id"], "error")
                    doc["status"] = "error"  # Update local status as well

            constructed_docs.append({
                "id": doc['_id'],
                "filename": document_name,
                "status": doc["status"],
                "createdAt": createdAt.split("T")[0]
            })
        return constructed_docs

    async def update_status(self, document_id: str, status: str) -> bool:
        result = await self.collection.update_one(
            {"_id": document_id},
            {"$set": {"status": status}}
        )
        return result.modified_count > 0

    async def check_existence(self, document_id: str) -> Optional[Dict]:
        return await self.collection.find_one({"_id": document_id})

    async def get_doc_by_id(self, document_id: str) -> Optional[Dict]:
        doc = await self.collection.find_one({"_id": document_id}, {"userId": 0})
        if not doc:
            return None

        
        userId, document_name, createdAt = DocumentEncoder.decode_document_id(doc["_id"])
        
        summary=await summary_repo.get_summary_by_document_id(document_id)
        
        return {
            "id":  document_id,
            "filename": document_name,
            "summary": summary["summary"],
            "creation_date": createdAt.split("T")[0]
        }
    
    async def delete_doc_by_document_id(self, document_id: str) -> bool:
        await self.summary_repo.delete_summary_by_document_id(document_id)
        await self.extracted_text_repo.delete_texts_by_document_id(document_id)
        await self.tables_repo.delete_tables_by_document_id(document_id)
        result = await self.collection.delete_one({"_id": document_id})
        return result.deleted_count > 0

# Initialize async database

db = get_database()
doc_repo = DocRepository(db)


