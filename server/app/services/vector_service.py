import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from app.core.config import settings

class VectorService:
    def __init__(self):
        # חיבור ל-ChromaDB
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(name=settings.COLLECTION_NAME)
        
        # מודל ה-Embeddings (רץ מקומית אצלך)
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # כלי לפירוק טקסט - 1000 תווים עם חפיפה של 100
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )

    def ingest_text(self, text: str, file_name: str):
        """תהליך ה-Ingestion: חיתוך, וקטוריזציה ושמירה"""
        
        # 1. חיתוך לצ'אנקים
        chunks = self.text_splitter.split_text(text)
        
        # 2. יצירת מזהים ייחודיים (IDs) ומטדאטה
        ids = [f"{file_name}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": file_name, "chunk_index": i} for i in range(len(chunks))]
        
        # 3. יצירת ה-Embeddings (הפיכה למספרים)
        embeddings = self.embed_model.encode(chunks).tolist()
        
        # 4. שמירה ב-Chroma
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        return len(chunks)

    def ingest_data(self, content: str, source_name: str, project_name: str, source_type: str = "file"):
        """
        1. תמיכה בטקסט וקבצים עם מטא-דאטה שקוף
        2. חלוקה לפרויקטים (collections)
        """
        # התחברות או יצירת אוסף לפי שם הפרויקט
        collection = self.client.get_or_create_collection(name=project_name)
        
        chunks = self.text_splitter.split_text(content)
        ids = [f"{source_name}_{source_type}_{i}" for i in range(len(chunks))]
        
        # שמירת מטא-דאטה לזיהוי שקוף של המקור
        metadatas = [{
            "source": source_name, 
            "type": source_type,
            "project": project_name,
            "chunk_index": i
        } for i in range(len(chunks))]
        
        embeddings = self.embed_model.encode(chunks).tolist()
        
        collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        return len(chunks)

    def search(self, query: str, project_name: str, n_results: int = 3):
        """חיפוש בתוך פרויקט ספציפי"""
        try:
            collection = self.client.get_collection(name=project_name)
            query_embedding = self.embed_model.encode([query]).tolist()
            return collection.query(query_embeddings=query_embedding, n_results=n_results)
        except:
            return None # פרויקט לא קיים
        
    # def search(self, query: str, n_results: int = 3):
    #     """חיפוש סמנטי בתוך ה-DB"""
    #     query_embedding = self.embed_model.encode([query]).tolist()
    #     results = self.collection.query(
    #         query_embeddings=query_embedding,
    #         n_results=n_results
    #     )
    #     return results['documents'][0] if results['documents'] else []

vector_service = VectorService()