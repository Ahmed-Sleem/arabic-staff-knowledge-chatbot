#!/usr/bin/env bash
# Centralized local verification runner for GPR.
# Runs backend tests, frontend production build, shell syntax checks, whitespace checks, and secret scans.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_VENV="${GPR_VERIFY_VENV:-/tmp/gpr-backend-venv}"

echo "[verify] repo: ${ROOT}"
cd "$ROOT"

echo "[verify] git diff whitespace check"
git diff --check

echo "[verify] shell syntax checks"
bash -n docker-entrypoint.sh
bash -n start.sh

echo "[verify] backend dependencies + tests"
python3 -m venv "$BACKEND_VENV"
# shellcheck disable=SC1091
source "$BACKEND_VENV/bin/activate"
pip install -r "$ROOT/src/backend/requirements.txt" >/tmp/gpr-verify-pip.log 2>&1
cd "$ROOT/src/backend"
export GPR_VAULT_MASTER_KEY="${GPR_VAULT_MASTER_KEY:-$(python - <<'PY'
import base64
print(base64.urlsafe_b64encode(b'v'*32).decode().rstrip('='))
PY
)}"
export GPR_COOKIE_SECURE="${GPR_COOKIE_SECURE:-false}"
PYTHONPATH=. pytest -q tests/

echo "[verify] frontend install + production build"
cd "$ROOT/src/frontend"
npm install --legacy-peer-deps >/tmp/gpr-verify-npm.log 2>&1
npm run build

echo "[verify] secret scan"
cd "$ROOT"
python3 scripts/secret_scan.py

echo "[verify] cleanup ignored runtime artifacts"
rm -rf src/frontend/.next src/frontend/node_modules src/backend/.pytest_cache
rm -f src/backend/data/gpr_workspace.db
find src/backend -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

echo "[verify] all checks passed"
