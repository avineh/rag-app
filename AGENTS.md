# AI Agent Guide for RAG Chat Application

## Project Overview
This is a Retrieval-Augmented Generation (RAG) system that combines local embeddings, vector search, and AI agents to answer questions about ingested documents.

**Tech Stack:**
- FastAPI (HTTP server)
- Chroma (persistent vector database)
- SentenceTransformers (local embeddings - `all-MiniLM-L6-v2`)
- PydanticAI (agent orchestration with tools)
- Google Gemini (LLM backend)

## System Architecture

### Core Services (`server/app/services/`)

1. **agent.py** - PydanticAI agent with tool integration
   - `search_project_docs()` - Main tool that retrieves context from vector DB
   - Takes `project_name` as dependency context
   - Returns structured `SearchResult` objects

2. **vector_service.py** - Vector database operations
   - `ingest_data()` - Split text into 1000-char chunks (100 overlap), embed, and store
   - `search()` - Query vector DB for top 3 similar chunks
   - `list_projects()` / `delete_project()` - Multi-tenancy support via Chroma collections
   - **Note:** All chunks are stored per project collection with metadata

3. **llm_service.py** - LLM integration
   - Automatically selects best available Gemini model (prefers `gemini-flash-lite-latest`)
   - Used by agent as default model

### API Endpoints (`server/app/main.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ask` | GET | Query the agent with optional project context |
| `/api/projects` | GET | List all projects |
| `/api/projects/{name}` | DELETE | Remove entire project |
| `/api/projects/{name}/reset` | POST | Clear project context |
| `/api/files/upload` | POST | Ingest file into project |
| `/api/ingest/text` | POST | Ingest text string into project |

## How to Modify and Extend

### Adding a New Tool to the Agent
1. Define tool function with `@agent.tool` decorator in [agent.py](server/app/services/agent.py#L22)
2. Include `ctx: RunContext[str]` parameter and return typed results
3. Tool automatically becomes available to agent (no manual registration needed)

**Example:**
```python
@agent.tool
async def new_capability(ctx: RunContext[str], param: str) -> OutputType:
    """Tool description for agent to understand when to use it."""
    # Use ctx.deps to access project_name context
    return result
```

### Modifying Chunking Strategy
Edit [vector_service.py](server/app/services/vector_service.py#L13-L17):
- `chunk_size`: Currently 1000 chars (good for Q&A)
- `chunk_overlap`: Currently 100 chars (preserves context across chunks)
- `separators`: Order matters - splits on double newlines first

### Changing LLM Model
Edit [config.py](server/app/core/config.py#L3):
- `GEMINI_API_KEY`: Store in `.env` file instead of hardcoding
- Modify `_get_best_model()` in [llm_service.py](server/app/services/llm_service.py#L5) for different selection logic

## Development Workflow

### Running the Application
```powershell
cd server
uvicorn app.main:app --reload
```
Server runs on `http://localhost:8000`

### Testing
Existing test scripts in `server/app/tests/`:
- `seed_data.py` - Populate DB with sample documents
- `search.py` - Test vector search directly
- `check_db.py` - Inspect Chroma database
- `rag_app.py` - Test full RAG pipeline

Run with: `python server/app/tests/{script_name}.py`

### Adding Documents
1. Use `/api/files/upload` for files (currently UTF-8 text only)
2. Use `/api/ingest/text` for raw text strings
3. Both create project collection if it doesn't exist
4. Automatic chunking and embedding happens server-side

## Configuration

**Environment Variables** (in `.env`):
- `GEMINI_API_KEY` - Google Gemini API key
- `CHROMA_PATH` - Vector DB storage path (default: `./chroma_data`)
- `COLLECTION_NAME` - Default project name (default: `my_documents`)

See [config.py](server/app/core/config.py) for all settings.

## Key Constraints & Conventions

- **Hebrew support**: Code comments are in Hebrew; agent responses use the language of the input query
- **Project isolation**: Each project is a separate Chroma collection (multi-tenancy built-in)
- **Local embeddings**: No API calls for embeddings (privacy + cost), but model is small (~400MB)
- **Single default LLM**: All agents share one Gemini model instance
- **Metadata preservation**: All chunks store `source`, `type` (file/text), `project`, and `chunk_index`

## Common Patterns

**To help the agent answer questions better:**
1. Ensure documents are chunked coherently (current 1000-char chunks are good for Q&A)
2. Provide rich metadata - agent sees source and chunk position
3. Test edge cases with `/api/ingest/text` before uploading files

**When debugging:**
- Check `chroma_data/` directory for persisted databases
- Use test scripts to isolate vector search from agent logic
- Verify `.env` file exists and GEMINI_API_KEY is valid

