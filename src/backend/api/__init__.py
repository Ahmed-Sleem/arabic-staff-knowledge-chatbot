"""API package containing modular FastAPI endpoints for documents and chat streaming."""
from .documents import router as documents_router
from .chat import router as chat_router
