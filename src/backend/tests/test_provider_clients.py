"""
Provider client streaming adapter tests.

WHY: Real streaming depends on provider adapters forwarding upstream deltas instead
of local word splitting. These tests cover deterministic parser/contract pieces
without calling external providers.
"""

from services.provider_clients import extract_gemini_text_parts


def test_extract_gemini_text_parts_skips_signature_only_chunks():
    chunk = {
        "candidates": [
            {"content": {"parts": [{"text": "Hello "}, {"text": "world"}]}, "finishReason": ""},
            {"content": {"parts": [{"thoughtSignature": "abc"}]}, "finishReason": "STOP"},
        ]
    }
    assert extract_gemini_text_parts(chunk) == ["Hello ", "world"]
