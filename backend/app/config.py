from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    conversations_grpc_host: str = "api.us.cloud.uniphorestaging.com"
    conversations_grpc_port: int = 80
    conversations_rest_base_url: str = "https://api.us.cloud.uniphorestaging.com"
    tenant_summary_template: str = ""
    summary_field_name: str = "generated_summary"
    environment: str = "prod"
    cors_origins: List[str] = ["http://localhost:4200"]

    class Config:
        env_file = ".env"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
