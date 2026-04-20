from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "CrisisLens API"
    APP_ENV: str = "dev"
    APP_PORT: int = 8000

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "crisislens"
    POSTGRES_USER: str = "crisislens"
    POSTGRES_PASSWORD: str = "crisislens"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    REDIS_STREAM_REPORTS: str = "reports:new"
    REDIS_STREAM_GROUP: str = "dispatchers"
    REDIS_STREAM_CONSUMER: str = "worker-1"

    JWT_SECRET: str = "change_me_in_production"
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 14
    TOKEN_REVOKE_PREFIX: str = "revoked"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


settings = Settings()