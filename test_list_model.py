import google.generativeai as genai

genai.configure(api_key="AIzaSyBraRAcRVSy9JM5l3WA2xrW0i7jYiqOvlU")

print("Listing available models...")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Model Name: {m.name}")