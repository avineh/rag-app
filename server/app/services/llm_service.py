import importlib
import types
from google import genai
from app.core.config import settings


class LLMService:

    # רשימת המודלים הנתמכים - מפתחות הם מזהי מודל, הערך מכיל תצורה ותווית
    SUPPORTED_MODELS = {
        # Google Gemini models (Free tier included in your API Key)
        "gemini-2.5-flash": {"name": "Gemini 2.5 Flash (Google - Free)", "provider": "google"},
        "gemini-2.5-pro": {"name": "Gemini 2.5 Pro (Google - Free Tier)", "provider": "google"},
        "gemini-1.5-pro-latest": {"name": "Gemini 1.5 Pro Latest (Google)", "provider": "google"},

        # GROQ Models (Free high-speed models, updated to latest versions)
        "groq:llama-3.3-70b-versatile": {"name": "Llama 3.3 70B (Groq - Free)", "provider": "groq"},
        "groq:llama3-70b-8192": {"name": "Llama 3 70B (Groq - Free)", "provider": "groq"},
        "groq:mixtral-8x7b-32768": {"name": "Mixtral 8x7B (Groq - Free RAG)", "provider": "groq"},

        # OpenRouter (Free Tier & OpenAI alternatives)
        "openrouter:deepseek/deepseek-chat": {"name": "DeepSeek V3 (OpenRouter - Ultra Cheap)", "provider": "openrouter"},
        "openrouter:google/gemini-2.5-flash": {"name": "Gemini 2.5 Flash (OpenRouter - Free)", "provider": "openrouter"},
        "openrouter:meta-llama/llama-3.3-70b-instruct:free": {"name": "Llama 3.3 70B (OpenRouter - Free)", "provider": "openrouter"},
        "openrouter:ibm/granite-3.1-8b-instruct:free": {"name": "IBM Granite 3.1 8B (OpenRouter - Free)", "provider": "openrouter"},

        # OpenAI (Paid - kept if you upgrade billing in the future)
        "openai-chat:gpt-4o": {"name": "OpenAI GPT-4o (Paid Quota)", "provider": "openai"},
        "openai-chat:gpt-4o-mini": {"name": "OpenAI GPT-4o Mini (Paid Quota)", "provider": "openai"},
    }
    
    # מודל ברירת המחדל למקרה שלא נבחר מודל
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self):
        # Google client (used when provider == 'google')
        self.google_client = None
        try:
            self.google_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception:
            self.google_client = None

    def _is_provider_configured(self, provider: str) -> bool:
        """Checks if the necessary API keys/configurations exist for a given provider."""
        if provider == "google":
            return bool(settings.GEMINI_API_KEY)
        if provider == "openai":
            return bool(settings.OPENAI_API_KEY)
        if provider == "openrouter":
            return bool(settings.OPENROUTER_API_KEY)
        if provider == "groq":
            return bool(settings.GROQ_API_KEY)
        return False

    def _split_model_id(self, model_id: str) -> tuple[str | None, str]:
        if ':' in model_id:
            return tuple(model_id.split(':', 1))
        if '/' in model_id:
            return tuple(model_id.split('/', 1))
        return None, model_id

    def generate_answer(self, prompt: str, model: str | None = None):
        """
        Generate a short answer using the requested model. If the model's provider
        is not configured or its client library is not installed, raise an error.
        """
        model_id = model or self.DEFAULT_MODEL
        meta = self.SUPPORTED_MODELS.get(model_id)
        if not meta:
            raise ValueError(f"Unknown model: {model_id}")

        provider = meta.get("provider")
        provider_name, actual_model_name = self._split_model_id(model_id)
        actual_model = model_id if provider == 'google' else actual_model_name

        # Google / Gemini
        if provider == "google":
            if not self.google_client:
                raise RuntimeError("Google Gemini client not configured")
            response = self.google_client.models.generate_content(
                model=actual_model,
                contents=prompt
            )
            return response.text

        # OpenAI
        if provider == "openai":
            openai_spec = importlib.util.find_spec("openai")
            if not openai_spec:
                raise RuntimeError("OpenAI client library not installed; run 'pip install openai'")
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.chat.completions.create(
                    model=actual_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512
                )
                return resp.choices[0].message.content
            except Exception as e:
                raise RuntimeError(f"OpenAI request failed: {e}")

        # OpenRouter (Non-streaming implementation)
        if provider == "openrouter":
            openai_spec = importlib.util.find_spec("openai")
            if not openai_spec:
                raise RuntimeError("OpenAI client library not installed; run 'pip install openai'")
            try:
                from openai import OpenAI
                base = getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
                key = settings.OPENROUTER_API_KEY
                if not key:
                    raise RuntimeError('OPENROUTER_API_KEY not configured')
                client = OpenAI(api_key=key, base_url=base)
                resp = client.chat.completions.create(
                    model=actual_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512
                )
                return resp.choices[0].message.content
            except Exception as e:
                raise RuntimeError(f"OpenRouter request failed: {e}")

        # Anthropic support (best-effort)
        if provider == "anthropic":
            anth_spec = importlib.util.find_spec("anthropic")
            if not anth_spec:
                raise RuntimeError("Anthropic client library not installed; run 'pip install anthropic'")
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                prompt_text = f"Human: {prompt}\nAssistant:" 
                resp = client.completions.create(model=actual_model, prompt=prompt_text, max_tokens=512)
                return getattr(resp, 'completion', getattr(resp, 'text', str(resp)))
            except Exception as e:
                raise RuntimeError(f"Anthropic request failed: {e}")

        # Other providers not implemented yet
        raise RuntimeError(f"Provider '{provider}' is not implemented in this server")

    def stream_answer(self, prompt: str, model: str | None = None):
        """
        Stream answer tokens/chunks for models that support streaming (generator).
        """
        model_id = model or self.DEFAULT_MODEL
        meta = self.SUPPORTED_MODELS.get(model_id)
        if not meta:
            raise ValueError(f"Unknown model: {model_id}")
        provider = meta.get("provider")
        provider_name, actual_model_name = self._split_model_id(model_id)
        actual_model = model_id if provider == 'google' else actual_model_name

        # OpenAI streaming
        if provider == "openai":
            openai_spec = importlib.util.find_spec("openai")
            if not openai_spec:
                raise RuntimeError("OpenAI client library not installed; run 'pip install openai'")
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                stream = client.chat.completions.create(
                    model=actual_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    stream=True
                )
                for chunk in stream:
                    try:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            yield delta.content
                    except Exception:
                        continue
                return
            except Exception as e:
                raise RuntimeError(f"OpenAI streaming failed: {e}")

        # OpenRouter streaming
        if provider == 'openrouter':
            openai_spec = importlib.util.find_spec("openai")
            if not openai_spec:
                raise RuntimeError("OpenAI client library not installed; run 'pip install openai'")
            try:
                from openai import OpenAI
                base = getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
                key = settings.OPENROUTER_API_KEY
                if not key:
                    raise RuntimeError('OPENROUTER_API_KEY not configured')
                client = OpenAI(api_key=key, base_url=base)
                stream = client.chat.completions.create(
                    model=actual_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    stream=True
                )
                for chunk in stream:
                    try:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            yield delta.content
                    except Exception:
                        continue
                return
            except Exception as e:
                raise RuntimeError(f"OpenRouter streaming failed: {e}")

        # Google/genai: no streaming helper implemented here; fallback to single response
        if provider == 'google':
            return (self.generate_answer(prompt, model=model) for _ in [None])

        # Anthropic: fallback to non-streaming
        if provider == 'anthropic':
            full = self.generate_answer(prompt, model=model)
            yield full
            return

    def get_models(self):
        # Return structured list including availability info
        models = []
        for model_id, meta in self.SUPPORTED_MODELS.items():
            provider = meta.get("provider")
            models.append({
                "id": model_id,
                "name": meta.get("name"),
                "provider": provider,
                "configured": self._is_provider_configured(provider)
            })
        return models

    def validate_model(self, model_id: str) -> None:
        """
        Lightweight validation of a model identifier.
        """
        model_info = self.SUPPORTED_MODELS.get(model_id)
        if not model_info:
            raise RuntimeError(f"Unknown model: {model_id}")
            
        provider = model_info.get("provider")

        # הרצת ולידציה ספציפית ל-Groq
        if provider == 'groq':
            try:
                import requests
            except Exception:
                raise RuntimeError("requests not available to validate Groq model")
                
            key = getattr(settings, 'GROQ_API_KEY', None)
            base = getattr(settings, 'GROQ_BASE_URL', None) or 'https://api.groq.com'
            if not key:
                raise RuntimeError('GROQ_API_KEY not configured')
                
            provider_name, actual = self._split_model_id(model_id)
            actual_model = actual
            url = f"{base.rstrip('/')}/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            body = {
                "model": actual_model,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            }
            try:
                r = requests.post(url, json=body, headers=headers, timeout=10)
                if r.status_code == 404:
                    try:
                        j = r.json()
                        msg = j.get('error', {}).get('message', r.text)
                    except Exception:
                        msg = r.text
                    raise RuntimeError(f"Groq model validation failed: {msg}")
                r.raise_for_status()
            except RuntimeError:
                raise
            except Exception as e:
                raise RuntimeError(f"Groq validation request failed: {e}")

        # בדיקת קונפיגורציה כללית לכל שאר הפרוביידרים
        if not self._is_provider_configured(provider):
            raise RuntimeError(f"Provider '{provider}' is not configured")


llm_service = LLMService()