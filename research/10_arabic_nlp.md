# Topic 10 — Arabic NLP Specifics

**Status:** Phase 2 — Deep Dive (in progress)
**Last update:** 2026-07-10

---

## Open questions

1. **Normalization** for both user queries and PDF text:
   - Alef forms: إ أ آ → ا
   - Yeh forms: ى ي → ي
   - Ta marbuta: ة → ه (only for search equality, not display)
   - Remove diacritics (tashkeel): ً ٌ ٍ َ ُ ِ ّ ْ
   - Remove tatweel: ـ
   - Normalize whitespace.
   - Normalize presentation forms (ﭐ ﭑ etc.) — important because some PDFs store Arabic in presentation forms B (FB16).
2. **Synonym / term expansion** — per PRD §7.9:
   ```
   الموارد البشرية  ↔  إدارة الموارد البشرية
   السلامة  ↔  HSE
   الجودة  ↔  QC/QA / QHSE
   المشاريع  ↔  PMO / إدارة المشاريع
   التحويل/التصعيد  ↔  قاعدة التصعيد الإداري
   مؤشرات الأداء  ↔  KPIs
   المهام  ↔  المهام والمسؤوليات
   يتبع من  ↔  التبعية التنظيمية
   يرفع لمن  ↔  يقدم تقاريره إلى
   ```
   - **Static dictionary** (lookup) at query time + at chunk time.
   - **Embedding-only** (the embedding model already maps synonyms close).
   - **Hybrid**: rewrite query with a known term, then embed.
3. **Mixed Arabic/English tokens** (KPI, PMO, HSE inside Arabic sentence):
   - Don't strip English tokens.
   - Transliteration handling (e.g. user writes "كي بي آي" for "KPI") — optional.
4. **Code-switching** in user input (user types in English — bot must still reply Arabic, per PRD §7.1). Translation of the question internally is one option; the LLM is multilingual enough to handle it directly.
5. **Numeric handling** — Arabic-Indic digits ٠١٢٣٤٥٦٧٨٩ vs 0123456789. Decide and be consistent.
6. **Word boundaries in RTL** — affects regex / chunking; many tools (Python regex) don't understand Arabic word boundaries natively. `pyarabic` and `arabic-reshaper` can help.

---

## Findings (append below)


## Findings — Arabic text normalization

### Source 1 — blog.brightcoding.dev "Awesome-Arabic-AI" (Mar 2026)
URL: https://www.blog.brightcoding.dev/2026/03/16/awesome-arabic-ai-7-powerful-resources-revolutionizing-arabic-ai
- **PyArabic** (`pyarabic.araby`):
  - `strip_tashkeel(text)` — remove diacritics.
  - `normalize_alef(text)` — unify إ أ آ → ا.
  - `strip_tatweel(text)` — remove elongation character ـ.
  - `is_arabicrange(text)` — check if text contains Arabic.
- **Camel Tools** (camel-tools):
  - `MLEDisambiguator` — pick the right lemma for a token.
  - `DefaultTagger` — POS tags.
  - "Using disambiguated lemmas improves retrieval accuracy in RAG systems by 25-40% compared to surface-form matching." (claim, but plausible.)
- "Most Arabic LLMs are trained on non-diacritized text. This preprocessing ensures your input matches training data distribution, improving tokenization accuracy by up to 30%."

### Source 2 — tashaphyne normalize.py (MTG ArabicTransliterator)
URL: https://github.com/MTG/ArabicTransliterator/blob/master/tashaphyne/normalize.py
- `normalize_searchtext(text)`:
  - strip tashkeel
  - strip tatweel
  - normalize Hamza
  - normalize Lam Alef (لا → لا properly)
  - normalize Teh Marbuta (ة → ه)
  - normalize Alef Maksura (ى → ي)
- `normalize_spellerrors(text)`:
  - TEH_MARBUTA → HEH
  - ALEF_MAKSURA → YEH
- This is the reference implementation many Arabic search engines use.

### Source 3 — Quran Search Engine normalize.ts
URL: https://adelpro-quran-search-engine.mintlify.app/guides/normalization
```ts
function normalizeArabic(text) {
  if (!text) return '';
  let n = removeTashkeel(text).normalize('NFC');
  n = n.replace(/[\u0670\u0640]/g, '');          // dagger alif + tatweel
  n = n.replace(/[إأآٱ]/g, 'ا');                  // alef variants → ا
  n = n.replace(/[ؤئء]/g, 'ء');                   // hamza variants → ء
  n = n.replace(/ى/g, 'ي');                        // alif maqsura → ي
  n = n.replace(/[\r\n]+/g, ' ');
  n = n.replace(/[^\u0621-\u064A\s-]+/g, '');     // strip non-Arabic
  n = n.replace(/\s{2,}/g, ' ');
  return n.trim();
}
```
- **Important note:** they strip all non-Arabic chars. For our case, we want to KEEP English tokens (KPI, PMO, HSE) that appear in mixed queries. We should NOT do that last step.

### Source 4 — preprocessing_arabic_text repo
- Functions: remove_usernames, remove_tashkeel, remove_tatweel, normalize_hamza, normalize_alef, normalize_yeh, normalize_heh.
- Note: their `normalize_heh` goes ه → ة, opposite of the standard Arabic search convention. We want the standard: ة → ه.

### Recommended normalization pipeline for our project
1. `text = text.normalize('NFC')` — Unicode normalization (combine characters).
2. Strip tashkeel: `[\u064B-\u0652\u0670\u0653\u0654\u0655]` → ''.
3. Strip tatweel: `[\u0640]` → ''.
4. Normalize alef: `[إأآٱ]` → `ا`.
5. Normalize alef maqsura: `ى` → `ي`.
6. Normalize teh marbuta: `ة` → `ه` (this is the standard for search equality; display layer restores it).
7. Trim, collapse whitespace.
8. **Keep English/digit tokens** (do NOT strip them) so "KPI", "PMO", "HSE" pass through.

### Where to apply normalization
- **At PDF ingestion time** (when chunking) — store the *original* text in the chunk, but also store a `normalized_text` field for keyword/BM25 search.
- **At query time** — normalize the user's question before embedding AND before BM25 search.
- **Display layer** — never display normalized text; always show the original PDF text to the user.

### Library choice
- **`pyarabic`** — simplest, no model download. Implements steps 1-7 cleanly.
- **`camel-tools`** — heavier, downloads models, but gives lemmatization (25-40% retrieval improvement claim). For a single-PDF small KB, the lemmatization benefit is small; the normalization alone is the big win.
- **Verdict:** use `pyarabic` for normalization, skip lemmatization for MVP. Add lemmatization as a v2 improvement.

