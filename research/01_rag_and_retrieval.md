# Topic 1 — RAG & Retrieval Design (Arabic)

**Status:** Phase 2 — Deep Dive (in progress)
**Last update:** 2026-07-10

---

## Open questions

1. Which **embeddings model** gives the best Arabic retrieval quality?
2. Which **vector store** is right for our use case?
3. **Chunking** strategy for Arabic
4. **Re-ranking** — do we need a cross-encoder reranker?
5. **Hybrid search** — BM25 + dense?
6. **Citation grounding** — how to make the LLM cite section/page reliably?
7. **Confidence score** — how to compute it?
8. **Query expansion / HyDE** — useful for Arabic?
9. **Which RAG architecture** — naive, advanced, agentic, tool-based?

## Architecture options (the big question)

### Option 1 — Naive RAG (the "vending machine")
**Flow:** User question → embed → top-k from vector store → LLM
- **Pros:** Simplest. Fastest. Cheapest. ~80% of the way there for clean docs.
- **Cons:** Misses exact matches (HSE, PMO, KPI). Misses when the user asks in a paraphrase. No self-correction. Tends to retrieve top-3 visually-similar but factually-wrong chunks.
- **When to use:** Tiny KB, simple QA pattern, demo-grade.

### Option 2 — Advanced RAG (the "short-order cook")
**Flow:** User question → normalize → embed → **hybrid search (dense + BM25)** → **RRF fusion** → **rerank** → LLM
- **Pros:** Handles paraphrases AND exact matches. 15-30% accuracy improvement over naive in production. Industry standard for single-doc RAG. Per Medium research: Advanced RAG hits 0.797 faithfulness vs 0.621 for naive.
- **Cons:** More components to build. Slightly more latency. Needs tuning of weights and k.
- **When to use:** Production-grade single-document QA. **← This is our sweet spot.**

### Option 3 — Agentic RAG (the "sous chef")
**Flow:** User question → LLM plans → LLM picks tools (search, BM25, vector, etc.) → LLM evaluates → LLM re-searches if needed → LLM answers
- **Pros:** Multi-hop reasoning. Self-correction. Adapts to query complexity. Can blend structured + unstructured sources.
- **Cons:** 3-5x more cost per query. 14ms+ framework overhead (LangGraph). Much more complex to build, debug, test. Higher latency. Most teams report the extra reasoning power is wasted on simple Q&A.
- **When to use:** Complex research, multi-source verification, legal/medical/financial analysis.
- **Verdict for us:** **Overkill.** Our PDF is one document. The questions are mostly direct ("who reports to X?", "what are the KPIs for Y?"). No multi-hop needed.

### Option 4 — HyDE (Hypothetical Document Embeddings)
**Flow:** User question → LLM generates a hypothetical answer → embed the hypothetical answer → top-k from vector store → LLM
- **Pros:** Bridges the "terse query vs verbose document" gap. Good for ambiguous queries.
- **Cons:** +1 LLM call per query = +25-60% latency. Hypothetical answer can hallucinate and lead to bad retrieval. The Springer 2025 paper shows it's bad for "well-specified, fact-bound domains" like our HR policy (where the question is precise and the answer is exact).
- **When to use:** Ambiguous open-ended questions, scientific Q&A, "explain X" prompts.
- **Verdict for us:** **Not appropriate.** Our users ask specific factual questions. A generated hypothetical answer would add noise.

### Option 5 — "Pre-router with section titles" (your "give the model the titles" idea)
**Flow:** Build a "section catalog" (every section's title + 1-line summary). On a user question: → embed question + section titles → top-5 matching sections → LLM gets the FULL content of those sections → answer.
- **Pros:** Faster (no need to embed every chunk). More precise (the LLM knows which sections to look in). Like a librarian pointing the user to the right shelf. Works great when sections map cleanly to questions.
- **Cons:** Doesn't help when the answer spans multiple sections. Doesn't help when the question doesn't map to a section title. For 64-page PDF it's actually overkill — full text fits in context (16,700 words ≈ 20K tokens, well within DeepSeek's 64K window).
- **When to use:** Large documents (1000+ pages), or when chunks are too granular.
- **Verdict for us:** **Not for MVP, but a powerful v2 idea.** A two-stage "section router + chunk retrieval" would be very effective for our use case. We could build it after the basic RAG works.

### Option 6 — "Two-stage agentic with titles + chunks" (your other idea)
**Flow:** Embed all section titles. On user question → LLM sees the question + the list of section titles → LLM returns a list of titles it wants to see → retrieve those sections in full → LLM answers.
- **Pros:** LLM-controlled retrieval. Adaptive. Handles multi-section questions.
- **Cons:** The LLM has to "know" what sections exist, which it can't unless we show it. This is essentially the same as Option 5 but with the LLM choosing instead of embedding similarity choosing.
- **When to use:** Same as Option 5.
- **Verdict for us:** **Worth considering as a v2 upgrade.** But it adds LLM call latency and is more complex than needed for MVP.

### The 64-page reality
- Our PDF is **only 64 pages, 16,700 Arabic words ≈ 20,000 tokens.**
- DeepSeek v4-flash has a **64K context window.**
- The **entire PDF fits in one LLM call.**
- This is the key insight: for this specific document, you could literally paste the whole thing into the prompt and get perfect answers.
- But: cost, latency, and "lost in the middle" effects make this bad for a chat UX.
- So we still need RAG. But the "library" is small, the chunk count is small, and retrieval precision matters more than recall.

## Findings — Embedding models (Arabic RAG, 2025–2026)

**Headline conclusion:** For Arabic RAG, **BGE-M3** and **multilingual-e5-large** are the most-cited winners in published benchmarks, and **Jina v3** is a strong hosted alternative.

### Source 1 — arxiv.org "Optimizing RAG Pipelines for Arabic" (Jun 2025)
URL: https://arxiv.org/html/2506.06339v1
- BGE-M3: 70.99 overall avg across 6 Arabic datasets (highest).
- multilingual-e5-large: 70.31 (second).
- Arabic-specialized models (Arabic-Triplet-Matryoshka-V2): 66.46.
- **Verdict:** "multilingual, contrastively trained models such as bge-m3 and multilingual-e5-large provide superior retrieval performance in Arabic RAG pipelines."

### Source 2 — Reddit r/LocalLLaMA, multilingual thread (2024–2025)
- "Tested a lot of multilingual embedding models, even the new Qwen. The best one for me is still BGE-m3 by a lot."

### Source 3 — MTEB leaderboard 2026 (app.ailog.fr)
| Rank | Model | MTEB v2 | License |
|---|---|---|---|
| 1 | Harrier-OSS-v1-27B | 74.3 | Free (MIT) but 27B params |
| 2 | Gemini Embedding 2 | 68.32 | Hosted |
| 3 | Jina v5-text-small | 71.7 | Free (Apache) |
| 4 | Qwen3-Embedding-8B | 70.58 | Free (Apache) but 8B |
| 8 | BGE-M3 | 63.0 | Free (MIT) |
| 10 | all-MiniLM-L6-v2 | 56.3 | Free |

### Source 4 — Future AGI 2026 guide
- "BGE-M3 supports 100+ languages and is the open-weight leader on multilingual retrieval."
- "Hybrid retrieval (dense + sparse + reranker) is the May 2026 default in production RAG, and BGE-M3 ships all three modes in one model."

### Source 5 — Jina v3 announcement
- 89 languages, Arabic among the top-30. Matryoshka (truncate to 32 dims). 8K context. Apache 2.0.

### Implication for our project
- **Don't need 8B embeddings.** A 568M-parameter BGE-M3 is plenty.
- **Bilingual / mixed Arabic-English queries** are expected (KPI, PMO, HSE). BGE-M3 and Jina v3 are both strong.

## Findings — Vector store options (free-tier, portable)

### Source 1 — Infrabase.ai 2026
- "Qdrant offers 1GB free forever. Turbopuffer starts at $64/mo. Self-hosting Milvus or pgvector costs only your infrastructure."
- "pgvector runs inside any PostgreSQL instance you already pay for, FAISS is in-memory and free, Chroma is open-source."

### Source 2 — Firecrawl guide 2026
- "Pinecone, Weaviate, and Qdrant are the strongest choices for most RAG workloads."
- "Weaviate has the best hybrid search, Qdrant offers the best free tier."

### Source 3 — DEV.to "Qdrant vs pgvector" (Jul 2026)
- Qdrant Cloud Free: 1GB free.
- "Qdrant close second with excellent filtering and recently added full-text search."

### Shortlist for our project
- **pgvector** — bundled with Postgres. **Top pick for portability (self-host).**
- **Qdrant** — best free tier, best filtering, Rust fast. **Top pick for cloud MVP.**
- **Weaviate** — best hybrid search as a single primitive. Good alternative.

### Our scale
- PDF is 64 pages, ~500 chunks at most.
- BGE-M3 is 1024 dims → 500 chunks × 1024 × 4 bytes = 2 MB of vectors. Trivially small.
- **Even the most generous free tier is 1000x more than we need.**

## Findings — Hybrid search (pgvector + BM25 + RRF)

### Source 1 — Reddit r/Rag "What's your experience with hybrid retrieval" (Feb 2026)
**Critical finding for our project.**
- "Vector alone misses acronyms, product codes, and proper nouns. I use pgvector (cosine) + BM25 via native PostgreSQL tsvector, fused with RRF."
- "Cross-encoder reranking: This was the single biggest quality jump after going hybrid. ms-marco-MiniLM-L-6-v2 as a second stage."
- "After reranking I also apply MMR to filter near-duplicate chunks."
- "Full pipeline: FAQ check → semantic cache → hybrid search (vector + BM25 + RRF) → cross-encoder rerank → MMR → LLM."

### Source 2 — jatinbansal.com "Hybrid Search: BM25 Meets Dense Vectors" (Jul 2026)
URL: https://jatinbansal.com/ai-engineering/hybrid-search/
- Confirmed: pgvector + tsvector + RRF. Working Python code.
- "Candidate counts matter more than weights. Fetch 50–200 candidates per retriever, fuse, then truncate to the final top_k."

### Source 3 — dev.to "Hybrid Search in 100 Lines" (Apr 2026)
- "plainto_tsquery parses raw user text into a tsquery without forcing them to know Postgres operators."
- "We pull k = 50 from each side even though the final answer is top-10. You want a deeper candidate pool than you ship."

### Source 4 — callsphere.ai (May 2026)
- Triple fusion: vector + tsvector + pg_trgm. Recall@10 jumps from 0.62 → 0.84+.

## Findings — RAG evaluation (Ragas, faithfulness, groundedness)

### Source 1 — qaskills.sh "RAG Evaluation Metrics 2026" (Jun 2026)
URL: https://qaskills.sh/blog/rag-evaluation-metrics-complete-2026
- **Faithfulness** / **Groundedness** — same idea: is every claim supported by retrieved context?
- **Context relevance** — does the retrieved set match what was needed?
- **Context precision** — are relevant chunks at the top? "Lost in the middle" effect.
- **Context recall** — of all the claims needed, how many were retrieved?
- **Answer relevancy** — does the answer address the question?

### Source 2 — comet.com "How to Evaluate RAG Systems" (Mar 2026)
URL: https://www.comet.com/site/blog/rag-evaluation/
- Confirmed: "lost in the middle" — LLMs attend to beginning and end, miss the middle.
- Tools: Ragas, Opik, Comet, TruLens.

## Findings — Actual structure of the HR PDF (the data file)

(See `research/03_pdf_ingestion.md` for full details.)
- 64 pages, ~16,700 Arabic words, 4-level numbered sections, clean Word-exported text.
- This is small enough that the **whole document fits in DeepSeek's 64K context** (20K tokens), but RAG is still the right choice for chat UX.

## Findings — Prompt injection / document injection

### Source 1 — tianpan.co "Document Injection" (Apr 2026)
URL: https://tianpan.co/blog/2026-04-15-document-injection-rag-pipeline
**Five defense layers:**
1. **Format normalization at ingestion** — convert untrusted docs to canonical format to strip invisible text, hidden layers, metadata.
2. **Language and entropy scoring** — flag suspicious chunks.
3. **Instruction-pattern classification** — BERT classifier for "ignore previous instructions" patterns.
4. **Prompt structure isolation** — wrap retrieved content in `<retrieved_document>` tags. System prompt forbids following instructions from retrieved content.
5. **Post-retrieval LLM verification** — for high-stakes, run a second LLM to check chunks.

### Source 2 — lakera.ai "Indirect Prompt Injection" (Dec 2025)
- "IPI doesn't target the prompt, it targets the data your AI ingests."
- "Fixing requires architecture, not vibes: trust boundaries, context isolation, output verification."

### Implication for our project
- **Our PDF is "trusted-ish"** (uploaded by HR admin). But the document is an attack surface.
- **Required mitigations:** Layer 4 (wrap chunks in tags, strict system prompt forbidding following instructions from context) + log all admin actions.

---

## ✅ Final locked RAG architecture (2026-07-10, end of discussion)

**Name:** Prompt-RAG + ReAct tool-calling hybrid (no vector DB)

### Core principle
- **No vector database. No embeddings.** We preprocess the PDF into a structured form (sections + KPI tables + escalation matrix) and store it in Postgres.
- **The LLM agent uses tools to navigate the structure.** Tools are deterministic Python functions. The LLM decides which tool to use per question.
- **Self-aware retries.** The model sees how many retries it has left and adapts.

### The structure (built at ingest, in Phase 1)
```sql
-- sections: the ToC, with full text
CREATE TABLE sections (
  id SERIAL PRIMARY KEY,
  section_id TEXT UNIQUE,            -- e.g. "7.1"
  parent_id TEXT,                    -- e.g. "7"
  level INT,                         -- 1, 2, 3, 4
  title_ar TEXT,                     -- Arabic title
  title_en TEXT,                     -- English title (extracted if present)
  summary TEXT,                      -- 1-line summary
  full_text TEXT,                    -- FULL section content
  page_start INT,
  page_end INT,
  document_id INT REFERENCES documents(id)
);

-- kpi_tables: structured KPI data per role
CREATE TABLE kpi_tables (
  id SERIAL PRIMARY KEY,
  role_name_ar TEXT,                 -- e.g. "مدير QHSE"
  section_id TEXT,                   -- e.g. "7.1"
  kpi_name TEXT,
  calculation TEXT,
  target TEXT,
  page INT,
  document_id INT
);

-- escalation_matrix: the escalation rules
CREATE TABLE escalation_matrix (
  id SERIAL PRIMARY KEY,
  topic TEXT,                        -- e.g. "financial", "contracts", "safety"
  first_escalation TEXT,             -- e.g. "direct manager"
  second_escalation TEXT,            -- e.g. "department manager"
  third_escalation TEXT,             -- e.g. "CEO"
  conditions TEXT,
  page INT,
  document_id INT
);

-- search_index: Postgres tsvector for keyword search (no vector DB)
CREATE TABLE search_index (
  id SERIAL PRIMARY KEY,
  content TEXT,
  content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
  section_id TEXT,
  document_id INT
);
CREATE INDEX idx_search_tsv ON search_index USING gin(content_tsv);
```

### The 5 tools (Python functions, exposed via OpenAI-style function calling)
1. **`list_sections(parent_id=None)`** — Returns the ToC. If `parent_id=None`, returns top-level sections. Otherwise, returns sub-sections of that parent. Each entry: `{section_id, title_ar, summary}`.
2. **`get_section(section_id)`** — Returns the FULL TEXT of a specific section.
3. **`search_keyword(query)`** — Returns matching sections via Postgres tsvector (BM25). No embeddings. Returns `{section_id, snippet, rank}`.
4. **`get_kpi_table(role_name_ar)`** — Returns the structured KPI table for a role.
5. **`get_escalation_path(topic)`** — Returns the escalation rules for a topic.

### The agent loop (ReAct)
```
1. User Q → LLM (with ToC + tools + retry counter)
2. LLM: Thought → Action (tool call) → Observation (result)
3. If LLM has enough → Final Answer in Arabic with [المصدر: ...] citations
4. If not enough → call another tool (retry_count--)
5. After 5 retries (configurable) → refuse with the standard message
```

### Cost & latency budget
- ~3-5 LLM calls per question (varies with question complexity)
- ~$0.003-0.005/question
- 3-8 seconds end-to-end
- 10K questions/month ≈ $30-50

### Why this is "production grade" (per the discussion)
- LLM makes decisions, not a classifier (more flexible, handles edge cases).
- Self-aware retries (the model can pace itself, try alternatives).
- 5 tools cover the full question space (definitions, comparisons, KPIs, escalation, navigation).
- The ToC is the primary navigation tool — the LLM rarely needs to call more than 2 tools.
- No vector DB = simpler ops, no embedding API, no reindex on every change.
- Postgres tsvector is built-in (no extra service).
- Configurable retry count, prompt, and refusal message (in config.yaml).

### Phase plan
- **Phase 1:** Build the structure (sections table, kpi_tables, escalation_matrix, search_index) from the PDF.
- **Phase 2:** Build the 5 tools + the ReAct agent loop + the chat endpoint. No frontend yet.
- **Phase 3:** Cyrkil frontend + chat UI.
- **Phase 4-7:** Admin, auth, logs, hardening.

