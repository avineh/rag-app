from google import genai
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = self._get_best_model()

    def _get_best_model(self):
        try:
            models = self.client.models.list()
            # מחפש דגמי flash יציבים לפי הרשימה שראינו
            available = [m.name for m in models if 'flash' in m.name.lower()]
            # עדיפות ל-lite-latest כי ראינו שהוא עובד אצלך
            if "models/gemini-flash-lite-latest" in available:
                return "gemini-flash-lite-latest"
            return available[0].replace("models/", "") if available else "gemini-1.5-flash"
        except Exception as e:
            print(f"DEBUG: Error listing models: {str(e)}") # זה ידפיס את השגיאה המדויקת
            return "gemini-flash-lite-latest" # נשנה גם את הדיפולט למשהו יציב יותר

    def generate_answer(self, prompt: str):
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text

llm_service = LLMService()