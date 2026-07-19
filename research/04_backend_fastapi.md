# Topic 4 — Backend (FastAPI) Design

**Status:** Phase 2 — Deep Dive (in progress)
**Last update:** 2026-07-10

---

## Open questions

1. **Framework**: FastAPI (confirmed), but:
   - Python version (3.11 / 3.12 / 3.13).
   - ASGI server: `uvicorn` vs `granian` vs `hypercorn`.
   - Project layout: src vs flat, modular routers.
2. **Endpoints** (draft):
   - `POST /auth/register` — email + password
   - `POST /auth/login` — email + password → session
   - `POST /auth/otp/request` — request email OTP
   - `POST /auth/otp/verify` — verify OTP
   - `GET /me` — current user
   - `POST /chat` — non-streaming chat (for testing)
   - `POST /chat/stream` — SSE stream of tokens
   - `GET /conversations` — list
   - `GET /conversations/{id}` — fetch
   - `DELETE /conversations/{id}`
   - `POST /admin/docs` — upload new PDF
   - `GET /admin/docs` — list versions
   - `POST /admin/docs/{id}/reindex` — trigger re-index
   - `POST /admin/docs/{id}/disable`
   - `POST /admin/test` — test question against a candidate index
   - `GET /admin/logs` — paginated question logs
   - `GET /admin/logs/top` — top asked questions
3. **Conversation memory**:
   - Store full messages? Sliding window of last N turns? Summary + recent turns?
4. **Background jobs** for re-indexing:
   - FastAPI BackgroundTasks (simple, lost on restart)
   - ARQ / RQ / Celery / Dramatiq / Prefect
   - Just run synchronously with a progress endpoint?
5. **Database**:
   - PostgreSQL (recommended for portability and reliability)
   - SQLite for dev
   - What stores what: users, sessions, conversations, messages, documents, chunks, logs.
6. **ORM**:
   - SQLAlchemy 2.x (async) — battle-tested.
   - SQLModel — nice DX, but smaller community.
   - Tortoise ORM — async-first.
7. **Migrations**: Alembic.
8. **Validation**: Pydantic v2.
9. **Configuration**: pydantic-settings + `.env`.
10. **Testing**: pytest, pytest-asyncio, httpx async client.
11. **Rate limiting**: slowapi / custom middleware.

---

## Findings (append below)


## Findings — FastAPI + RAG patterns

### Source 1 — Reddit r/Rag "RAG Implementation: With LlamaIndex/LangChain or Without Libraries?" (Feb 2025)
- "I tried both. Then, gave up using libraries because when there is a new update with some other stuff, RAG frameworks gave error." — A production engineer.
- "RAG frameworks offer great ideas. Get familiar with them. If you see anything useful, write a code for that specific part."
- Counter-voice: "LlamaIndex for data loading. You don't need to know how to curl a web page and turn it into markdown. Raw dog the rest - you'll get to really learn which levers have what effect."

### Source 2 — Reddit r/LangChain (Jul 2024) — feedback on similar stack
- "PyMuPDF is solid open source option. Other options: Unstructured, deepdoctection and marker, layout-parser."
- "Chunking / cleaning: spacy + tiktoken to roll your own. Or use unstructured / langchain."
- "You will get best results with hierarchal chunking (ie. split recursively first on sentences then paragraphs etc until you have the desired chunk size). Build in some overlap between the chunks for more robust retrieval results."
- "Calling the LLMs / embedding models: Langchain is great for prototyping and smaller projects but very quickly starts getting in the way in my experience. Often calling the LLM providers directly with tenacity or similar for retries is the way to go. If you want a thin wrapper around the different providers I would recommend litellm."
- "Storing vectors and semantic retrieval: Postgres + pgvector + ts_rank for hybrid search. Reranking: Cohere API to rerank the retrieved chunks."
- Production-grade setup confirmed: **PyMuPDF + pgvector + ts_rank hybrid search + Cohere rerank + calling LLM providers directly via litellm.** No LangChain/LlamaIndex.

### Source 3 — Medium "Mastering LangChain RAG: Implementing Streaming Capabilities" (Jun 2024)
- Streaming via `StreamingResponse` + SSE in FastAPI.
- Use `langchain_core.runnables.RunnablePassthrough` for chain composition.
- Pattern: contextualize question with chat history, then retrieve, then answer.
- For our project: we DON'T need LangChain. We can do the same with direct API calls + async generators.

### Source 4 — Medium "8 LangChain vs LlamaIndex Calls You'll Actually Make" (Sep 2025)
- "For front-end SSE and observability dashboards, both are fine."
- LangChain: "rich parser ecosystem, LangSmith tracing."
- LlamaIndex: "Programs are elegant for single-schema tasks, FaithfulnessEvaluator for eval."

### Implication for our project
- **Don't use LangChain or LlamaIndex.** Reasons:
  1. We only have one LLM (DeepSeek) and one vector store (pgvector). The framework overhead isn't worth it.
  2. Frameworks have version-drift problems (Reddit testimony).
  3. Our prompt is strict and small — we can write it inline.
  4. Easier to debug, easier for another dev to read.
- **Do use:**
  - `litellm` or direct `httpx` calls to DeepSeek (OpenAI-compatible API).
  - `asyncpg` + `pgvector` via raw SQL or `sqlalchemy[asyncio]` with the `pgvector` SQLAlchemy type.
  - `pymupdf4llm` + custom chunker.
  - `tenacity` for retry-with-backoff on LLM calls.
  - `sse-starlette` for SSE streaming (well-maintained, used by FastAPI community).
- **Chat pipeline** (no framework, hand-rolled):
  ```
  user_message
    → normalize Arabic
    → embed (Jina v3)
    → hybrid search (pgvector cosine + tsvector BM25)
    → optionally rerank (BGE reranker)
    → build prompt (system + retrieved chunks + history + new question)
    → stream from DeepSeek v4-flash
    → on the fly, parse out citation markers
    → return SSE events: {token: "..."} then {sources: [...]} then {done: true}
  ```

### Project structure (recommended)
```
backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS, middleware
│   ├── core/
│   │   ├── config.py            # pydantic-settings (env)
│   │   ├── db.py                # asyncpg engine + session
│   │   ├── security.py          # password hash, JWT
│   │   └── deps.py              # FastAPI dependencies (current_user, db, etc.)
│   ├── models/                  # SQLAlchemy ORM
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── chunk.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   └── log.py
│   ├── schemas/                 # Pydantic v2
│   │   ├── auth.py
│   │   ├── chat.py
│   │   └── admin.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── conversations.py
│   │   ├── admin_docs.py
│   │   ├── admin_logs.py
│   │   └── health.py
│   ├── services/
│   │   ├── llm.py               # DeepSeek client (litellm or direct httpx)
│   │   ├── embeddings.py        # Jina v3 client
│   │   ├── retrieval.py         # hybrid search + rerank
│   │   ├── ingestion.py         # PDF → chunks
│   │   ├── arabic.py            # normalization
│   │   ├── email.py             # send OTP
│   │   └── prompt.py            # prompt templates + system prompt
│   └── tasks/
│       └── reindex.py           # background reindex job
├── migrations/                  # Alembic
├── tests/
├── scripts/
│   ├── seed_admin.py
│   └── server-install-and-validate.sh
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

