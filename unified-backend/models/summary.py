from typing import List
from pydantic import BaseModel, Field
from services.document_db import get_database

class HighlightedImage(BaseModel):
    id: str
    page_number: int

class Summary(BaseModel):
    text: str
    highlighted_image_ids: List[HighlightedImage]
    
class SummaryModel(BaseModel):
    document_id: str = Field(...)
    summary: Summary = Field(...)

class SummaryRepository:
    def __init__(self, database):
        self.collection = database['summaries']

    async def create_summary(self, summary_data: SummaryModel):
        result = await self.collection.insert_one(summary_data.model_dump(by_alias=True))
        return str(result.inserted_id)

    async def get_summary_by_document_id(self, document_id: str):
        return await self.collection.find_one({"document_id": document_id})
    
    async def delete_summary_by_document_id(self, document_id: str):
        result = await self.collection.delete_many({"document_id": document_id})
        return result.deleted_count > 0


db = get_database()
summary_repo = SummaryRepository(db)