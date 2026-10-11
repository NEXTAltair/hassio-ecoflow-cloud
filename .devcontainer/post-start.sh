#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Compose owns the HA process. Reopening never starts another instance.
bash .devcontainer/dev.sh wait
