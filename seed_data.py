import chromadb
#בוא נלך על האופציה המקומית (HuggingFace) – ככה נשמור על הכל בתוך המחשב שלך בלי להסתבך עם אמצעי תשלום כרגע.
from sentence_transformers import SentenceTransformer

def seed_real_data():
    # 1. טעינת מודל חכם (בפעם הראשונה זה יוריד אותו מהאינטרנט, כ-400MB)
    # המודל הזה יודע להפוך משפט לרשימה של 384 מספרים שמייצגים משמעות
    model = SentenceTransformer('all-MiniLM-L6-v2')

    client = chromadb.PersistentClient(path="./chroma_data")
    
    # מחיקת הקולקשן הקודם (עם הנתונים האקראיים) כדי להתחיל נקי
    try:
        client.delete_collection(name="my_documents")
    except:
        pass
        
    collection = client.get_or_create_collection(name="my_documents")

    docs = [
        "FastAPI is a Python framework for building APIs.",
        "A Golden Retriever is a friendly family dog.",
        "The weather in Tel Aviv is sunny today.",
        "Python is great for machine learning and AI."
    ]

    # 2. יצירת הוקטורים האמיתיים! 
    # המודל סורק את הטקסט ומייצר "טביעת אצבע" דיגיטלית לכל משפט
    embeddings = model.encode(docs).tolist()

    ids = [f"id{i}" for i in range(len(docs))]

    collection.add(
        embeddings=embeddings,
        documents=docs,
        ids=ids
    )
    
    print(f"Successfully inserted {len(docs)} real embeddings!")

if __name__ == "__main__":
    seed_real_data()