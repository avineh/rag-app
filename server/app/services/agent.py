from pydantic_ai import Agent, RunContext
from app.services.vector_service import vector_service
from app.services.llm_service import llm_service
from app.core.config import settings # ייבוא ההגדרות המרכזי[cite: 3]
from pydantic import BaseModel

# מבנה נתונים לתוצאת חיפוש
class SearchResult(BaseModel):
    content: str
    source: str

model_instance = llm_service._get_best_model()

agent = Agent(
    model_instance, 
    deps_type=str, 
    system_prompt=settings.SYSTEM_PROMPT
)

@agent.tool
async def search_project_docs(ctx: RunContext[str], query: str) -> list[SearchResult]:
    """
    חיפוש מידע במסמכי הפרויקט הנוכחי.
    """
    try:
        project_name = ctx.deps  
        
        print(f"DEBUG: Searching for '{query}' in project '{project_name}'") #####
        results = vector_service.search(query, project_name)
        print(f"DEBUG: Found {len(results.get('documents', [[]])[0])} results") #####
        
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
        