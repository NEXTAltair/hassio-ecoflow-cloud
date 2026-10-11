#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Dependencies are installed in the image, so creation also works offline.
bash .devcontainer/dev.sh versions
bash .devcontainer/dev.sh smoke
