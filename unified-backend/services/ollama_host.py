from configs.config import OllamaSettings
from langchain_ollama import OllamaEmbeddings

ollama_settings = OllamaSettings()

MODEL_NAME = "nomic-embed-text"

current_ollama_client = OllamaEmbeddings(
        model=MODEL_NAME,
        base_url=ollama_settings.OLLAMA_ENDPOINT_URL
    )