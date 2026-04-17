#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-devops-platform}"
API_SERVICE="${API_SERVICE:-api}"
LOCAL_PORT="${LOCAL_PORT:-18080}"
JWT_SECRET="${JWT_SECRET:-change-me-dev-secret}"
JWT_ISSUER="${JWT_ISSUER:-devops-test-suite}"
JWT_AUDIENCE="${JWT_AUDIENCE:-devops-clients}"

cleanup() {
  if [[ -n "${PF_PID:-}" ]]; then
    kill "${PF_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

kubectl -n "${NAMESPACE}" port-forward "svc/${API_SERVICE}" "${LOCAL_PORT}:8000" >/tmp/api-port-forward.log 2>&1 &
PF_PID=$!

ATTEMPTS=0
until curl -fsS "http://127.0.0.1:${LOCAL_PORT}/healthz" >/dev/null 2>&1; do
  if ! kill -0 "${PF_PID}" >/dev/null 2>&1; then
    echo "kubectl port-forward exited unexpectedly:" >&2
    cat /tmp/api-port-forward.log >&2 || true
    exit 1
  fi
  ATTEMPTS=$((ATTEMPTS + 1))
  if [[ "${ATTEMPTS}" -ge 20 ]]; then
    echo "Timed out waiting for API port-forward to become ready" >&2
    cat /tmp/api-port-forward.log >&2 || true
    exit 1
  fi
  sleep 1
done

TOKEN="$(python3 infra/scripts/create_jwt.py --secret "${JWT_SECRET}" --issuer "${JWT_ISSUER}" --audience "${JWT_AUDIENCE}")"

curl -fsS "http://127.0.0.1:${LOCAL_PORT}/healthz" >/dev/null
curl -fsS "http://127.0.0.1:${LOCAL_PORT}/readyz" >/dev/null

curl -fsS -X POST "http://127.0.0.1:${LOCAL_PORT}/task" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"smoke-task-1","payload":{"source":"smoke","value":1}}' >/dev/null

ATTEMPTS=0
while [[ "${ATTEMPTS}" -lt 30 ]]; do
  STATS="$(curl -fsS "http://127.0.0.1:${LOCAL_PORT}/stats")"
  if python3 - "${STATS}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required = {"valkey_keys_count", "queue_backlog", "worker_processed_count"}
missing = required - payload.keys()
if missing:
    raise SystemExit(f"missing fields: {sorted(missing)}")
if payload["worker_processed_count"] < 1:
    raise SystemExit(2)
PY
  then
    echo "Smoke test passed"
    exit 0
  else
    rc=$?
    if [[ "${rc}" -ne 2 ]]; then
      exit "${rc}"
    fi
  fi
  ATTEMPTS=$((ATTEMPTS + 1))
  sleep 2
done

echo "Timed out waiting for worker_processed_count to increase" >&2
exit 1
