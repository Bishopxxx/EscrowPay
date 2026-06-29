from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file = ".env")


    DATABASE_URL: str
    NOMBA_API_URL: str
    NOMBA_CLIENT_ID: str
    NOMBA_PRIVATE_KEY: str
    NOMBA_PARENT_ACCOUNT_ID: str
    NOMBA_SUB_ACCOUNT_ID: str
    NOMBA_WEBHOOK_SECRET: str 



settings = Settings()