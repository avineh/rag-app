from fastapi import FastAPI
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# הגדרות (כמו קודם)
genai.configure(api_key="AIzaSyBraRAcRVSy9JM5l3WA2xrW0i7jYiqOvlU")
llm_model = genai.GenerativeModel('models/gemini-1.5-flash')
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_collection(name="my_documents")

# יצירת האפליקציה (כמו WebApplication.CreateBuilder ב-C#)
app = FastAPI()

@app.get("/ask")
def ask_ai(question: str):
    # 1. חיפוש ב-DB
    query_vector = embedding_model.encode([question]).tolist()
    results = collection.query(query_embeddings=query_vector, n_results=1)
    context = results['documents'][0][0]
    
    # 2. פנייה ל-AI
    prompt = f"Context: {context}\n\nQuestion: {question}"
    response = llm_model.generate_content(prompt)
    
    # 3. החזרת תשובה בפורמט JSON אוטומטי
    return {"answer": response.text, "source": context}