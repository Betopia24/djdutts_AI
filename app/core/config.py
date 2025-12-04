import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    GOOGLE_AI_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")


settings = Settings()