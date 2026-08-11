#!/usr/bin/env bash
# Fail if plugin / dashboard / Python / UI version strings diverge.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"

plugin_version="$(
  python3 - <<'PY' "$root/plugin.yaml"
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r"(?m)^version:\s*[\"']?([^\"'\s]+)[\"']?\s*$", text)
if not match:
    raise SystemExit("version not found in plugin.yaml")
print(match.group(1))
PY
)"

dashboard_version="$(
  python3 - <<'PY' "$root/dashboard/manifest.json"
import json, pathlib, sys
print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])
PY
)"

pyproject_version="$(
  python3 - <<'PY' "$root/pyproject.toml"
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', text)
if not match:
    raise SystemExit("version not found in pyproject.toml")
print(match.group(1))
PY
)"

ui_version="$(
  python3 - <<'PY' "$root/ui/package.json"
import json, pathlib, sys
print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])
PY
)"

echo "plugin.yaml:            $plugin_version"
echo "dashboard/manifest.json: $dashboard_version"
echo "pyproject.toml:         $pyproject_version"
echo "ui/package.json:        $ui_version"

if [[ "$plugin_version" != "$dashboard_version" || "$plugin_version" != "$pyproject_version" || "$plugin_version" != "$ui_version" ]]; then
  echo "error: version mismatch — keep plugin.yaml, dashboard/manifest.json, pyproject.toml, and ui/package.json in sync" >&2
  exit 1
fi

echo "ok: versions aligned at $plugin_version"
