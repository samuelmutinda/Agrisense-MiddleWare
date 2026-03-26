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

    # InfluxDB Configuration for time-series telemetry
    influxdb_url: str = ""
    influxdb_token: str = ""
    influxdb_org: str = "agrisense"
    influxdb_bucket_raw: str = "telemetry-raw"
    influxdb_bucket_downsampled: str = "telemetry-downsampled-1h"
    influxdb_bucket_kpi: str = "kpi-metrics"
    influxdb_bucket_digital_twin: str = "digital_twin"
    influxdb_enabled: bool = False

    # Notification Service Configuration
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: str = "alerts@agrisense.io"
    
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    
    africastalking_api_key: Optional[str] = None
    africastalking_username: Optional[str] = None
    africastalking_shortcode: Optional[str] = None

    # Firebase Cloud Messaging for push notifications
    fcm_server_key: Optional[str] = None

    # Google Maps API for route optimization
    google_maps_api_key: Optional[str] = None

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.cors_origins or not self.cors_origins.strip():
            return []
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def influxdb_configured(self) -> bool:
        return bool(self.influxdb_url and self.influxdb_token and self.influxdb_enabled)

    @property
    def sendgrid_configured(self) -> bool:
        return bool(self.sendgrid_api_key)

    @property
    def twilio_configured(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token)

    @property
    def africastalking_configured(self) -> bool:
        return bool(self.africastalking_api_key and self.africastalking_username)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

