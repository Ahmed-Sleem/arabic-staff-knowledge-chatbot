"""API package containing modular FastAPI endpoints for documents, chat streaming, and encrypted device vault profiles."""
from .documents import router as documents_router
from .chat import router as chat_router
from .vault import router as vault_router
