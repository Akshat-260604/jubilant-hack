from pydantic import BaseModel
from typing import Optional
from services.document_db import get_database

class PreviewModel(BaseModel):
    id: str
    document_id: str
    page_number: Optional[int] = None  # Optional, if you want to store page number

class PreviewRepository:
    def __init__(self, database):
        self.collection = database['previews']

    async def add_new_preview(self, preview_data: PreviewModel):
        preview_data_dict = preview_data.model_dump(by_alias=True)
        result = await self.collection.insert_one(preview_data_dict)
        return str(result.inserted_id)

    async def get_previews_by_document_id(self, document_id: str):
        previews_cursor = self.collection.find({"document_id": document_id}, {"_id": 0})
        previews = await previews_cursor.to_list(length=None)
        return previews

db = get_database()
preview_repo = PreviewRepository(db)