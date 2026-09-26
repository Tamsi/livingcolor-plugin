# LivingColor Server (`lc_server/`)

> Parent: [`../AGENTS.md`](../AGENTS.md) · Delivery domain: [`../delivery_runtime/AGENTS.md`](../delivery_runtime/AGENTS.md)

The **LivingColor Server** is the delivery orchestration host. It owns execution
bridges, persistence wiring, and external integrations. Mission Control UI lives
in `ui/` and ships via `dashboard/`.

## Scope

**Owns:**

- Server bootstrap and service wiring (`bootstrap.py`, `factory.py`)
- Jira readiness integration (`integrations/jira_readiness.py`)
- Agent runtime adapters (`agent_bridge/hermes_runtime.py`)
- Project automation provisioning (`provisioning/`)
- GitLab/GitHub/Jira write integrations for delivery execution
- Firebase / Team-mode bridges (`integrations/firestore_store.py`, `api/firebase_routes.py`)

**Does not own:**

- Delivery domain models and persistence → `delivery_runtime/`
- HTTP route definitions → `delivery_runtime/api/routes.py` (mounted by the host)
- Mission Control UI → `ui/src/app/delivery/`

## Architecture

```text
Mission Control (ui/ → dashboard/dist)
  ⇄ HTTP /api/plugins/livingcolor/… and /api/delivery/*
LivingColor Server (this package)
  ⇄ delivery_runtime/
  ⇄ agent_bridge/ → Hermes (replaceable)
  ⇄ integrations/ → Jira / GitLab / GitHub MCP
```

## Load-bearing entry points

| Path | Role |
| --- | --- |
| `bootstrap.py` | Wire `delivery_runtime.api.deps` at server startup |
| `factory.py` | Construct readiness/work-order/gate services |
| `integrations/jira_readiness.py` | Jira issue fetch for readiness scans |
| `agent_bridge/hermes_runtime.py` | Hermes-backed `AgentRuntimeBridge` |
| `agent_bridge/hermes_developer.py` | Hermes `AIAgent` loop for patch generation |
| `agent_bridge/hermes_analyst.py` | Hermes `AIAgent` loop for readiness analysis |
| `agent_bridge/hermes_sprint_reporter.py` | Hermes `AIAgent` loop for sprint retrospectives |
| `agent_bridge/developer_backend.py` | Selects Hermes vs heuristic developer backend |
| `provisioning/provisioner.py` | Writes per-project agent manifests and automation state |
| `provisioning/prerequisites.py` | Validates Jira/VCS/MCP prerequisites before setup |
| `provisioning/template_renderer.py` | Renders bundled agent templates (`agent_templates/v1/`) |

## Invariants

- Only this package (and deeper Hermes layers) may import Hermes CLI/tooling for delivery.
- `delivery_runtime/` must remain Hermes-free.
- Product data lives under `~/.hermes/livingcolor/` via `lc_constants.get_livingcolor_home()`.

## Project automation provisioning

Provisioning is triggered via `POST /api/delivery/projects/{projectKey}/setup-automation`
(routes live in `delivery_runtime/api/routes.py`; execution is delegated here).

**Prerequisites** (checked by `provisioning/prerequisites.py`):

- Jira project mapping exists in `~/.hermes/livingcolor/project_mapping.yaml`
- Jira and VCS MCP servers configured for the project
- VCS discovery returns at least one repo (or a default repo is set)

On success, `ProjectAutomationProvisioner` writes:

```text
~/.hermes/livingcolor/projects/{PROJECT_KEY}/
  automation.yaml
  agents/
    orchestrator.yaml   # declarative v1; not executed — OrchestrationEngine drives workflow
    analyst.yaml
    planner.yaml
    developer.yaml
    publisher.yaml
    reporter.yaml
```

Manifest schema and registry live in `delivery_runtime/agents/` (Hermes-free).
Templates are bundled under `lc_server/agent_templates/v1/`.

**Orchestrator vs OrchestrationEngine:** v1 workflow is driven by `OrchestrationEngine`
(Python), not the orchestrator manifest.

**API surface:**

| Endpoint | Role |
| --- | --- |
| `POST /api/delivery/projects/{key}/setup-automation` | Provision manifests; `?force=true` re-renders |
| `GET /api/delivery/projects/{key}/automation` | Read provisioned state and per-role manifest summary |

Returns `400` with `{ error: "prerequisites_missing", missing: [...] }` when setup
cannot proceed. Returns `404` on GET when automation was never provisioned.

Agent bridges load manifests via `AgentManifestRegistry` when automation is ready;
they fall back to legacy prompts when manifests are absent.
