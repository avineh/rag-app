from google import genai
from app.core.config import settings

class LLMService:

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._cached_model = None
        #self.model_name = self._get_best_model()
        
    def _get_best_model(self):
        if self._cached_model:
            return self._cached_model
        
        try:
            models = self.client.models.list() #Fetching best model from Google API...
            available = [m.name for m in models if 'flash' in m.name.lower()]
            
            if "models/gemini-flash-lite-latest" in available:
                self._cached_model = "gemini-flash-lite-latest"
            else:
                self._cached_model = available[0].replace("models/", "") if available else "gemini-1.5-flash"
            
            return self._cached_model

        except Exception as e:
            print(f"DEBUG: Error listing models: {str(e)}") # זה ידפיס את השגיאה המדויקת
            return "gemini-flash-lite-latest" # נשנה גם את הדיפולט למשהו יציב יותר

    def generate_answer(self, prompt: str):
        # משתמשים בפונקציה שבודקת אם יש Cache
        current_model = self._get_best_model()
        
        response = self.client.models.generate_content(
            model=current_model,
            contents=prompt
        )
        return response.text
    
    def get_models(self):
        try:
            models = self.client.models.list()
            return [m.name.replace("models/", "") for m in models]
        except Exception as e:
            print(f"DEBUG: Error listing models: {str(e)}")
            return []

llm_service = LLMService()