import chromadb
from sentence_transformers import SentenceTransformer
from google import genai

#מימוש RAG ראשוני ובסיסי
# קובץ שמדגים איך כל החלקים מתחברים יחד – חיפוש ב-DB + שאלת ה-LLM עם הקונטקסט שמצאנו    

# 1. הגדרת ה-AI (תצטרך להוציא מפתח API חינמי של Gemini)
genai.configure(api_key="AIzaSyBraRAcRVSy9JM5l3WA2xrW0i7jYiqOvlU")
llm_model = genai.GenerativeModel('models/gemini-2.5-flash') #gemini-1.5-pro

# 2. הגדרת הזיכרון והמודל של הוקטורים
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_collection(name="my_documents")

def ask_rag(user_query):
    # א. הפיכת השאלה לוקטור וחיפוש ב-DB
    query_vector = embedding_model.encode([user_query]).tolist()
    search_results = collection.query(query_embeddings=query_vector, n_results=1)
    
    # ב. שליפת הטקסט שמצאנו
    context = search_results['documents'][0][0]
    
    # ג. בניית ה"פרומפט" - כאן קורה הקסם
    prompt = f"""
    You are a professional Python developer. 
    Based on the provided context, answer the user's question. 
    If the context mentions a specific framework, recommend it.
        
    Context: {context}
    
    User Question: {user_query}
    """
    
    # ד. קבלת תשובה מה-LLM
    response = llm_model.generate_content(prompt)
    return response.text

# הרצה
if __name__ == "__main__":
    question = "Which framework should I use for Python APIs?"
    answer = ask_rag(question)
    print(f"AI Answer: {answer}")
