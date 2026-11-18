"""Central, environment-driven application settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    app_name: str = "StockPilot API"
    environment: str = "development"
    debug: bool = False
    database_url: str = "sqlite:///./stockpilot.db"
    jwt_secret_key: str = "fK-0gf7XawrKd9UdMSPGrG2JMzgxpgFTYlAumZ1Fq5PyuuYSeg-DKq-jZKdTgARq"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://172.20.10.3:5173,https://stock-pilot-frontend-six.vercel.app"
    mongodb_url: str | None = None
    mongodb_database: str = "stockpilot"
    llm_api_key: str | None = None
    llm_model: str = "openai/gpt-oss-20b"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: float = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.environment.lower() not in {"development", "test"}:
            if self.jwt_secret_key == "CHANGE_ME_TO_A_LONG_RANDOM_SECRET_BEFORE_DEPLOYMENT" or len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must be a unique random secret of at least 32 characters outside development")
            if self.debug:
                raise ValueError("DEBUG must be disabled outside development")
            if "*" in self.cors_origin_list:
                raise ValueError("Wildcard CORS origins are not allowed outside development")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
