from pydantic import BaseModel
from services.document_db import get_database


class TableModel(BaseModel):
    id: str  # S3 key for the table image
    document_id: str
    page_number: int
    table_number: int


class TableRepository:
    def __init__(self, database):
        self.collection = database['tables']

    async def add_new_table(self, table_data: TableModel):
        table_data_dict = table_data.model_dump(by_alias=True)
        result = await self.collection.insert_one(table_data_dict)
        return str(result.inserted_id)

    async def get_tables_by_document_id(self, document_id: str):
        tables_cursor = self.collection.find(
            {"document_id": document_id}, 
            {"_id": 0}
        )
        tables = await tables_cursor.to_list(length=None)
        return tables
    
    async def get_table_count_by_document_id(self, document_id: str):
        count = await self.collection.count_documents({"document_id": document_id})
        return count


# Initialize the repository
db = get_database()
table_repo = TableRepository(db)