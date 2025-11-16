import asyncio
from pydantic import BaseModel, Field
from services.document_db import get_database


class ExtractedTextModel(BaseModel):
    document_id: str = Field(...)
    page_number: int = Field(...)
    fe_text: str = Field(...)
    be_text: dict = Field(...)


class ExtractedTextRepository:
    def __init__(self, database):
        self.collection = database['extracted_texts']
        asyncio.create_task(self._ensure_indexes())

    async def _ensure_indexes(self):
        """Create indexes only for fields used in queries."""
        await self.collection.create_index("document_id")

    async def create_text(self, text_data: ExtractedTextModel):
        result = await self.collection.insert_one(text_data.model_dump(by_alias=True))
        return str(result.inserted_id)

    async def bulk_create_text(self, text_data_list: list[ExtractedTextModel]):
        """Insert multiple text documents in bulk."""
        if not text_data_list:
            return 0
        documents = [td.model_dump(by_alias=True) for td in text_data_list]
        result = await self.collection.insert_many(documents)
        return len(result.inserted_ids)

    async def total_pages_count(self, document_id: str):
        return await self.collection.count_documents({"document_id": document_id})

    async def get_extracted_text_by_document_id(self, document_id: str):
        cursor = self.collection.find({"document_id": document_id})
        return await cursor.to_list(length=None)

    async def get_extracted_text_by_document_id_and_page_number(self, document_id: str, page_number: int):
        result = await self.collection.find_one(
            {"document_id": document_id, "page_number": page_number},
            {"_id": 0, "be_text": 1}
        )
        if result:
            return result['be_text']
        return None

    async def delete_texts_by_document_id(self, document_id: str):
        result = await self.collection.delete_many({"document_id": document_id})
        return result.deleted_count > 0


db = get_database()
extracted_text_repo = ExtractedTextRepository(db)
