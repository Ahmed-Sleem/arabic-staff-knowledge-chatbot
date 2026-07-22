"""
Provider client helpers for live API-key validation and streaming.

WHY: API-key checks, internal JSON control calls, and final answer streaming must
use the same production provider paths. This module prevents fake provider
success and supports native Gemini SSE plus OpenAI-compatible delta streaming.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - exercised only if dependency missing
    AsyncOpenAI = None


@dataclass(frozen=True)
class ProviderCheckResult:
    status: str
    message: str
    preview: str = ""


def default_model_for_provider(provider: str, model: str = "") -> str:
    cleaned_provider = provider.lower().strip()
    if model and model.strip():
        return model.strip()
    if cleaned_provider == "groq":
        return "llama-3.3-70b-versatile"
    if cleaned_provider == "gemini":
        return "gemini-1.5-flash"
    if cleaned_provider == "openai":
        return "gpt-4o-mini"
    return "deepseek-chat"


def base_url_for_provider(provider: str) -> str:
    cleaned_provider = provider.lower().strip()
    if cleaned_provider == "groq":
        return "https://api.groq.com/openai/v1"
    if cleaned_provider == "openai":
        return "https://api.openai.com/v1"
    return "https://api.deepseek.com"


def _gemini_from_messages(messages: List[Dict[str, str]]) -> tuple[Dict[str, Any] | None, List[Dict[str, Any]]]:
    system_instruction = None
    contents: List[Dict[str, Any]] = []
    for message in messages:
        role = message.get("role", "user")
        text = message.get("content", "")
        if role == "system" and system_instruction is None:
            system_instruction = {"parts": [{"text": text}]}
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": text}]})
    return system_instruction, contents


def extract_gemini_text_parts(chunk: Dict[str, Any]) -> List[str]:
    """Extract textual deltas from one Gemini GenerateContentResponse chunk."""
    texts: List[str] = []
    for candidate in chunk.get("candidates", []) or []:
        content = candidate.get("content", {}) or {}
        for part in content.get("parts", []) or []:
            text = part.get("text")
            if text:
                texts.append(text)
    return texts


async def complete_chat_text(provider: str, model: str, api_key: str, messages: List[Dict[str, str]], *, temperature: float = 0, max_tokens: int | None = None) -> str:
    """Return a completed provider response for non-user-visible internal control decisions."""
    provider_clean = provider.lower().strip()
    model_clean = default_model_for_provider(provider_clean, model)
    if provider_clean == "gemini":
        import httpx
        system_instruction, contents = _gemini_from_messages(messages)
        payload: Dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": temperature}}
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        async with httpx.AsyncClient(timeout=20.0) as client:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_clean}:generateContent?key={api_key.strip()}"
            res = await client.post(url, headers={"Content-Type": "application/json", "X-goog-api-key": api_key.strip()}, json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Gemini API Error {res.status_code}: {res.text[:240]}")
            data = res.json()
            return "".join(extract_gemini_text_parts(data))

    if AsyncOpenAI is None:
        raise RuntimeError("OpenAI-compatible client dependency is unavailable on the server.")
    client = AsyncOpenAI(api_key=api_key.strip(), base_url=base_url_for_provider(provider_clean), timeout=20.0)
    kwargs: Dict[str, Any] = {"model": model_clean, "messages": messages, "temperature": temperature}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    response = await client.chat.completions.create(**kwargs)
    return (response.choices[0].message.content or "") if response and response.choices else ""


async def stream_chat_deltas(provider: str, model: str, api_key: str, messages: List[Dict[str, str]], *, temperature: float = 0.1) -> AsyncGenerator[str, None]:
    """Yield actual provider-delivered text deltas, never locally fabricated words."""
    provider_clean = provider.lower().strip()
    model_clean = default_model_for_provider(provider_clean, model)
    if provider_clean == "gemini":
        import httpx
        system_instruction, contents = _gemini_from_messages(messages)
        payload: Dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": temperature}}
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_clean}:streamGenerateContent?alt=sse&key={api_key.strip()}"
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, headers={"Content-Type": "application/json", "X-goog-api-key": api_key.strip()}, json=payload) as res:
                if res.status_code != 200:
                    body = await res.aread()
                    raise RuntimeError(f"Gemini API Error {res.status_code}: {body[:240].decode('utf-8', 'replace')}")
                async for line in res.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_text = line.split("data:", 1)[1].strip()
                    if not data_text or data_text == "[DONE]":
                        continue
                    chunk = json.loads(data_text)
                    for text in extract_gemini_text_parts(chunk):
                        yield text
        return

    if AsyncOpenAI is None:
        raise RuntimeError("OpenAI-compatible client dependency is unavailable on the server.")
    client = AsyncOpenAI(api_key=api_key.strip(), base_url=base_url_for_provider(provider_clean), timeout=20.0)
    stream_resp = await client.chat.completions.create(
        model=model_clean,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    async for stream_chunk in stream_resp:
        delta = stream_chunk.choices[0].delta.content or ""
        if delta:
            yield delta


async def check_provider_connection(provider: str, model: str, api_key: str) -> ProviderCheckResult:
    """Verify a provider key using a tiny real prompt without exposing the key."""
    provider_clean = provider.lower().strip()
    model_clean = default_model_for_provider(provider_clean, model)
    key_clean = api_key.strip()
    if len(key_clean) < 5:
        return ProviderCheckResult(status="error", message="API key is required and must not be empty.")
    try:
        preview = await complete_chat_text(
            provider_clean,
            model_clean,
            key_clean,
            [{"role": "user", "content": "Return exactly: OK"}],
            temperature=0,
            max_tokens=4,
        )
        if preview:
            return ProviderCheckResult(status="valid", message=f"Verified {provider_clean.upper()} model '{model_clean}'.", preview=preview[:80])
        return ProviderCheckResult(status="error", message="No response returned from API provider.")
    except Exception as exc:
        return ProviderCheckResult(status="error", message=f"Connection Error: {str(exc)[:240]}")
