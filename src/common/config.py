from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str
    database_url: str
    rabbitmq_url: str

    outbox_relay_enabled: bool = True
    outbox_poll_interval: float = 0.5
    outbox_batch_size: int = 100

    max_attempts: int = 3
    retry_base_delay: float = 1.0

    gateway_min_delay: float = 2.0
    gateway_max_delay: float = 5.0
    gateway_success_rate: float = 0.9
    gateway_timeout: float = 10.0

    webhook_timeout: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
