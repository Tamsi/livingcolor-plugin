# Delivery Runtime (`delivery_runtime/`)

> Parent: [`../AGENTS.md`](../AGENTS.md) · Server host: [`../lc_server/AGENTS.md`](../lc_server/AGENTS.md)

Instructions for AI assistants working on the **LivingColor Autonomous Delivery Platform** domain layer.

## Scope

**Owns:**

- Work Orders (primary product entity)
- Delivery Readiness Queue (A+ intake)
- Execution graphs, gates, events
- SQLite persistence under `~/.hermes/livingcolor/` (`runtime.db`, `project_mapping.yaml`)
- REST API at `/api/delivery/*` (routes only — server wires dependencies)
- Orchestration loop and agent bridge **protocol**

**Does not own:**

- Mission Control UI → `ui/src/app/delivery/`
- Hermes agent loop or MCP transport → `lc_server/`
- Dashboard host mounting → `dashboard/plugin_api.py`

## Load-bearing entry points

| Path | Role |
| --- | --- |
| `persistence/db.py` | SQLite schema + connections |
| `readiness/service.py` | Readiness queue queries |
| `work_orders/service.py` | Work Order queries |
| `events/store.py` | Append-only audit trail |
| `api/routes.py` | FastAPI router |
| `api/deps.py` | Server-injected service dependencies |
| `orchestration/engine.py` | Scheduler |
| `agent_bridge/protocol.py` | `AgentRuntimeBridge` protocol |
| `agents/schema.py` | `AgentManifest` schema and validation |
| `agents/paths.py` | Per-project manifest paths under `~/.hermes/livingcolor/projects/{KEY}/agents/` |
| `agents/registry.py` | `AgentManifestRegistry` — load/cache manifests and `automation.yaml` state |

## Invariants

- Delivery Runtime is **Hermes-free** — no imports from `hermes_cli`, Hermes `tools`, or host agent loops.
- LivingColor Server (`lc_server/`) owns integrations and agent runtime adapters.
- Events are append-only — never UPDATE or DELETE audit rows.
- Readiness analysis must not mutate Jira or create Work Orders automatically in MVP.
- Work Orders are created only via explicit human promotion (`POST /readiness/{id}/promote`).
- Gates pause orchestration; Jira writes happen only after human gate approval: the Original Estimate write-back fires at `analysis_plan` (Gate 1) approval (best-effort, shadow-mode-aware, never blocking); all other Jira mutations remain post-Gate 3.
- Agent runtime is replaceable via `AgentRuntimeBridge` — implementations live in `lc_server/agent_bridge/`.

## FAST DEV mode

During active delivery implementation (workspace confinement, patch quality, MR draft prep):

```bash
export LIVINGCOLOR_FAST_DEV=true
# Prefer targeted unit tests for touched modules over the full suite.
```

- **Do run:** targeted unit tests for touched modules.
- **Do not run by default:** BN shadow evaluation, live/shadow corpus evaluation, full `tests/delivery_runtime/`, audit report generation.

Implementation helpers (when present): `delivery_runtime/fast_dev/`.

## Related docs

- [`../docs/superpowers/plans/2026-06-28-livingcolor-moa-delivery.md`](../docs/superpowers/plans/2026-06-28-livingcolor-moa-delivery.md)
- [`../docs/superpowers/specs/2026-06-28-livingcolor-moa-delivery-design.md`](../docs/superpowers/specs/2026-06-28-livingcolor-moa-delivery-design.md)
- [`../README.md`](../README.md)
