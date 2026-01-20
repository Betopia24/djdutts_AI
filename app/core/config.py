import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL_NAME: str = os.getenv("embedding_model_name", "text-embedding-3-large")
    GENERATION_MODEL_NAME: str = os.getenv("generation_model_name", "gpt-4o-mini")
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "faiss_index")
    cohere_embedding_api_key: str = os.getenv("Cohere_embedding_api_key", "")


settings = Settings()



