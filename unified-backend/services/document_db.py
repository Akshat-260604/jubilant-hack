from motor.motor_asyncio import AsyncIOMotorClient
from configs.config import mongo_db_settings

class DatabaseConnection:
    _client = None
    
    @classmethod
    def get_connection(cls, connection_string: str):
        if cls._client is None:
            cls._client = AsyncIOMotorClient(connection_string)
        return cls._client

def get_database():
    client = DatabaseConnection.get_connection(mongo_db_settings.DOCUMENT_DB_CONNECTION_STRING)
    return client['creator']