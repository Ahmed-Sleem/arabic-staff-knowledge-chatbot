#!/usr/bin/env python3
"""
Repository secret scanner for GPR verification.

WHY: GPR handles API keys and GitHub deploy credentials. This scanner gives the
project a repeatable local gate for common secret patterns in both the working
copy and reachable Git history while allowing deliberate dummy test fixtures.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", "node_modules", ".next", "__pycache__", ".pytest_cache", ".venv", "dist", "build"}
BINARY_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".db", ".sqlite", ".zip"}
DATA_JSON_PREFIXES = (
    "uploads/deepseek_json_",
    "src/backend/data/deepseek_json_",
    "src/backend/data/curated_knowledge_graph",
)
ALLOW_DUMMY_TEST_FIXTURES = {
    "src/backend/tests/test_vault.py",
    "src/backend/tests/test_react_agent.py",
}
SECRET_PATTERNS = {
    "github_pat_classic": re.compile(r"ghp_[A-Za-z0-9_]{30,}"),
    "github_pat_fine_grained": re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    "openai_like_sk": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "groq_like_gsk": re.compile(r"\bgsk_[A-Za-z0-9_-]{20,}\b"),
    "google_api_key": re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    "pem_private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "old_admin_password": re.compile("admin" + "1234"),
}


def is_excluded_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    if Path(normalized).suffix.lower() in BINARY_SUFFIXES:
        return True
    return normalized.endswith(".json") and normalized.startswith(DATA_JSON_PREFIXES)


def scan_text(path: str, text: str) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    normalized = path.replace("\\", "/").lstrip("./")
    for name, regex in SECRET_PATTERNS.items():
        if regex.search(text):
            if normalized in ALLOW_DUMMY_TEST_FIXTURES and name in {"openai_like_sk", "groq_like_gsk"}:
                continue
            findings.append((normalized, name))
    return findings


def scan_workspace() -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [item for item in dirnames if item not in EXCLUDED_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            rel = path.relative_to(ROOT).as_posix()
            if is_excluded_path(rel):
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if b"\0" in data[:4096]:
                continue
            text = data.decode("utf-8", "replace")
            findings.extend(scan_text(rel, text))
    return findings


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)


def scan_history() -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    try:
        commits = git("rev-list", "--all").splitlines()
    except Exception:
        return [("<git-history>", "unable_to_scan_history")]
    for commit in commits:
        for path in git("ls-tree", "-r", "--name-only", commit).splitlines():
            if is_excluded_path(path):
                continue
            try:
                data = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT, stderr=subprocess.DEVNULL, timeout=3)
            except Exception:
                continue
            if b"\0" in data[:4096]:
                continue
            text = data.decode("utf-8", "replace")
            for rel, name in scan_text(path, text):
                findings.append((f"{commit[:8]}:{rel}", name))
    return findings


def main() -> int:
    workspace_findings = scan_workspace()
    history_findings = scan_history()
    print(f"[secret-scan] workspace findings: {len(workspace_findings)}")
    print(f"[secret-scan] history findings: {len(history_findings)}")
    for rel, name in workspace_findings + history_findings:
        print(f"[secret-scan] FINDING {name} {rel}")
    return 1 if workspace_findings or history_findings else 0


if __name__ == "__main__":
    sys.exit(main())
