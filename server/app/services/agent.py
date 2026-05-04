import os
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from app.services.vector_service import vector_service
from app.services.llm_service import llm_service
from pydantic import BaseModel

# טעינה מפורשת של משתני הסביבה לתוך המערכת (OS)
load_dotenv() 

class SearchResult(BaseModel):
    content: str
    source: str

model_name = llm_service._get_best_model()
if not model_name.startswith('google-gla:'):
    model_name = f'google-gla:{model_name}'

# עכשיו הסוכן ימצא את GOOGLE_API_KEY בתוך המערכת בזכות load_dotenv()
agent = Agent(
    model_name,
    deps_type=str,
    system_prompt=(
        "אתה עוזר מקצועי המבוסס על מסמכי פרויקט. "
        "השתמש בכלי החיפוש כדי למצוא הקשר רלוונטי לפני מתן תשובה. "
        "אם המידע לא נמצא במסמכים, ציין זאת במפורש."
    ),
)

@agent.tool
async def search_project_docs(ctx: RunContext[str], query: str) -> list[SearchResult]:
    # ... הלוגיקה שלך לחיפוש נשארת זהה ...
    project_name = ctx.deps  
    results = vector_service.search(query, project_name)
    
    formatted_results = []
    if results and results['documents'] and results['documents'][0]:
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            formatted_results.append(SearchResult(
                content=doc, 
                source=meta.get('source', 'unknown')
            ))
    return formatted_results