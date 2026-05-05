import os
from dotenv import load_dotenv # 1. ייבוא הפונקציה
from pydantic_ai import Agent, RunContext
from app.services.vector_service import vector_service
from app.services.llm_service import llm_service
from pydantic import BaseModel

# 2. טעינת ה-env לזיכרון המערכת באופן אוטומטי
load_dotenv()

# מבנה נתונים לתוצאת חיפוש
class SearchResult(BaseModel):
    content: str
    source: str

# שליפת שם המודל דרך השירות שכבר עבר אופטימיזציה (Caching)
model_name = llm_service._get_best_model()

# הבטחת פורמט השם עבור PydanticAI
if not model_name.startswith('google-gla:'):
    model_name = f'google-gla:{model_name}'

# הגדרת הסוכן
agent = Agent(
    model_name,
    deps_type=str,
    system_prompt=(
        "אתה עוזר מקצועי המבוסס על מסמכי פרויקט. "
        "השתמש בכלי החיפוש כדי למצוא הקשר רלוונטי לפני מתן תשובה. "
        "אם המידע לא נמצא במסמכים, ענה על סמך הידע הכללי שלך אך ציין שזה לא מהמסמכים."
    ),
)

@agent.tool
async def search_project_docs(ctx: RunContext[str], query: str) -> list[SearchResult]:
    """
    חיפוש מידע במסמכי הפרויקט הנוכחי.
    """
    try:
        project_name = ctx.deps  
        results = vector_service.search(query, project_name)
        
        # סעיף 3: הגנה מפני תוצאות ריקות או שגיאות בחיפוש
        if not results or not results.get('documents') or not results['documents'][0]:
            return []
            
        formatted_results = []
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            formatted_results.append(SearchResult(
                content=doc, 
                source=meta.get('source', 'unknown')
            ))
        return formatted_results
        
    except Exception as e:
        print(f"Error in search_project_docs: {e}")
        return []
    