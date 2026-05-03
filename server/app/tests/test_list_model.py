from google import genai
import os
from dotenv import load_dotenv

# טעינת המפתח מהקובץ הנסתר
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

print("Listing available models...")
try:
    models = client.models.list()
    for model in models:
        print(f"Model Name: {model.name}")

except Exception as e:
    print(f"Error: {e}")