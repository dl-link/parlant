#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PARLANT_HOME=${PARLANT_HOME:-"${PROJECT_ROOT}/.parlant"}
export PARLANT_SERVER_PORT=${PARLANT_SERVER_PORT:-8800}
export PARLANT_PROVIDER_PROFILE=${PARLANT_PROVIDER_PROFILE:-openai}

cd "${PROJECT_ROOT}"
python app/main.py
