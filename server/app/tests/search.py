import chromadb
from sentence_transformers import SentenceTransformer

#בדיקת חיפוש וקטורי - האם אנחנו באמת מוצאים את מה שזרקנו קודם?

# טעינת המודל (חייב להיות אותו מודל מה-Seed!)
model = SentenceTransformer('all-MiniLM-L6-v2')

client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_collection(name="my_documents")

# נסה לשנות את המשפט הזה למשהו דומה אבל לא זהה (למשל: "puppy" או "programming")
query_text = "I want to build a web service with python"

# 1. הופכים את השאלה שלנו לוקטור
query_embedding = model.encode([query_text]).tolist()

# 2. מחפשים את המשפט הכי קרוב ב-DB
results = collection.query(
    query_embeddings=query_embedding,
    n_results=1
)

print(f"Query: {query_text}")
print(f"Most similar document: {results['documents'][0][0]}")