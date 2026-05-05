from fastapi import FastAPI, File, Query, HTTPException, UploadFile, Request
from fastapi.responses import StreamingResponse
from app.services.vector_service import vector_service
from app.services.agent import agent
from app.core.config import settings
from pydantic_ai.messages import ModelMessage
from typing import List, Dict
import fitz  # PyMuPDF

app = FastAPI(title="RAG Chat App with PydanticAI")

# --- Middleware (משימה 9) ---
@app.middleware("http")
async def simple_auth_middleware(request: Request, call_next):
    # מאפשרים גישה חופשית לתיעוד ה-API
    if request.url.path in ["/docs", "/openapi.json"]:
        return await call_next(request)
        
    # בדיקת ה-Token ב-Header
    token = request.headers.get("X-API-TOKEN")
    if token != settings.API_TOKEN:
        return StreamingResponse(iter(["Unauthorized access: Invalid Token"]), status_code=401)
        
    return await call_next(request)

# מאגר זכרון זמני להיסטוריית השיחות (בייצור כדאי להשתמש ב-Redis)
chat_histories: Dict[str, List[ModelMessage]] = {}

# עדכון ה-Ask לתמיכה בפרויקט ושימוש בסוכן החדש (שכבר כולל את היכולת לחפש ב-VectorDB)
@app.get("/ask")
async def ask_ai(
    question: str, 
    session_id: str = "default", 
    project: str = Query(None)
):
    """
    Endpoint התומך ב-Streaming ובהיסטוריית שיחה.
    """
    target_project = project or settings.COLLECTION_NAME
    
    # שליפת היסטוריית השיחה הקודמת או יצירת חדשה
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    
    async def stream_generator():
        # שימוש ב-run_streaming לקבלת תשובה זורמת
        async with agent.run_stream(
            question, 
            deps=target_project, 
            message_history=chat_histories[session_id]
        ) as result:
            
            async for chunk in result.stream_text(delta=True):
                yield chunk
            
            # בסיום ההזרמה, שומרים את כל חילופי הדברים בזיכרון
            chat_histories[session_id] = result.all_messages()

    return StreamingResponse(stream_generator(), media_type="text/plain")

# --- תשתית לניהול פרויקטים ---
# החזרת רשימת פרויקטים קיימים
@app.get("/api/projects")
def list_projects():
    return {"projects": vector_service.list_projects()}

# מחיקת פרויקט שלם
@app.delete("/api/projects/{project_name}")
def delete_project(project_name: str):
    success = vector_service.delete_project(project_name)
    return {"message": "Deleted"} if success else {"error": "Not found"}

# איפוס פרויקט (מחיקת תוכן בלי למחוק את הפרויקט עצמו)
@app.post("/api/projects/{project_name}/reset")
def reset_project(project_name: str):
    """מוחק את המידע (context) מבלי למחוק את הפרויקט עצמו"""
    # פשוט מוחקים ויוצרים מחדש - זו הדרך הכי נקיה ב-Chroma
    vector_service.delete_project(project_name)
    vector_service.client.get_or_create_collection(name=project_name)
    return {"message": f"Context for {project_name} cleared."}

# העלאת טקסט חופשי לפרויקט
@app.post("/api/ingest/text")
async def ingest_text(content: str, project: str, source_label: str = "manual_entry"):
    num_chunks = vector_service.ingest_data(content, source_label, project, source_type="text")
    return {"message": f"Added {num_chunks} chunks to project '{project}'"}

# העלאת קבצים לקונטקסט של הפרויקט
# @app.post("/api/files/upload")
# async def upload_file(project: str, file: UploadFile = File(...)):
#     content = await file.read()
#     text = content.decode("utf-8") # כרגע תומך ב-txt. ל-pdf נצטרך ספריה נוספת
#     num_chunks = vector_service.ingest_data(text, file.filename, project, source_type="file")
#     return {"message": f"File '{file.filename}' ingested into project '{project}'"}

@app.post("/api/files/upload")
async def upload_file(project: str, file: UploadFile = File(...)):
    filename = file.filename
    content = await file.read()
    text = ""

    try:
        if filename.endswith(".pdf"):
            # חילוץ טקסט מ-PDF
            with fitz.open(stream=content, filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text()
        elif filename.endswith(".txt"):
            # קובץ טקסט רגיל
            text = content.decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="סיומת קובץ לא נתמכת. נא להעלות PDF או TXT בלבד.")

        if not text.strip():
            raise HTTPException(status_code=400, detail="הקובץ ריק או שלא ניתן היה לחלץ ממנו טקסט.")

        # שליחה ל-VectorService לעיבוד ושמירה[cite: 6]
        num_chunks = vector_service.ingest_data(
            content=text, 
            source_name=filename, 
            project_name=project, 
            source_type="file"
        )
        
        return {
            "message": f"הקובץ '{filename}' עובד בהצלחה.",
            "chunks": num_chunks,
            "project": project
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בעיבוד הקובץ: {str(e)}")