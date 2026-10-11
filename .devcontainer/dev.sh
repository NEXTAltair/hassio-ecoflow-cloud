#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python=/home/vscode/.local/ha-venv/bin/python

case "${1:-check}" in
  versions)
    "$python" - <<'PY'
import sys
from importlib.metadata import version

print(f"Python {sys.version.split()[0]}")
for package in ("homeassistant", "protobuf", "ruff", "mypy"):
    print(f"{package} {version(package)}")
PY
    ;;
  lint)
    # Match upstream's mise lint policy without syncing the protected local .venv.
    deferred_rules=$("$python" - <<'PY'
import tomllib

with open("mise.toml", "rb") as config:
    print(tomllib.load(config).get("env", {}).get("RUFF_DEFERRED", ""))
PY
    )
    ruff_options=(--output-format concise)
    if [[ -n "$deferred_rules" ]]; then
      ruff_options+=(--ignore "$deferred_rules")
    fi
    "$python" -m ruff check "${ruff_options[@]}" custom_components
    ;;
  typecheck)
    "$python" -m mypy custom_components
    ;;
  smoke)
    "$python" - <<'PY'
import ast
import importlib.util
import sys
from importlib.metadata import version
from pathlib import Path

from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct
import yaml

assert sys.version_info[:3] == (3, 14, 6), "Unexpected development Python"
assert version("homeassistant") == "2026.10.0", "Unexpected development HA"
assert version("protobuf") == "7.36.0", "Unexpected development protobuf"
config = yaml.safe_load(Path(".devcontainer/ha-config/configuration.yaml").read_text())
assert not {"default_config", "discovery", "mqtt", "ecoflow_cloud"}.intersection(config)
assert config["homeassistant"]["name"] == "EcoFlow Development"
message = Struct()
message.update({"offline": True})
assert MessageToDict(message, preserving_proto_field_name=True) == {"offline": True}
sources = list(Path("custom_components").rglob("*.py"))
assert sources, "No integration sources found"
for source in sources:
    ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
generated = list(Path("custom_components/ecoflow_cloud/devices/internal/proto").glob("*_pb2.py"))
assert generated, "No generated protobuf schemas found"
for source in generated:
    # Load generated schemas directly without importing the integration's __init__.
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.startswith("google.protobuf") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").startswith("google.protobuf")
    spec = importlib.util.spec_from_file_location(source.stem, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.DESCRIPTOR.name
print(f"Offline smoke OK: versions, isolated configuration, protobuf, {len(sources)} Python files, {len(generated)} generated schemas")
PY
    ;;
  status|wait)
    "$python" - "${1}" <<'PY'
import sys
import time
import urllib.error
import urllib.request

deadline = time.monotonic() + (180 if sys.argv[1] == "wait" else 3)
while True:
    try:
        with urllib.request.urlopen("http://homeassistant:8123/", timeout=3) as response:
            assert response.status == 200
        print("Development HA HTTP ready")
        break
    except (OSError, urllib.error.URLError):
        if time.monotonic() >= deadline:
            raise SystemExit("Development HA is not ready; check its Compose logs")
        time.sleep(2)
PY
    ;;
  logs)
    sudo tail -F /ha-state/home-assistant.log
    ;;
  docs)
    cd docs
    PYTHONPATH=.. "$python" gen.py
    ;;
  check)
    result=0
    for check in smoke lint typecheck; do
      if bash .devcontainer/dev.sh "$check"; then
        echo "$check: passed"
      else
        echo "$check: failed" >&2
        result=1
      fi
    done
    exit "$result"
    ;;
  *)
    echo "Usage: bash .devcontainer/dev.sh {versions|smoke|lint|typecheck|check|status|wait|logs|docs}" >&2
    exit 2
    ;;
esac
