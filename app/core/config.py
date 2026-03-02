from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "Agrisense Middleware"
    api_prefix: str = "/api"
    cors_origins: str = ""

    database_url: str

    # Sysadmin created on startup if both are set
    sysadmin_email: Optional[str] = None
    sysadmin_password: Optional[str] = None

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    chirpstack_base_url: str
    chirpstack_api_token: str
    chirpstack_webhook_token: str

    websocket_max_connections: int = 1000

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.cors_origins or not self.cors_origins.strip():
            return []
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

