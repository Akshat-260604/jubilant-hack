from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Dict, Literal, Optional
from services.document_db import get_database
import asyncio
from lib.logger import log

class HighlightModel(BaseModel):
    message_id: str
    index: int = Field(default=None) #TODO default value to be removed with v1 removed
    document_id: str  
    page_number: int
    source_text: Optional[str]=Field(default=None)
    bounding_boxes: Optional[List[Dict]]=Field(default=None)
    status: Literal['pending', 'done', 'error'] = Field(default='pending')


class HighlightRepository:
    def __init__(self, database):
        self.collection = database['highlights']
        asyncio.create_task(self._ensure_indexes())

    async def _ensure_indexes(self):
        """Create indexes only for fields used in queries."""
        await self.collection.create_index(
            [("message_id", 1), ("index", 1)]
        )
        # Uncomment only if you expect to keep using the deprecated methods
        await self.collection.create_index(
            [("message_id", 1), ("document_id", 1), ("page_number", 1)]
        )

    async def create_highlight(self, highlight: HighlightModel):
        result = await self.collection.insert_one(highlight.model_dump(by_alias=True))
        return str(result.inserted_id) 
    
    async def get_highlight(self, message_id: str, index: int):
        result = await self.collection.find_one({"message_id": message_id, "index": index})
        return result
    
    async def get_highlights_bulk(self, pairs: list[tuple[str, int]]):
        query = {"$or": [{"message_id": m_id, "index": idx} for m_id, idx in pairs]}
        cursor = self.collection.find(query,{"source_text": 0, "bounding_boxes": 0, "status": 0})
        results = await cursor.to_list(length=None)
        # map for quick lookup
        return {(r["message_id"], r["index"]): r for r in results}

    
    async def get_highlights_by_message_id(self, message_id: str):
        result = await self.collection.find({"message_id": message_id}).to_list(length=None)
        return result

    async def get_highlight_status(self, message_id: str, index: int):
        result = await self.collection.find_one({"message_id": message_id, "index": index}, {"status": 1})
        return result.get("status") if result else None
    
    async def get_highlight_source_text(self, message_id: str, index: int):
        result = await self.collection.find_one({"message_id": message_id, "index": index}, {"source_text": 1})
        return result.get("source_text") if result else None

    async def update_highlight_status(self, message_id: str, index:int, status: str):
        await self.collection.update_one({"message_id": message_id, "index": index}, {"$set": {"status": status}})

    async def update_highlight_text_and_bounding_box(self, message_id: str, index: int, source_text: str, bounding_boxes: List[Dict]):
        await self.collection.update_one({"message_id": message_id, "index": index}, {"$set": {"source_text": source_text, "bounding_boxes": bounding_boxes}})

# NOTE DEPRECATED
    async def get_highlight_by_doc_page(self,message_id: str, document_id: str, page_number: int):
        return await self.collection.find_one({"message_id": message_id,"document_id": document_id, "page_number": page_number})

    async def update_highlight_status_by_doc_page(self, message_id: str, document_id: str, page_number: int, status: str):
        result = await self.get_highlight_by_doc_page(message_id, document_id, page_number)
        if result is None:
            return
        query = {"message_id": message_id, "document_id": document_id, "page_number": page_number}
        if result != 'done':
            update = {"$set": {"status": status}}
            await self.collection.update_many(query, update)
        else:
            log(f"Skipping update of highlight status for message id in database: '{message_id}', document_id: '{document_id}', page_number: '{page_number}' | Already marked to done")

db = get_database()
highlight_repo = HighlightRepository(db)