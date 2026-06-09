from fastapi import FastAPI, File, Query, HTTPException, UploadFile, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from app.services.vector_service import vector_service
from app.services.agent import agent
from app.core.config import settings
from pydantic_ai.messages import (
    ModelRequest, 
    ModelResponse, 
    UserPromptPart, 
    TextPart, 
    SystemPromptPart
)
from app.services.llm_service import llm_service
import fitz  # PyMuPDF
from docx import Document
import io
import datetime
from pymongo import MongoClient
import certifi

MONGO_URI = "mongodb+srv://avineh_db_user:ZO8Yb89m69do3sdp@raggapp-cluster.sdrgbxh.mongodb.net/?retryWrites=true&w=majority"
#MONGO_URI = "mongodb://localhost:27017/"

client = MongoClient(
    MONGO_URI, 
    #tlsCAFile=certifi.where(),
    #tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=5000 # יקרוס תוך 5 שניות במקום חצי דקה אם יש בעיה
)
db = client["rag_application"]       # שם בסיס הנתונים
chat_collection = db["chat_history"]  # שם האוסף (ה"טבלה") עבור ההיסטוריה

app = FastAPI(title="RAG Chat App with PydanticAI")

# --- Middleware (אבטחה ו-CORS) ---
@app.middleware("http")
async def simple_auth_middleware(request: Request, call_next):
    # שורה אחת שמבטלת את האבטחה לצורך פיתוח - מאשרת הכל וממשיכה הלאה
    return await call_next(request)
    # מאפשרים גישה חופשית לתיעוד ה-API
    if request.url.path in ["/docs", "/openapi.json"]:
        return await call_next(request)
        
    # בדיקת ה-Token ב-Header
    token = request.headers.get("X-API-TOKEN")
    if token != settings.API_TOKEN:
        return StreamingResponse(iter(["Unauthorized access: Invalid Token"]), status_code=401)
        
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# מאגר זכרון זמני להיסטוריית השיחות
chat_histories: Dict[str, List[dict]] = {}

# --- Endpoints ---
@app.get("/ask")
async def ask(question: str, project: str, session_id: str, system_prompt: str = None, user_model: str = None):
    # 1. לוגיקת ברירת מחדל
    actual_prompt = settings.DEFAULT_PROMPT #system_prompt
    target_project = project or settings.COLLECTION_NAME
    
    # 2. שליפת היסטוריה ממונגו
    raw_history = list(chat_collection.find(
        {"user_id": session_id, "project_id": project},
        {"_id": 0}
    ).sort("timestamp", 1))

    # 3. בניית הזיכרון (Message History) בצורה תקנית ומקצועית עבור PydanticAI
    formatted_history = []
    
    # הזרקת ה-System Prompt הדינמי בצורה רשמית - זה מונע את ה-AssertionError!
    formatted_history.append(
        ModelRequest(parts=[SystemPromptPart(content=actual_prompt)])
    )
    
    # המרת הודעות העבר מה-DB למבנה ה-AST הרשמי של השיחה
    for msg in raw_history:
        if msg["role"] == "user":
            formatted_history.append(
                ModelRequest(parts=[UserPromptPart(content=msg["text"])])
            )
        elif msg["role"] == "ai":
            formatted_history.append(
                ModelResponse(parts=[TextPart(content=msg["text"])])
            )    

    # 4. שמירת שאלת המשתמש ב-MongoDB מיד
    save_chat_message(project, "user", question, session_id)

    # 5. בחירת המודל מתוך הרשימה הנתמכת (ומוודאים שהוא מוגדר בסביבה)
    selected_model = llm_service.DEFAULT_MODEL
    if user_model:
        model_info = next((m for m in llm_service.get_models() if m["id"] == user_model), None)
        if not model_info:
            raise HTTPException(status_code=400, detail=f"Unknown model requested: {user_model}")
        if not model_info.get("configured"):
            available = [m["id"] for m in llm_service.get_models() if m.get("configured")]
            raise HTTPException(status_code=400, detail=f"Model '{user_model}' is not configured on server. Available: {available}")
        selected_model = user_model
    # Pre-validate model availability for known providers (e.g., Groq)
    try:
        llm_service.validate_model(selected_model)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    async def stream_generator():
        full_response = ""
        
        # קריאה נקייה ויציבה ללא פרמטרים שבורים
        async with agent.run_stream(
            question, 
            deps=target_project, 
            message_history=formatted_history, 
            model=selected_model
        ) as result:
            
            async for chunk in result.stream_text(delta=True):
                full_response += chunk
                yield chunk
            
            # 6. בסיום ההזרמה - שמירת תשובת ה-AI ב-MongoDB
            if full_response:
                save_chat_message(project, "ai", full_response, session_id)

    return StreamingResponse(stream_generator(), media_type="text/plain")

# --- ניהול פרויקטים וקבצים ---
@app.get("/api/projects")
def list_projects():
    return {"projects": vector_service.list_projects()}

@app.delete("/api/projects/{project_name}")
def delete_project(project_name: str):
    success = vector_service.delete_project(project_name)
    return {"message": "Deleted"} if success else {"error": "Not found"}

@app.post("/api/projects/{project_name}/reset")
def reset_project(project_name: str):
    vector_service.delete_project(project_name)
    vector_service.client.get_or_create_collection(name=project_name)
    return {"message": f"Context for {project_name} cleared."}

@app.post("/api/ingest/text")
async def ingest_text(content: str, project: str, source_label: str = "manual_entry"):
    num_chunks = vector_service.ingest_data(content, source_label, project, source_type="text")
    return {"message": f"Added {num_chunks} chunks to project '{project}'"}

@app.post("/api/files/upload")
async def upload_file(project: str, file: UploadFile = File(...)):
    filename = file.filename
    content = await file.read()
    text = ""

    try:
        if filename.endswith(".pdf"):
            with fitz.open(stream=content, filetype="pdf") as doc:
                for page in doc: text += page.get_text()
        elif filename.endswith(".docx"): # תמיכה ב-Word
            doc = Document(io.BytesIO(content))
            text = "\n".join([para.text for para in doc.paragraphs])
        elif filename.endswith(".txt"):
            text = content.decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="סיומת לא נתמכת")

        if not text.strip():
            raise HTTPException(status_code=400, detail="הקובץ ריק")

        num_chunks = vector_service.ingest_data(
            content=text, 
            source_name=filename, 
            project_name=project, 
            source_type="file"
        )
        return {"message": f"File '{filename}' ingested successfully.", "chunks": num_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
@app.get("/api/projects/{project_name}/sources")
def get_project_sources(project_name: str):
    """מחזיר רשימה של שמות הקבצים/מקורות שקיימים בפרויקט"""
    try:
        # שליפת כל ה-metadata מהאוסף
        collection = vector_service.client.get_collection(name=project_name)
        results = collection.get(include=['metadatas'])
        
        # חילוץ שמות מקורות ייחודיים מתוך ה-metadata
        sources = set() # שימוש ב-set כדי להבטיח ייחודיות   
        for meta in results['metadatas']:
            if 'source' in meta:
                sources.add(meta['source'])
        
        return {"sources": list(sources)}
    except Exception as e:
        return {"sources": [], "error": str(e)}

@app.delete("/api/projects/{project_name}/sources")
def delete_specific_source(project_name: str, source_name: str):
    """מוחק את כל ה-chunks ששייכים למקור ספציפי בתוך פרויקט"""
    try:
        collection = vector_service.client.get_collection(name=project_name)
        # מחיקה לפי פילטר metadata
        collection.delete(where={"source": source_name})
        return {"message": f"Source '{source_name}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/models")
def get_models():
    try:
        return llm_service.get_models()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

# --- main.py ---

# עדכון ה-Endpoint לשמירה חכמה (כדי שיעבוד עם ה-JSON מה-Frontend)
@app.post("/api/ingest/text/smart")
async def ingest_text_smart(project: str, request: Request):
    try:
        data = await request.json()
        content = data.get("content", "")
        
        if not content:
            raise HTTPException(status_code=400, detail="No content provided")
        
        # לוגיקת ה-LLM והשמירה שלך...
        title_prompt = f"Generate a short title (max 5 words) for this:\n\n{content[:200]}"
        suggested_title = llm_service.generate_answer(title_prompt).strip().replace('"', '')
        
        vector_service.ingest_data(
            content=content, 
            source_name=suggested_title, 
            project_name=project, 
            source_type="manual"
        )
        return {"suggested_title": suggested_title}
    except Exception as e:
        print(f"Error in smart ingest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint חדש לשינוי שם של מקור (Source) קיים
@app.post("/api/projects/{project_name}/sources/rename")
def rename_source(project_name: str, old_name: str, new_name: str):
    try:
        collection = vector_service.client.get_collection(name=project_name)
        # שליפת כל ה-IDs ששייכים למקור הישן
        results = collection.get(where={"source": old_name})
        if not results['ids']:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # עדכון ה-Metadata עבור כל ה-Chunks של אותו מקור
        new_metadatas = [{"source": new_name, "type": m.get("type", "manual")} for m in results['metadatas']]
        collection.update(ids=results['ids'], metadatas=new_metadatas)
        
        return {"message": "Source name updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Endpoint לשליפת היסטוריית צ'אט עבור פרויקט ומשתמש ספציפי
@app.get("/api/chat/history")
async def get_chat_history(project: str, user_id: str = "user_1"):
    try:
        # שליפת כל ההודעות שמתאימות למשתמש ולפרויקט, מסודרות לפי זמן מהישן לחדש
        cursor = chat_collection.find(
            {"user_id": user_id, "project_id": project},
            {"_id": 0} # אנחנו מתעלמים מה-ID הפנימי של מונגו כדי שלא יעשה בעיות ב-JSON
        ).sort("timestamp", 1)
        
        history = list(cursor)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

# פונקציית עזר (או Endpoint) לשמירת הודעה חדשה
# אתה תרצה לקרוא לזה בתוך ה-Endpoint של ה-/ask שלך, גם עבור ה-user וגם עבור ה-ai
def save_chat_message(project: str, role: str, text: str, user_id: str = "user_1"):
    try:
        message_doc = {
            "user_id": user_id,
            "project_id": project,
            "role": role,         # 'user' או 'ai'
            "text": text,
            # "timestamp": datetime.datetime.utcnow() # זמן שמירה בשעון בינלאומי
            "timestamp": datetime.datetime.now(datetime.timezone.utc) 
        }
        chat_collection.insert_one(message_doc)
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")

# 4. עדכון ה-clear_memory הקיים שלך כדי שימחוק גם ממונגו
@app.post("/clear_memory")
async def clear_memory(project: str, session_id: str = "user_1"):
    try:
        # מחיקת כל ההודעות ששייכות למשתמש הספציפי בפרויקט הספציפי
        result = chat_collection.delete_many({"user_id": session_id, "project_id": project})
        print(f"Memory cleared from MongoDB for session: {session_id}, documents deleted: {result.deleted_count}")

        return {"status": "success", "message": f"Deleted {result.deleted_count} messages"}
    except Exception as e:
        print(f"Error clearing MongoDB: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear history")
        