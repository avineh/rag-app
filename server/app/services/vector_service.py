import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from app.core.config import settings

class VectorService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PATH) # חיבור ל-ChromaDB
        self.collection = self.client.get_or_create_collection(name=settings.COLLECTION_NAME) # יצירת קולקשן ברירת מחדל (Sandbox)
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2') # מודל ה-Embeddings (רץ מקומית)
        self.text_splitter = RecursiveCharacterTextSplitter( # כלי לפירוק טקסטים לחתיכות קטנות יותר
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

    # פונקציה שמבצעת את כל תהליך ה-ingest: חיתוך הטקסט, וקטוריזציה ושמירה ב-ChromaDB תחת שם הפרויקט המתאים. 
    # בנוסף, היא מוסיפה מטא-דאטה עשיר לכל חתיכה של טקסט, כולל שם המקור, סוגו, שם הפרויקט ואינדקס החתיכה בתוך המקור, 
    # כדי לאפשר שליפה מדויקת יותר בעת החיפוש. הפונקציה מחזירה את מספר החתיכות שנוצרו מהטקסט שהועלה.
    def ingest_data(self, content: str, source_name: str, project_name: str, source_type: str = "file"):
        collection = self.client.get_or_create_collection(name=project_name)
        chunks = self.text_splitter.split_text(content)
        
        ids = [f"{source_name}_{source_type}_{i}" 
            for i in range(len(chunks))] # יצירת מזהים ייחודיים לכל חתיכה של טקסט, כולל שם המקור והסוג שלו

        metadatas = [{"source": source_name, "type": source_type, "project": project_name, "chunk_index": i}
            for i in range(len(chunks))] # יצירת מטא-דאטה עשיר לכל חתיכה, כולל שם המקור, סוגו, שם הפרויקט ואינדקס החתיכה בתוך המקור 
        
        embeddings = self.embed_model.encode(chunks).tolist()
        collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        return len(chunks)
    
    # פונקציה שמחזירה את רשימת הקבצים/מקורות הייחודיים שקיימים בפרויקט מסוים, על בסיס שדה ה-'source' שהגדרנו במטא-דאטה של כל חתיכה בעת ה-ingest
    def get_project_files(self, project_name: str):
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

    # פונקציית חיפוש בתוך פרויקט ספציפי, מחזירה את התוצאות הכי רלוונטיות לפי השאילתה שהתקבלה    
    def search(self, query: str, project_name: str, n_results: int = 3): 
        try:
            collection = self.client.get_collection(name=project_name)
            query_embedding = self.embed_model.encode([query]).tolist()
            return collection.query(query_embeddings=query_embedding, n_results=n_results)
        except Exception:
            return None

    # פונקציה שמאפשרת לשנות את שם הפרויקט (הקולקשן) ב-ChromaDB, כולל טיפול בשגיאות במידה והפרויקט הישן לא קיים או שהשם החדש כבר תפוס            
    def rename_project(self, old_name: str, new_name: str):
        try:
            collection = self.client.get_collection(name=old_name)
            collection.modify(name=new_name)
            return True
        except Exception as e:
            print(f"Error renaming project: {e}")
            return False

vector_service = VectorService()