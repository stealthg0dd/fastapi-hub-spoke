from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database — spokes share the same Postgres instance, isolated by schema
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/hubdb"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Application
    app_env: str = "development"
    debug: bool = True

    # Spoke identity — override per startup
    spoke_name: str = "spoke-template"
    api_prefix: str = "/api/v1"

    # Hub base URL for internal service calls
    hub_url: str = "http://hub:8000"


settings = Settings()
