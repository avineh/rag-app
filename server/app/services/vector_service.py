import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from app.core.config import settings

class VectorService:
    def __init__(self):
        # חיבור ל-ChromaDB
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        # יצירת קולקשן ברירת מחדל (Sandbox)
        self.collection = self.client.get_or_create_collection(name=settings.COLLECTION_NAME)
        
        # מודל ה-Embeddings (רץ מקומית)
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # כלי לפירוק טקסט
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )

    def list_projects(self):
        """מחזירה רשימה של שמות כל הפרויקטים הקיימים"""
        collections = self.client.list_collections()
        return [c.name for c in collections]
    
    def delete_project(self, project_name: str):
        """מוחק פרויקט שלם מה-DB"""
        try:
            self.client.delete_collection(name=project_name)
            return True
        except Exception as e:
            print(f"Error deleting collection {project_name}: {e}")
            return False

    def ingest_data(self, content: str, source_name: str, project_name: str, source_type: str = "file"):
        """חיתוך, וקטוריזציה ושמירה לפי שם פרויקט"""
        collection = self.client.get_or_create_collection(name=project_name)
        
        chunks = self.text_splitter.split_text(content)
        ids = [f"{source_name}_{source_type}_{i}" for i in range(len(chunks))]
        
        metadatas = [{
            "source": source_name, 
            "type": source_type,
            "project": project_name,
            "chunk_index": i
        } for i in range(len(chunks))]
        
        embeddings = self.embed_model.encode(chunks).tolist()
        collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        return len(chunks)
    
    def get_project_files(self, project_name: str):
        """מחזירה רשימת קבצים ייחודיים שקיימים בפרויקט"""
        try:
            collection = self.client.get_collection(name=project_name)
            # שליפת כל המטא-דאטה מהפרויקט
            results = collection.get(include=['metadatas'])
            
            if not results['metadatas']:
                return []
                
            # הוצאת שמות הקבצים הייחודיים מתוך שדה ה-'source' שהגדרנו ב-ingest
            sources = {meta.get('source') for meta in results['metadatas'] if meta.get('source')}
            return list(sources)
        except Exception:
            return []

    def search(self, query: str, project_name: str, n_results: int = 3):
        """חיפוש בתוך פרויקט ספציפי"""
        try:
            collection = self.client.get_collection(name=project_name)
            query_embedding = self.embed_model.encode([query]).tolist()
            return collection.query(query_embeddings=query_embedding, n_results=n_results)
        except Exception:
            return None

vector_service = VectorService()