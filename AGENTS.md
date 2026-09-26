# LivingColor Plugin — Agent Guide

Hermes Agent plugin (not a Cursor plugin): autonomous delivery with human-approved
gates, plus a Mission Control dashboard tab.

## Package layout

| Path | Role |
| --- | --- |
| `plugin.yaml` | Hermes plugin manifest (version source of truth) |
| `dashboard/` | Dashboard tab + FastAPI plugin API (`manifest.json`, `plugin_api.py`, `dist/`) |
| `ui/` | Vite/React source for Mission Control; build output → `dashboard/dist/` |
| `delivery_runtime/` | Hermes-free delivery domain (Work Orders, readiness, gates, SQLite API) |
| `lc_server/` | Host bridges (Jira/GitLab/GitHub, Hermes agents, provisioning, Firebase) |
| `agent_surfaces.py` | Slash `/delivery` + delivery model tools |
| `livingcolor_pm_tools.py` | PM / Mission Control model tools |
| `skills/productivity/livingcolor-pm/` | Bundled PM skill |
| `livingcolor.skills.lock.json` | Pinned external skills (`Tamsi/livingcolor-skills`) |
| `cloud_api/` | Team-mode cloud API (Firebase) |
| `tests/` | Python tests; UI tests live under `ui/` |

## Data home

Default product data: `~/.hermes/livingcolor/` (via `lc_constants.get_livingcolor_home()`,
honors `HERMES_HOME` / `LIVINGCOLOR_HOME`).

Hermes host config (MCP, model, command allowlist): `~/.hermes/config.yaml`.

Legacy `~/.livingcolor/` paths may still appear in comments or migration helpers;
do not introduce them in new user-facing copy.

## Invariants

- `delivery_runtime/` must stay Hermes-free (no `hermes_cli` / Hermes tool imports).
- Agent/CLI surfaces should reuse `delivery_runtime.api.routes` so contracts match HTTP.
- Keep versions aligned: `plugin.yaml`, `dashboard/manifest.json`, `pyproject.toml`,
  `ui/package.json` — verify with `./scripts/check-versions.sh`.
- Human gates pause orchestration; do not auto-approve delivery gates.

## Dev commands

```bash
./scripts/check-versions.sh
pip install -e ".[test]"
./scripts/run-ci-tests.sh -q
cd ui && npm ci && npm test && npm run build
```

## Related guides

- [`delivery_runtime/AGENTS.md`](delivery_runtime/AGENTS.md)
- [`lc_server/AGENTS.md`](lc_server/AGENTS.md)
- [`README.md`](README.md)
