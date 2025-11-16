from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class AppInfo(BaseSettings):
    PROJECT_NAME: str = "Process Document Microservice"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for instant ai content generation"
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["*"]  # Update with real domains for production


class QdrantSettings(BaseSettings):
    QDRANT_HOST_URL:str
 
    class Config:
        env_file = ".env"  
        env_file_encoding = "utf-8"
        extra = "ignore"  
 
 
class MongoDBSettings(BaseSettings):
    DOCUMENT_DB_CONNECTION_STRING:str
 
    class Config:
        env_file = ".env"  
        env_file_encoding = "utf-8"
        extra = "ignore"  
 
mongo_db_settings=MongoDBSettings()
 
class OllamaSettings(BaseSettings):
    OLLAMA_ENDPOINT_URL:str="http"
    OLLAMA_EMBEDDING_MODEL:str='nomic-embed-text'
    OLLAMA_ANALYTICAL_MODEL:str='gpt-4o'
    OLLAMA_ANALYTICAL_MODEL2:str='gpt-4o'
 
    class Config:
        env_file = ".env"  
        env_file_encoding = "utf-8"
        extra = "ignore"
 
class AWSSettings(BaseSettings):
    access_key: str
    secret_key: str
    qdrant_host_url: str
    ollama_endpoint_url: str
    document_db_connection_string: str

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"    # Add this line to allow extra fields in env


class OpenAISettings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_API_MODEL: str = "gpt-4o"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

class GoogleDriveSettings(BaseSettings):
    """
    Google Drive API configuration.

    Attributes:
        GOOGLE_DRIVE_FOLDER_ID (Optional[str]): ID of the shared Google Drive folder containing medical documents
        GOOGLE_SERVICE_ACCOUNT_KEY_PATH (str): Path to the service account JSON key file
        GOOGLE_DRIVE_QDRANT_COLLECTION (str): Qdrant collection name for Drive documents
        GOOGLE_DRIVE_ENABLED (bool): Whether Google Drive integration is enabled
    """
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_KEY_PATH: str = "credentials/service_account.json"
    GOOGLE_DRIVE_QDRANT_COLLECTION: str = "creator"
    GOOGLE_DRIVE_ENABLED: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-enable Google Drive if folder ID is provided
        if self.GOOGLE_DRIVE_FOLDER_ID:
            self.GOOGLE_DRIVE_ENABLED = True

    @property
    def is_configured(self) -> bool:
        """Check if Google Drive is properly configured."""
        import os
        return (
            self.GOOGLE_DRIVE_ENABLED and
            self.GOOGLE_DRIVE_FOLDER_ID is not None and
            os.path.exists(self.GOOGLE_SERVICE_ACCOUNT_KEY_PATH)
        )


# Initialize settings instances
app_info = AppInfo()
qdrant_settings = QdrantSettings()
mongo_db_settings = MongoDBSettings()
ollama_settings = OllamaSettings()
openai_settings = OpenAISettings()
aws_settings = AWSSettings()
google_drive_settings = GoogleDriveSettings()