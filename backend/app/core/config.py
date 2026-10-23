from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trans Boes API"
    app_env: str = "development"
    database_url: str = "sqlite:///./transboes.db"
    jwt_secret: str = "development-only-change-this-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    auto_assign_trip: bool = False
    auto_release_vehicle: bool = True
    freight_validation_mode: Literal["PASS_THROUGH", "MANUAL", "MOCK", "RULE_BASED"] = "MOCK"
    gps_provider: str = "mock"
    whatsapp_provider: str = "mock"
    preparation_minutes: int = 40
    vehicle_release_rule: Literal["AFTER_UNLOAD", "AFTER_RETURN"] = "AFTER_UNLOAD"
    maintenance_alert_km: int = 1000
    maintenance_alert_days: int = 15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def secure_production(self):
        if self.app_env == "production" and (len(self.jwt_secret) < 32 or self.jwt_secret == "development-only-change-this-secret"):
            raise ValueError("Configure um segredo JWT forte em produção")
        return self

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
