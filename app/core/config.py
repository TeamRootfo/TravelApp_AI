from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_URI: str
    MONGO_DB: str

    OPENAI_API_KEY: str
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"  # 1536 dims
    ELEVENLABS_API_KEY: str
    GOOGLE_MAPS_API_KEY: str
    OPENAI_TAG_MODEL: str = "gpt-4.1-mini"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()