from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GEMINI_API_KEY: str = "AIzaSyAdE-o_V5wJJ_8DmGuz_JNwWG4QrLkeeO8"
    CHROMA_PATH: str = "./chroma_data"
    COLLECTION_NAME: str = "my_documents"
    
    # טעינה אוטומטית מקובץ .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()