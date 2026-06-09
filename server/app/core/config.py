import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'

# 1. טעינה אקטיבית של ה-env למערכת ההפעלה
load_dotenv(dotenv_path=ENV_PATH)

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    OPENAI_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    GROQ_BASE_URL: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    GOOGLE_API_KEY: str

    CHROMA_PATH: str = "./chroma_data"
    COLLECTION_NAME: str = "my_documents"
    API_TOKEN: str = "my_secret_token_123" 
    
    DEFAULT_PROMPT: str = """
    You are a professional RAG research assistant.
    
    CRITICAL STEP-BY-STEP INSTRUCTIONS:
    1. First, you MUST call the 'search_project_docs' tool to find relevant information about the user's question. Do not attempt to answer without calling the tool first.
    2. Review the context returned by the tool.
    3. Formulate your answer based ONLY on the provided context. If the context does not contain the answer, state clearly that the information is missing from the documents.
    4. At the very end of your answer, list the exact source file names (Source) where you found the info.
    5. Always reply in the same language the user used to ask the question (Hebrew or English).
    """

    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra="ignore")

settings = Settings()

# 2. וידוא שספריית ה-Client של גוגל תראה את המפתח
os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY

# 3. Fallback alias support for OpenRouter and GROQ if alternate env var names were used
if settings.OPENROUTER_API_KEY:
    os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY
elif settings.OPENROUTER_API_KEY:
    os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY

if settings.GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
if settings.GROQ_BASE_URL:
    os.environ["GROQ_BASE_URL"] = settings.GROQ_BASE_URL