# Topic 2 — DeepSeek API

**Status:** Phase 2 — Deep Dive (in progress)
**Last update:** 2026-07-10

---

## Open questions

1. Which DeepSeek model is best for our use case?
   - `deepseek-chat` (V3)
   - `deepseek-reasoner` (R1)
   - `deepseek-coder`
2. **Arabic quality** — how well does DeepSeek perform in Arabic, especially formal Modern Standard Arabic?
3. **Pricing** — current rates for input/output tokens, and free credits if any.
4. **Rate limits** — RPM / TPM at our tier.
5. **Streaming** support?
6. **Function calling / structured output** support?
7. **Context window** — do we have enough for our prompt + retrieved chunks + history?
8. **System prompt adherence** — does it reliably follow the "answer in Arabic only / refuse if not in PDF / cite source" instructions?
9. **Data privacy** — what is DeepSeek's data retention / training-on-input policy? Implications for sending the PDF chunks and user questions to their API.
10. **Endpoint** — `https://api.deepseek.com` or self-hosted DeepSeek? For KSA / Arabic, are there regional endpoints?

---

## Findings (append below)


## Findings — DeepSeek API (V4 line, May 2026)

### Models available
- **`deepseek-v4-flash`** — lower cost, faster, good for high-volume and RAG workloads. **This is our default pick.**
- **`deepseek-v4-pro`** — stronger reasoning/coding/agentic, more expensive, sometimes discounted 75% through 2026-05-31.
- Legacy aliases `deepseek-chat` and `deepseek-reasoner` → route to v4-flash (non-thinking and thinking modes). Scheduled for deprecation 2026-07-24.

### Pricing (as of May 2026)
| Model | Cache-hit input | Cache-miss input | Output |
|---|---|---|---|
| deepseek-v4-flash | $0.0028 / 1M | $0.14 / 1M | $0.28 / 1M |
| deepseek-v4-pro (regular) | higher | higher | higher |
| deepseek-v4-pro (75% promo) | $0.003625 / 1M | $0.435 / 1M | $0.87 / 1M |

For comparison:
- OpenAI gpt-4o-mini: ~$0.15 / 1M input, ~$0.60 / 1M output.
- Gemini 1.5 Flash: ~$0.075 / 1M input, ~$0.30 / 1M output.

**Cost implication for our use case:** Our prompts will be system + question + retrieved chunks + history. With ~5K input + 500 output tokens per question:
- ~$0.0007 input + ~$0.00014 output = **~$0.0008 per question** on v4-flash.
- 10K questions/month ≈ **$8/month**. Very affordable.
- Cache hits make subsequent turns in the same conversation much cheaper (deepseek caches prompt prefixes — a big win for multi-turn).

### Capability checklist (from official docs)
- ✅ OpenAI-compatible API (`base_url=https://api.deepseek.com`, `model="deepseek-v4-flash"`).
- ✅ Streaming (SSE).
- ✅ JSON output (`response_format={"type": "json_object"}`).
- ✅ Tool / function calling.
- ✅ Context caching (cache-hit pricing is 98% off cache-miss).
- ✅ 64K context window (v4-flash). 8K max output (default 4K).
- ✅ "Thinking mode" available on v4-flash and v4-pro (toggle via parameter).

### Arabic quality
- **DeepSeek-V3 baseline (May 2025, arxiv 2412.19437):** MMMLU-non-English 79.4, competitive with the field.
- **Adapted Arabic-DeepSeek-R1 (April 2026, arxiv 2604.06421):** SOTA on 5/7 Arabic benchmarks, OALL avg 80.18% — beats GPT-5.1 (+2.31), Llama-3.3-70B, Jais-family. This is a fine-tuned variant, not the base API, but it tells us DeepSeek's underlying architecture is strong on Arabic.
- **BALSAM Arabic benchmark (Jul 2025):** DeepSeek V3 scored 1.99 avg, behind GPT-4o (2.05) and Gemini 2.0 Flash (2.02) but ahead of Claude Sonnet 3.5 (1.99), Grok-2 (1.96), and Qwen-2.5 32B (1.80).
- **Verdict:** DeepSeek V3/V4 is **competitive on Arabic** but not the very best out-of-the-box. For our use case (formal MSA, structured Q&A with strict source citation), this should be fine because we'll constrain output via the system prompt and our chunks will be Arabic. The "thinking mode" can be left off to save cost.

### Data privacy
- API inputs are not used for training (per DeepSeek's standard API policy). Same as OpenAI / Anthropic.
- Data goes to DeepSeek's infrastructure (China-hosted). **For KSA customers with strict data-residency requirements, this is a concern** — must call out in compliance topic.
- Alternative: self-host DeepSeek-V3 (open weights) for full data control. Heavy on GPU, but possible.

### Endpoints
- OpenAI-compatible: `https://api.deepseek.com` (or `https://api.deepseek.com/v1`).
- Anthropic-compatible: `https://api.deepseek.com/anthropic`.
- Both use the same model and same pricing.

### Rate limits
- 429 errors possible; need retry-with-backoff.
- For high concurrency, plan an async queue on the backend.

### Recommendation (locked candidate for plan)
- **LLM:** `deepseek-v4-flash` (non-thinking) for chat.
- **Optionally** upgrade to `deepseek-v4-flash` thinking mode for the test-mode admin questions, where quality matters more.
- **Streaming** enabled for the chat UX.
- **JSON output** enabled for the structured answer object (answer text + sources + confidence).
- **Context caching** to be enabled (DeepSeek caches the system prompt + retrieved chunks prefix automatically — huge win for our pattern).

