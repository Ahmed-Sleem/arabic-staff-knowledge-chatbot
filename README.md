# Arabic Staff Knowledge Chatbot (المساعد الداخلي الذكي للموظفين) — Cyrkil Ecosystem

## Story-Driven Genesis

In high-growth corporate environments like **Kayan Al-Mamlaka Company (شركة كيان المملكة كاك)** in Saudi Arabia, organizational clarity is often buried under pages of dense operational manuals. I noticed that staff and new hires constantly struggled to answer basic daily questions: *Who is responsible for pricing? Who does the PMO Manager report to? What exact formula measures our QHSE incident follow-up KPI? And what is the administrative escalation path when an urgent contract issue arises?* 

Every time someone asked these questions, they either spent 30 minutes scrolling through the 64-page **Organizational Structure, Job Responsibilities, and KPI Guide (v1.0)** or interrupted department leads. Traditional AI chatbots weren't an option—they hallucinated company policies, mixed up Arabic corporate synonyms (`PMO` vs. `إدارة المشاريع`), and choked when chunking complex multi-column KPI tables across arbitrary page breaks.

So I got the idea to build **Cyrkil Arabic Staff Knowledge Chatbot**: a lightning-fast, Arabic-exclusive internal assistant that rejects vector databases in favor of **structural relational RAG**. By indexing sections, job descriptions, KPI formulas (`طريقة الحساب`), and administrative escalation matrices (`مصفوفة التصعيد الإداري`) directly into structured Postgres relational tables (`tsvector`), our assistant grounds every single answer strictly in the official guide. Better yet, it presents exact inline citations (`[المصدر: القسم 4.2 - مسؤول التسعير]`), opens an interactive right-hand excerpt drawer highlighting the exact PDF passage, dynamically accepts custom LLM API keys right from the GUI, and strictly refuses to guess if information isn't in the manual (`عذراً، هذه المعلومة غير متوفرة في دليل الهيكل التنظيمي المعتمد حالياً.`).

---

## Technical Stack & Architecture

| Layer | Choice | Justification |
|---|---|---|
| **Frontend** | **Next.js 15 App Router + Cyrkil Design System** | Full RTL (`dir="rtl"`), IBM Plex Sans Arabic font, 3-panel split-screen resizable workspace, dynamic LLM API key configuration header, and interactive citation drawers. |
| **Backend** | **FastAPI (Python 3.11+) + Async SQLAlchemy 2.0** | High-concurrency token streaming via Server-Sent Events (`/api/v1/chat/stream`), ARQ Redis background workers, and relational domain ingestion. |
| **RAG Engine** | **Structural Relational RAG (No Vector DB)** | Custom `pypdf`/`pdfplumber` pipeline extracting hierarchical sections, multi-column KPI tables (`calculation` & `target`), and escalation decision trees into Postgres `tsvector` full-text search. |
| **LLM Agent** | **DeepSeek v4-flash (`deepseek-chat`) via OpenAI Python SDK** | Non-thinking ReAct agent equipped with 5 specialized relational retrieval tools (`search_sections`, `get_job_description`, `get_kpis`, `get_escalation_path`, `get_reporting_line`). |
| **API Management** | **Dynamic Header Ingestion (`X-LLM-API-Key`)** | Staff or admins can input their own DeepSeek/OpenAI API key in the Cyrkil GUI settings modal; requests dynamically route using the active client or server-fallback key. |

---

## Directory Structure

```
arabic-staff-knowledge-chatbot/
├── README.md                                # This story-driven architectural specification
├── _working_docs/                           # Master agent governance & append-only verification logs
│   ├── AGENT_RULES.md                       # Standing mandatory operating rules (30 rules)
│   ├── AUDIT_AND_TODO.md                    # Active and closed gap tracking
│   ├── IMPLEMENTATION_LOG.md                # Self-check verification evidence (a/b/c format)
│   ├── CHANGELOG.md                         # Session history and git promotion logs
│   └── NEXT_SESSIONS_ROADMAP.md             # Immediate and future execution step guide
├── _development_docs_REMOVE_BEFORE_DEPLOYMENT/  # System blueprints and project mapping
├── research/                                # 11 topic deep-dives (RAG, DeepSeek, Arabic NLP, Auth)
├── uploads/                                 # Source HR guide (`hr_source.pdf`), PRD, & GUI sketch
└── src/                                     # Production Application Source Code
    ├── backend/                             # FastAPI application & ingestion engine (`GAP-ASKC-01` $\rightarrow$ `03`)
    │   ├── models.py                        # Relational schema (`sections`, `kpi_tables`, `escalation_rules`)
    │   ├── database.py                      # Async database engine and session management
    │   ├── ingestion/                       # Structural PDF parsing (`parse_hr_pdf.py`)
    │   ├── agent/                           # ReAct agent & 5 retrieval tools
    │   └── main.py                          # Streaming API server (`/api/v1/chat/stream`)
    └── frontend/                            # Next.js 15 Cyrkil-styled 3-panel GUI (`GAP-ASKC-04`)
```

---

## Quickstart & Local Execution

### 1. Ingest the Arabic HR Guide into Relational Structure
Run the structural ingestion pipeline (`GAP-ASKC-01`) directly against the official company manual:
```bash
cd src/backend
python3 -m ingestion.parse_hr_pdf --pdf ../../uploads/hr_extracted/hr_source.pdf --out data/hr_indexed.json
```

### 2. Run the Automated Verification Suite
We maintain zero-mock production standards. Run the pytest suite to assert exact page counts, table extraction precision, and Arabic full-text grounding:
```bash
cd src/backend
pytest -v
```

### 3. Launch Backend API Server
```bash
cd src/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## License & Governance
Developed under strict engineering governance for **Cyrkil Ecosystem** and **Kayan Al-Mamlaka Company**. Every commit must pass the **Parse-Think-Verify loop (`Rule 23`)** and maintain zero technical debt (`Rule 21`).
