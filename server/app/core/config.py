import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# 1. טעינה אקטיבית של ה-env למערכת ההפעלה
load_dotenv() 

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GOOGLE_API_KEY: str
    CHROMA_PATH: str = "./chroma_data"
    COLLECTION_NAME: str = "my_documents"
    API_TOKEN: str = "my_secret_token_123" 
    
    DEFAULT_PROMPT: str = """
    אתה עוזר מחקר אסיסטנט המבוסס על RAG.
    """

    # תפקידך לספק תשובות מדויקות המבוססות אך ורק על המידע שנמצא ב-Context שהוחזר מכלי החיפוש.
    # חוקים נוקשים:
    # 1. תמיד השתמש בכלי 'search_project_docs' לפני מתן תשובה.
    # 2. אם התשובה לא נמצאת ב-Context, אמור במפורש שאינך יודע כי המידע חסר במסמכים.
    # 3. אל תשתמש בידע פנימי שלך שאינו מגובה במסמכים שהועלו.
    # 4. בסוף כל תשובה, ציין את שמות הקבצים המקורים (Source) מהם נלקח המידע.
    # 5. ענה בשפה שבה נשאלה השאלה (עברית או אנגלית).

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# 2. וידוא שספריית ה-Client של גוגל תראה את המפתח
os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY