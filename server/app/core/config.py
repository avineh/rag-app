from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GOOGLE_API_KEY: str  # הוספנו כדי לסנכרן עם ה-Agent
    CHROMA_PATH: str = "./chroma_data"
    COLLECTION_NAME: str = "my_documents"
    API_TOKEN: str
    
    # טעינה אוטומטית מקובץ .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()