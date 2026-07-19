"""
Master FastAPI Application (`src/backend/main.py`).

Initializes the Universal Relational RAG & Obsidian Graph Backend:
- Configures CORS middleware for Next.js Cyrkil GUI (`localhost:3000`, `chat.cyrkil.com`).
- Mounts modular routers (`/api/v1/documents`, `/api/v1/chat`).
- Initializes relational multi-document tables (`init_db`) on application startup via modern Lifespan handler.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from .db.session import init_db
    from .api import documents_router, chat_router
except ImportError:
    from db.session import init_db
    from api import documents_router, chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize persistent database tables on startup cleanly without deprecation warnings."""
    await init_db()
    yield


app = FastAPI(
    title="Cyrkil Universal Knowledge Workspace & Arabic/English Staff Chatbot API",
    description="Relational structural RAG streaming backend without vector DBs, featuring Obsidian Graph View network queries and dynamic API key management.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration enabling Next.js 15 frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/health", tags=["system"])
async def health_check():
    """System health check endpoint."""
    return {"status": "healthy", "version": "1.0.0", "system": "Cyrkil Universal RAG Backend"}
