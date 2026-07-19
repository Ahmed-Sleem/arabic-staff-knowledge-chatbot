# Topic 11 — Compliance & Data Handling

**Status:** Phase 2 — Deep Dive (in progress)
**Last update:** 2026-07-10

---

## Open questions

1. **What is sent to DeepSeek?**
   - System prompt (static, fine).
   - User question.
   - Retrieved chunks (the PDF content).
   - Conversation history.
   - User's name? No, but maybe email — depends on what we send.
2. **DeepSeek's data policy** — what does their API do with inputs? Are they stored? Used for training? Logged?
3. **PDPL (Personal Data Protection Law — Saudi Arabia)**: KSA-issued PDPL (effective Sept 2024 with grace period). Applies to personal data of individuals in KSA. Implications for logging emails, questions, etc.
4. **PII in conversation history**:
   - Should we store conversations at all? PRD says "Chat history" is in scope.
   - How long do we retain logs?
   - Can the user delete their own conversation?
5. **Data minimization**:
   - Don't log full user agent, IP, etc., unless needed.
   - Hash user IDs where possible.
6. **Data residency** — for KSA customers, ideally data stays in KSA / GCC. Free-tier cloud options mostly aren't in-region. Need to call this out and let the customer decide.
7. **Right to be forgotten** — does the user have a way to delete all their data?
8. **Backup & retention** — what's in backups, how long kept, encrypted at rest?

---

## Findings (append below)


## Findings — Saudi PDPL (Personal Data Protection Law)

### Source 1 — sgc.consulting "SDAIA and Saudi Personal Data Protection Law (PDPL)" (May 2026)
URL: https://www.sgc.consulting/sdaia-saudi-personal-data-protection-law-pdpl-compliance-guide/
- PDPL enacted by Royal Decree No. M/19 in September 2021, amended March 2023, in full force from 14 September 2023.
- **Grace period expired 14 September 2024.** Compliance is now legally required.
- Regulator: **SDAIA** (Saudi Data and AI Authority).
- 48 enforcement decisions in 2025-2026 alone.

**Seven core obligations:**
1. **Lawful basis for processing** — consent primary; also contractual necessity, legal obligation, vital interests, legitimate interest. Must be documented.
2. **Data subject rights** — access, correction, deletion, objection, portability. Must respond within regulatory timeframes.
3. **Data breach notification, 72 hours** — must notify SDAIA within 72 hours of breach awareness.
4. **Data minimization** — collect only what's needed for the purpose.
5. **Sensitive data** — stricter safeguards. Includes ethnic/tribal origin, religious belief, political belief, civil association membership.
6. **Cross-border transfers** — strict rules. SDAIA SCCs, BCRs, or Certificate of Accreditation required.
7. **DPO appointment** — required if processing personal data on a large scale, regular monitoring, or sensitive data.

### Source 2 — regulations.ai "Regulation on Personal Data Transfer Outside the Kingdom (PDPL transfer regulation)" (May 2026)
URL: https://regulations.ai/regulations/RAI-SA-NA-PDTOKXX-2024
- "Limit personal data transfers to only what is strictly necessary for a defined, lawful purpose, ensuring data minimization."
- "A thorough risk assessment is mandatory, evaluating the legal, technical, and practical risks to personal data rights in the destination country and with the recipient."
- "Organizations must implement specific safeguards, choosing from SDAIA Standard Contractual Clauses, approved Binding Common Rules for internal group transfers, or a Certificate of Accreditation."

### Source 3 — trade.gov "Saudi Arabia ICT Cross-Border Data Transfer Rules" (Aug 2025)
URL: https://www.trade.gov/market-intelligence/saudi-arabia-ict-cross-border-data-transfer-rules-now-under-enforcement
- "The regulations require companies to store sensitive and personally identifiable data within Saudi Arabia, unless specific exemptions are granted."
- Saudi Arabia is "actively enforcing" — SDAIA + NCA rolling out detailed enforcement mechanisms.

### Source 4 — securiti.ai "Saudi Arabia's PDPL"
URL: https://securiti.ai/solutions/saudi-arabia-pdpl/
- SDAIA is the main regulatory authority for the first two years. Transfer of supervision to NDMO may be considered in 2024.
- Organizations must appoint a DPO if core activities involve large-scale personal data processing, regular/systematic monitoring, or sensitive data.

### Implication for our project
- **What counts as "personal data" in our system?**
  - User email + password hash (login).
  - User's chat history (questions, answers, timestamps).
  - IP address in HTTP logs.
  - User agent in HTTP logs.
  - Session cookies.
- **What about the PDF content?** The PDF is the company policy, not personal data of any specific individual. Job titles, KPIs, reporting lines are all public-internal. So the PDF itself is NOT personal data.
- **Where does this leave us?**
  - **Lawful basis:** staff have an employment relationship with the company; using the chatbot is part of their job. Contractual necessity applies. We need to inform employees about what we collect (privacy notice).
  - **Data minimization:** log only what's needed for the admin logs (per PRD §13). Drop IPs after 30 days. Don't log user agents.
  - **Data subject rights:** build a "Delete my data" endpoint (per-user) and a "Download my data" endpoint.
  - **Breach notification:** document the 72-hour breach procedure in SUPPORTING_NOTES.md.
  - **Cross-border transfer:** **This is the big one.** Sending data to DeepSeek API = cross-border transfer. We need to:
    - Inform users that their question goes to DeepSeek.
    - Document DeepSeek as a sub-processor.
    - Consider the SDAIA SCC requirement.
    - **Or self-host DeepSeek for full data residency.** This is expensive but the cleanest path.
  - **DPO:** For a small staff tool, the company itself acts as DPO. We document the contact in the privacy notice.

### Recommendation (locked candidate for plan)
- **Privacy notice (in Arabic):** shown on first login. Covers what we collect, why, who has access (the company), retention period, user rights, breach notification process, contact info.
- **User rights endpoints:**
  - `GET /me/data` — download JSON of user's data.
  - `DELETE /me/data` — delete all of user's data (sessions, conversations, messages, logs).
- **Admin controls:**
  - Soft-delete with 30-day grace, then hard delete.
  - Log retention: 1 year max for admin logs; user can request earlier deletion.
- **Cross-border transfer:**
  - Default: DeepSeek API with a clear privacy notice. **Documented as a sub-processor.**
  - Future option: self-hosted DeepSeek-V3 if customer requires full in-KSA residency.
- **DPO contact:** the admin's email, configured via env var.
- **SDAIA breach procedure:** in SUPPORTING_NOTES.md. Out of scope to actually notify SDAIA — that's the customer's job; we provide the tooling.

