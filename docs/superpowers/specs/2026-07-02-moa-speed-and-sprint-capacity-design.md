# MoA Speed Optimization & Sprint Capacity Honesty — Design

**Date:** 2026-07-02
**Status:** Approved (user delegated final decisions)
**Scope:** `livingcolor-plugin` only — no changes to the deployed Hermes runtime (`~/.hermes/hermes-agent`).

## Context

Two problems reported:

1. **Every LLM step of the delivery workflow is very slow.** The deployed Hermes MoA
   runtime (`agent/moa_loop.py`) re-runs all reference models on **every agent
   iteration that produced a new tool result** (the reference cache key includes
   tool results), blocks on the slowest reference, and imposes no token cap on
   references. The current nemotron-tier presets use `deepseek/deepseek-v4-pro`
   and `openai/gpt-5.5` as references — both slow reasoning models. With the
   analyst allowed 15 iterations and the planner 20, a single ticket analysis can
   trigger dozens of reference fan-outs.
2. **The sprint panel appears to ignore the configured capacity.** With
   `sprint.capacity_days: 2.0`, the user sees ~6 tickets of 8h each (6
   person-days). Investigation shows the selection engine
   (`build_sprint_recommendation`) is correct — the persisted BN sprint contains
   exactly 2.0d of tickets for a 2.0d capacity. The problem is downstream:
   `build_selected_sprint_payload` appends non-ready backlog tickets
   (`needs_clarification`, `not_ready`, `analysis_failed`) to the payload with
   `sprintSelected: true`, `merge_active_work_orders_into_sprint` adds in-flight
   work orders, and the kanban "Sprint" column renders all of them together.
   Missing estimations default to 1.0d (8h), producing the "6 × 8h" impression.
   Additionally, ready tickets that do not fit the capacity are silently dropped
   from the payload, and changing capacity in project settings does not rebuild
   the persisted sprint until the next daily analysis.

## Constraints

- Keep the Hermes MoA architecture with the Nemotron aggregator
  (`nvidia/nemotron-3-super-120b-a12b`) for analyst and planner.
- The developer role keeps its non-nemotron preset (`lc-developer`, Opus
  aggregator).
- Plugin-only changes: presets, iteration budgets, concurrency, payload and UI.
- User accepted the speed/diversity trade-off: fewer, faster reference models.

## Workstream 1 — MoA speed

### 1.1 Slimmer, faster reference models (`lc_server/moa/presets.yaml`)

| Preset | Aggregator (unchanged) | References before | References after |
| --- | --- | --- | --- |
| `lc-analyst-nemotron` | `nvidia/nemotron-3-super-120b-a12b` | `deepseek/deepseek-v4-pro`, `openai/gpt-5.5` | `nvidia/nemotron-3-nano-30b-a3b` (nvidia), `z-ai/glm-5.2` (openrouter) |
| `lc-planner-nemotron` | `nvidia/nemotron-3-super-120b-a12b` | `nvidia/nemotron-3-nano-30b-a3b`, `deepseek/deepseek-v4-pro`, `openai/gpt-5.5` | `nvidia/nemotron-3-nano-30b-a3b` (nvidia), `z-ai/glm-5.2` (openrouter) |
| `lc-developer` | `anthropic/claude-opus-4.8` | `openai/gpt-5.5`, `anthropic/claude-sonnet-4.6`, `z-ai/glm-5.2` | `openai/gpt-5.5`, `anthropic/claude-sonnet-4.6` |

- Standard and premium tiers are left untouched (not used by default).
- `presetVersion` bumps: `lc-analyst-nemotron` 1.2.0 → 1.3.0,
  `lc-planner-nemotron` 1.2.0 → 1.3.0, `lc-developer` 1.1.1 → 1.2.0.
- `_BUNDLE_VERSION` in `lc_server/moa/loader.py` 1.2.1 → 1.3.0 so
  `ensure_moa_presets_from_bundle()` re-merges the presets into
  `~/.hermes/config.yaml` at server startup (managed presets only; user-edited
  presets are preserved per existing bootstrap semantics).

Rationale: reference calls are advisory only (the aggregator is the acting
model). Replacing two slow reasoning references with one small Nemotron and one
fast GLM keeps two diverse perspectives while cutting per-iteration reference
latency substantially. The aggregators — the actual quality gate — do not
change.

### 1.2 Iteration budgets

Each agent iteration under MoA costs one full reference fan-out plus one
aggregator call, so max-iteration budgets multiply directly into wall-clock
time.

| Role | Before | After | Files |
| --- | --- | --- | --- |
| analyst | 15 | 8 | `lc_server/agent_templates/v1/analyst.yaml.tmpl` (maxIterations), `lc_server/agent_bridge/hermes_analyst.py` (legacy fallback) |
| planner | 20 | 12 | `lc_server/agent_templates/v1/planner.yaml.tmpl`, `lc_server/agent_bridge/hermes_planner.py` (legacy fallback) |
| developer | 60 | 60 (unchanged) | — |

- `lc_server/agent_templates/v1/manifest.json` version 1.8.0 → 1.9.0 so
  `provisioning/upgrade.py` auto re-renders provisioned per-project manifests
  (non-manually-edited only).

Risk: complex tickets could exhaust 8 analyst iterations. Mitigation: the
analyst prompt is already structured around a bounded fetch-then-analyze flow;
if truncation shows up in practice, the budget is a one-line manifest bump.

### 1.3 Ticket-level analysis concurrency

- `delivery_runtime/readiness/analysis_dispatcher.py`: the constructor clamps
  concurrency with `min(max(1, concurrency), 3)` — raise the cap to 5 and the
  default from 3 to 5.
- `delivery_runtime/readiness/scanner.py`: `analysis_concurrency` default 3 → 5.
- The 180s per-ticket timeout is unchanged.

### Out of scope (documented for future work)

The dominant remaining cost — references re-running on every tool result and
having no token cap — lives in Hermes (`agent/moa_loop.py`) and is excluded per
the plugin-only constraint. If speed is still unsatisfactory after this change,
the next lever is a Hermes-side change (run references only on new user turns,
cap reference `max_tokens`, add a per-reference timeout).

## Workstream 2 — Sprint capacity honesty

### 2.1 Backend payload stops mislabeling (`delivery_runtime/pm_inbox/sprint_selection.py`)

- Backlog extras (statuses `needs_clarification`, `not_ready`,
  `analysis_failed`) are appended with `sprintSelected: false` (currently
  `true`).
- Ready tickets ranked by `build_sprint_recommendation` but **not** selected
  (over capacity) are added to the payload as backlog entries with
  `sprintSelected: false` and `readinessStatus: "ready"`, so they remain
  visible instead of silently disappearing.
- `sprint_capacity_used_days` and `usedDays` semantics are unchanged: only
  ready + selected (or in-flight selected) tickets count toward capacity.
  `_ticket_counts_toward_sprint_capacity` must be updated so a non-in-development
  ticket counts only when `sprintSelected` is true (not merely `ready`), with the
  same fix mirrored in `ui/src/app/delivery/sprint-capacity.ts`.

### 2.2 Kanban UI: strict Sprint column + new Backlog column (`ui/src/app/delivery/kanban-routing.ts`, `kanban-board.tsx`)

- New column id `backlog`, rendered after `sprint`.
- The **Sprint** column shows only tickets with `sprintSelected === true` and
  `readinessStatus === 'ready'` (and not already in dev/gate/done columns).
- The **Backlog** column shows the rest: non-selected ready tickets (over
  capacity), `needs_clarification`, `not_ready`, `analysis_failed`. Existing
  CTAs (`Clarify`, `View blockers`, `Approve dev`) follow the ticket to the
  backlog column.
- The sprint header strip (`{usedDays}d / {capacityDays}d`) is unchanged and now
  visually matches the Sprint column contents.

### 2.3 Rebuild sprint on settings change (`delivery_runtime/api/routes.py`)

- `PUT /project-config` triggers a sprint rebuild (same logic as
  `DailyAnalysisPipeline._rebuild_selected_sprint`: build payload, merge active
  work orders, persist) when `sprintCapacityDays` or `sprintDurationDays` is
  present in the request, unless the sprint state has `manualOverride`.
- The rebuild helper is extracted into `sprint_selection.py` (e.g.
  `rebuild_and_persist_selected_sprint(project_key)`) so the pipeline and the
  route share one implementation. Best-effort: a rebuild failure must not fail
  the settings save (log + continue).

## Data flow after the change

```
readiness_records + ticket_estimations
  → build_sprint_recommendation (greedy within capacity_days)   [unchanged]
  → build_selected_sprint_payload
       selected ready        → sprintSelected: true
       ready over capacity   → sprintSelected: false  [new]
       non-ready extras      → sprintSelected: false  [fixed]
  → merge_active_work_orders_into_sprint                        [unchanged]
  → persist / API
  → kanban: Sprint column (selected only) + Backlog column (rest)  [new]
```

## Error handling

- MoA preset re-merge failures at startup already fall back to single-model
  inference (`resolve_moa_or_fallback`); unchanged.
- Sprint rebuild on config save is best-effort and never blocks the save.

## Testing

- `tests/lc_server/test_moa_loader.py`: bundle version 1.3.0, new reference
  lists for the three modified presets.
- `tests/lc_server/test_inference_config.py`: unchanged tier mapping still
  holds (developer never maps to nemotron).
- `tests/delivery_runtime/test_reporter_template.py` and template tests:
  manifest version 1.9.0, analyst maxIterations 8, planner 12.
- New/updated dispatcher tests: concurrency cap 5.
- `tests/delivery_runtime/test_sprint_selection*.py`:
  - extras carry `sprintSelected: false`;
  - over-capacity ready tickets present with `sprintSelected: false`;
  - `usedDays` unchanged (counts only selected).
- New route test: `PUT /project-config` with a smaller capacity rebuilds and
  persists a sprint whose `usedDays <= capacityDays`; `manualOverride` skips
  rebuild.
- UI tests: `kanban-routing.test.ts` covers the Backlog column split;
  `sprint-capacity.test.ts` covers the `sprintSelected`-based counting.
