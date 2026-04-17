#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

bash "$ROOT/scripts/commit_and_push.sh"
bash "$ROOT/scripts/commit_hermes_agent_code.sh"
