from google import genai
from app.core.config import settings

class LLMService:

    # רשימת המודלים הנתמכים בתוכנה שבדקנו ועובדים עם RAG ו-Tools
    SUPPORTED_MODELS = {
        # "gemini-2.5-flash": "Gemini 2.5 Flash (מהיר ומומלץ)",
        # "gemini-2.5-pro": "Gemini 2.5 Pro (חזק ומדויק)",
        # "gemini-1.5-flash": "Gemini 1.5 Flash (גרסה יציבה)",
        # "gemini-1.5-pro": "Gemini 1.5 Pro (למשימות מורכבות)"

        "gemini-2.5-flash": "Gemini 2.5 Flash (מהיר ומומלץ)",
        "gemini-flash-latest": "Gemini Flash Latest",
        "gemini-3-flash-preview": "Gemini 3 Flash Preview",
        "gemini-3.1-flash-lite-preview": "Gemini 3.1 Flash Lite Preview"
    }
    
    # מודל ברירת המחדל למקרה שלא נבחר מודל
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generate_answer(self, prompt: str):
        # שימוש במודל הדיפולטיבי עבור משימות פנימיות כמו יצירת כותרות
        response = self.client.models.generate_content(
            model=self.DEFAULT_MODEL,
            contents=prompt
        )
        return response.text
    
    def get_models(self):
        # return [
        #     {"id": model_id, "name": name} 
        #     for model_id, name in self.SUPPORTED_MODELS.items()
        # ]
        return list(self.SUPPORTED_MODELS.keys())

llm_service = LLMService()