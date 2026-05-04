from fastapi import FastAPI, UploadFile, File, Query
from app.services.llm_service import llm_service
# כאן נוסיף בהמשך את ה-vector_service
from app.services.vector_service import vector_service


app = FastAPI(title="RAG Chat App")

# עדכון ה-Ask לתמיכה בפרויקט
@app.get("/ask")
def ask_ai(question: str, project: str = Query(..., description="שם הפרויקט לחיפוש")):
    results = vector_service.search(question, project)
    
    if not results or not results['documents'][0]:
        return {"answer": "לא נמצא מידע בפרויקט זה."}

    context_text = "\n---\n".join(results['documents'][0])
    
    # ב: הפניה שקופה למקורות כולל שם הקובץ והסוג
    sources = []
    for meta in results['metadatas'][0]:
        sources.append(f"Source: {meta['source']} ({meta['type']})")

    prompt = f"Context:\n{context_text}\n\nQuestion: {question}\nAnswer:"
    answer = llm_service.generate_answer(prompt)
    
    return {"answer": answer, "sources": list(set(sources))}


# העלאת קבצים לפרויקט
@app.post("/api/files/upload")
async def upload_file(project: str, file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8") # כרגע תומך ב-txt. ל-pdf נצטרך ספריה נוספת
    num_chunks = vector_service.ingest_data(text, file.filename, project, source_type="file")
    return {"message": f"File '{file.filename}' ingested into project '{project}'"}


# א+ג: העלאת טקסט חופשי לפרויקט
@app.post("/api/ingest/text")
async def ingest_text(content: str, project: str, source_label: str = "manual_entry"):
    num_chunks = vector_service.ingest_data(content, source_label, project, source_type="text")
    return {"message": f"Added {num_chunks} chunks to project '{project}'"}

# הצגת כל הפרויקטים
@app.get("/api/projects")
def get_all_projects():
    projects = vector_service.list_projects()
    return {"projects": projects}

# מחיקת פרויקט
@app.delete("/api/projects/{project_name}")
def delete_project(project_name: str):
    success = vector_service.delete_project(project_name)
    if success:
        return {"message": f"Project '{project_name}' deleted successfully."}
    return {"error": f"Project '{project_name}' not found."}, 404