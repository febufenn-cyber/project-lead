from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LeadGen MVP API"
    api_prefix: str = "/api/v1"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/leadgen"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Data Sources
    google_places_api_key: str = ""
    google_custom_search_api_key: str = ""
    google_custom_search_engine_id: str = ""
    bing_search_api_key: str = ""
    
    # Email & Contact Enrichment
    hunter_api_key: str = ""
    snov_api_key: str = ""
    apollo_api_key: str = ""
    clearbit_api_key: str = ""
    
    # AI Services
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    
    # Infrastructure
    cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080,http://localhost:3000"
    request_timeout_seconds: int = 20
    proxy_list: str = ""
    
    # Integration Webhooks
    n8n_webhook_url: str = ""
    yetiforce_api_url: str = ""
    openclaw_gateway_url: str = "http://localhost:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
