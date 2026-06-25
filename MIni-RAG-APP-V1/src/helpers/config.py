from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str
    APP_VERSION: str

    # Files
    FILE_ALLOWED_TYPES: List[str]
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    # Database
    # MONGODB_URI: str
    # MONGODB_DATABASE: str

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Backends
    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str
    OCR_BACKEND: str
    OCR_ENABLED: bool = True

    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_URL: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None

    # Models
    GENERATION_MODEL_ID_LITERAL: Optional[List[str]] = None 
    GENERATION_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_SIZE: Optional[int] = None
    OCR_MODEL_ID: Optional[str] = None

    # Generation params
    INPUT_DEFAULT_MAX_CHARACTERS: Optional[int] = None
    GENERATION_DEFAULT_MAX_TOKENS: Optional[int] = None
    GENERATION_DEFAULT_TEMPERATURE: Optional[float] = None

    # Vector DB
    VECTOR_DB_BACKEND_LITERAL: Optional[List[str]] = None
    VECTOR_DB_BACKEND: str
    VECTOR_DB_PATH: str
    VECTOR_DB_DISTANCE_METHOD: Optional[str] = None
    VECTOR_DB_DEFAULT_VECTOR_SIZE: int = 1536
    VECTOR_DB_INDEX_THRESHOLD: int = 100
    

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"



    model_config = SettingsConfigDict(
        env_file=(".env", "src/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )



def get_settings() -> Settings:
    return Settings()
