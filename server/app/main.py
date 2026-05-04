from fastapi import FastAPI, File, Query, HTTPException, UploadFile
from app.services.vector_service import vector_service
from app.services.agent import agent  # הסוכן החדש שיצרנו
from app.core.config import settings

app = FastAPI(title="RAG Chat App with PydanticAI")

# עדכון ה-Ask לתמיכה בפרויקט ושימוש בסוכן החדש (שכבר כולל את היכולת לחפש ב-VectorDB)
@app.get("/ask")
async def ask_ai(question: str, project: str = Query(None)):
    # 1. קביעת הפרויקט (דיפולט אם לא נשלח)
    target_project = project or settings.COLLECTION_NAME # "my_documents"
    
    try:
        # 2. הרצת הסוכן - הוא כבר יקרא ל-Tool של החיפוש לבד!
        result = await agent.run(question, deps=target_project)
        return {"answer": result.output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

# העלאת קבצים לקונטקסט של הפרויקט
@app.post("/api/files/upload")
async def upload_file(project: str, file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8") # כרגע תומך ב-txt. ל-pdf נצטרך ספריה נוספת
    num_chunks = vector_service.ingest_data(text, file.filename, project, source_type="file")
    return {"message": f"File '{file.filename}' ingested into project '{project}'"}

# העלאת טקסט חופשי לפרויקט
@app.post("/api/ingest/text")
async def ingest_text(content: str, project: str, source_label: str = "manual_entry"):
    num_chunks = vector_service.ingest_data(content, source_label, project, source_type="text")
    return {"message": f"Added {num_chunks} chunks to project '{project}'"}


