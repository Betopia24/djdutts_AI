import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    Model_name : str = os.getenv("Model_name", "")
    pinecone_api: str = os.getenv("pinecone_api", "")


settings = Settings()