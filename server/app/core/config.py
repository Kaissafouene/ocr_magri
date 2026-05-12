from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Magriplast Document Processing"
    debug: bool = Field(default=False, validation_alias=AliasChoices("APP_DEBUG", "MAGRIPLAST_DEBUG"))
    api_prefix: str = "/api/v1"


    database_url: str = Field(
        default="sqlite+aiosqlite:///./magriplast.db"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Celery / Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")

    # Storage (S3 / MinIO)
    storage_endpoint_url: str = Field(default="http://localhost:9000")
    storage_access_key: str = Field(default="minioadmin")
    storage_secret_key: str = Field(default="minioadmin")
    storage_bucket_name: str = Field(default="magriplast-documents")
    storage_region: str = Field(default="us-east-1")
    storage_mode: str = Field(default="local")
    local_storage_path: str = Field(default="./data/storage")

    # Task execution
    task_mode: str = Field(default="local")

    # OCR
    tesseract_cmd: str = Field(default="tesseract")
    tesseract_language: str = "fra"
    ocr_confidence_threshold: float = 0.70  # below this → cloud fallback
    classification_confidence_threshold: float = 0.90  # below this → LLM fallback

    # Google Document AI (cloud OCR fallback)
    google_docai_enabled: bool = False
    google_docai_project_id: str = Field(default="")
    google_docai_processor_id: str = Field(default="")
    google_application_credentials: str = Field(default="")

    # LLM fallback (OpenAI)
    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    llm_model: str = Field(default="gpt-4.1", validation_alias=AliasChoices("OPENAI_MODEL", "LLM_MODEL"))
    llm_max_tokens: int = 1500
    llm_temperature: float = 0.0
    price_tolerance: float = 0.01       # EUR
    quantity_tolerance: float = 0.0     # units (exact by default)
    line_total_tolerance: float = 0.02  # EUR
    tva_tolerance: float = 0.0          
    reference_levenshtein_max_distance: int = 2
    max_pdf_size_bytes: int = 52_428_800  # 50MB
    max_pdf_pages: int = 50
    job_timeout_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
