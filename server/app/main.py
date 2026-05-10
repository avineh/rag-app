from fastapi import FastAPI, File, Query, HTTPException, UploadFile, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import fitz  # PyMuPDF
from app.services.vector_service import vector_service
from app.services.agent import agent
from app.core.config import settings
from pydantic_ai.messages import ModelMessage

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
chat_histories: Dict[str, List[ModelMessage]] = {}

# --- Endpoints ---

@app.get("/ask")
async def ask(
    question: str, 
    project: str, 
    session_id: str, 
    system_prompt: str = None 
):
    # 1. לוגיקת ברירת מחדל לפרומפט ופרויקט
    actual_prompt = system_prompt or settings.DEFAULT_PROMPT
    target_project = project or settings.COLLECTION_NAME
    
    # 2. ניהול היסטוריה (לוודא שה-session קיים)
    if session_id not in chat_histories:
        chat_histories[session_id] = []

    async def stream_generator():
        # שימוש ב-run_stream לקבלת תשובה זורמת מהסוכן של PydanticAI
        # ה-actual_prompt מוזרק כאן כהודעת מערכת
        async with agent.run_stream(
            question, 
            deps=target_project, 
            message_history=chat_histories[session_id]
        ) as result:
            
            async for chunk in result.stream_text(delta=True):
                yield chunk
            
            # בסיום ההזרמה, מעדכנים את היסטוריית ההודעות בזיכרון השרת
            chat_histories[session_id] = result.all_messages()

    return StreamingResponse(stream_generator(), media_type="text/plain")

@app.post("/clear_memory")
async def clear_memory(session_id: str):
    if session_id in chat_histories:
        chat_histories[session_id] = []
        print(f"Memory cleared for session: {session_id}")
        return {"status": "success", "message": "History cleared"}
    return {"status": "not_found", "message": "Session not found"}

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
                for page in doc:
                    text += page.get_text()
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
        sources = set()
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