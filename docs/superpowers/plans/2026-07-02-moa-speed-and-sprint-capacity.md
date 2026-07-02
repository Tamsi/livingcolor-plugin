# MoA Speed Optimization & Sprint Capacity Honesty — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the wall-clock time of every MoA-backed LLM step (analyst/planner/developer) using plugin-only levers, and make the sprint panel honestly reflect the configured capacity.

**Architecture:** Workstream 1 slims the MoA presets to fast reference models, lowers analyst/planner iteration budgets, and raises ticket-level analysis concurrency. Workstream 2 fixes the `sprintSelected` flag at the payload source (`sprint_selection.py`), splits the kanban Sprint column into strict Sprint + new Backlog columns, and rebuilds the persisted sprint when capacity settings change.

**Tech Stack:** Python (FastAPI, sqlite), pytest; React/TypeScript UI tested with vitest.

**Spec:** `docs/superpowers/specs/2026-07-02-moa-speed-and-sprint-capacity-design.md`

---

### Task 1: Slim the nemotron/developer MoA presets and bump the bundle version

**Files:**
- Modify: `lc_server/moa/presets.yaml`
- Modify: `lc_server/moa/loader.py:6`
- Test: `tests/lc_server/test_moa_loader.py`

- [ ] **Step 1: Update the loader tests to the new expectations**

Replace the two tests in `tests/lc_server/test_moa_loader.py` with:

```python
from lc_server.moa.loader import bundled_preset_version, load_bundled_presets


def test_load_bundled_presets_contains_standard_and_premium():
    presets = load_bundled_presets()
    assert "lc-developer" in presets
    assert "lc-developer-premium" in presets
    assert presets["lc-developer"]["aggregator"]["model"] == "anthropic/claude-opus-4.8"
    assert presets["lc-developer-premium"]["aggregator"]["model"] == "anthropic/claude-opus-4.8"
    assert bundled_preset_version() == "1.3.0"


def test_load_bundled_presets_contains_nemotron_tier():
    presets = load_bundled_presets()
    assert "lc-analyst-nemotron" in presets
    assert "lc-planner-nemotron" in presets
    assert "lc-developer-nemotron" not in presets
    assert presets["lc-planner-nemotron"]["aggregator"]["provider"] == "nvidia"
    assert presets["lc-planner-nemotron"]["aggregator"]["model"] == "nvidia/nemotron-3-super-120b-a12b"


def test_nemotron_presets_use_fast_references():
    presets = load_bundled_presets()
    expected_refs = [
        {"provider": "nvidia", "model": "nvidia/nemotron-3-nano-30b-a3b"},
        {"provider": "openrouter", "model": "z-ai/glm-5.2"},
    ]
    assert presets["lc-analyst-nemotron"]["reference_models"] == expected_refs
    assert presets["lc-planner-nemotron"]["reference_models"] == expected_refs


def test_developer_preset_has_two_references():
    presets = load_bundled_presets()
    assert presets["lc-developer"]["reference_models"] == [
        {"provider": "openrouter", "model": "openai/gpt-5.5"},
        {"provider": "openrouter", "model": "anthropic/claude-sonnet-4.6"},
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/lc_server/test_moa_loader.py -v`
Expected: FAIL (version is 1.2.1, reference lists differ)

- [ ] **Step 3: Update `lc_server/moa/presets.yaml`**

In `lc-analyst-nemotron`, replace the `reference_models` block and bump `presetVersion`:

```yaml
  lc-analyst-nemotron:
    aggregator:
      provider: nvidia
      model: nvidia/nemotron-3-super-120b-a12b
    reference_models:
      - provider: nvidia
        model: nvidia/nemotron-3-nano-30b-a3b
      - provider: openrouter
        model: z-ai/glm-5.2
    reference_temperature: 0.6
    aggregator_temperature: 0.4
    max_tokens: 4096
    enabled: true
    livingcolor:
      presetVersion: "1.3.0"
      role: analyst
      tier: nemotron
      managed: true
```

In `lc-planner-nemotron`, same `reference_models` (2 entries, drop `deepseek/deepseek-v4-pro` and `openai/gpt-5.5`), `presetVersion: "1.3.0"`. Aggregator unchanged.

In `lc-developer`, drop the `z-ai/glm-5.2` reference (keep `openai/gpt-5.5` and `anthropic/claude-sonnet-4.6`), bump `presetVersion` to `"1.2.0"`. Aggregator (Opus) unchanged.

Do not touch `lc-analyst`, `lc-planner`, `lc-analyst-premium`, `lc-planner-premium`, `lc-developer-premium`.

- [ ] **Step 4: Bump `_BUNDLE_VERSION` in `lc_server/moa/loader.py`**

```python
_BUNDLE_VERSION = "1.3.0"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/lc_server/test_moa_loader.py tests/lc_server/test_inference_config.py -v`
Expected: PASS (inference-config tier mapping is unaffected; developer still never maps to nemotron)

- [ ] **Step 6: Commit**

```bash
git add lc_server/moa/presets.yaml lc_server/moa/loader.py tests/lc_server/test_moa_loader.py
git commit -m "perf: use fast MoA reference models for nemotron tier and developer"
```

---

### Task 2: Lower analyst/planner iteration budgets and bump the template manifest

**Files:**
- Modify: `lc_server/agent_templates/v1/analyst.yaml.tmpl:11` (`maxIterations: 15` → `8`)
- Modify: `lc_server/agent_templates/v1/planner.yaml.tmpl:11` (`maxIterations: 20` → `12`)
- Modify: `lc_server/agent_templates/v1/manifest.json` (`"version": "1.8.0"` → `"1.9.0"`)
- Modify: `lc_server/agent_bridge/hermes_analyst.py:114` (fallback `max_iterations = 15` → `8`)
- Modify: `lc_server/agent_bridge/hermes_planner.py:135` (fallback `max_iterations = 20` → `12`)
- Test: `tests/lc_server/test_provisioning.py:64`, `tests/delivery_runtime/test_reporter_template.py:43`

- [ ] **Step 1: Update the test expectations**

In `tests/lc_server/test_provisioning.py` line 64, change:

```python
    assert manifest.runtime.max_iterations == 8
```

In `tests/delivery_runtime/test_reporter_template.py` line 43, change:

```python
    assert manifest["version"] == "1.9.0"
```

Search for any other assertion pinning analyst `15` / planner `20` iterations or manifest `1.8.0` and update it the same way:

Run: `rg -n "1\.8\.0|max_iterations == 15|max_iterations == 20|maxIterations: 15|maxIterations: 20" tests/`

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/lc_server/test_provisioning.py tests/delivery_runtime/test_reporter_template.py -v`
Expected: FAIL (templates still carry the old values)

- [ ] **Step 3: Apply the template and fallback changes**

- `analyst.yaml.tmpl` line 11: `maxIterations: 8`
- `planner.yaml.tmpl` line 11: `maxIterations: 12`
- `manifest.json`: `"version": "1.9.0"`
- `hermes_analyst.py` legacy fallback branch: `max_iterations = 8`
- `hermes_planner.py` legacy fallback branch: `max_iterations = 12`

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/lc_server/test_provisioning.py tests/delivery_runtime/test_reporter_template.py tests/delivery_runtime/test_agent_manifest.py -v`
Expected: PASS. The bumped manifest version makes `provisioning/upgrade.py` re-render provisioned manifests at next server start — no manual migration needed.

- [ ] **Step 5: Commit**

```bash
git add lc_server/agent_templates/v1/ lc_server/agent_bridge/hermes_analyst.py lc_server/agent_bridge/hermes_planner.py tests/
git commit -m "perf: lower analyst/planner MoA iteration budgets (15->8, 20->12)"
```

---

### Task 3: Raise ticket-analysis concurrency cap from 3 to 5

**Files:**
- Modify: `delivery_runtime/readiness/analysis_dispatcher.py:109,114`
- Modify: `delivery_runtime/readiness/scanner.py:54`
- Test: `tests/delivery_runtime/test_analysis_dispatcher.py`

- [ ] **Step 1: Update and add dispatcher tests**

In `tests/delivery_runtime/test_analysis_dispatcher.py`:

- `test_summary_to_dict_uses_spec_shape_with_durations` (constructs with `concurrency=10`): change `assert summary["concurrency"] == 3` to `== 5`.
- Add below `test_dispatcher_limits_concurrency_to_three` (keep that test as-is — explicit `concurrency=3` must still bound at 3):

```python
@pytest.mark.asyncio
async def test_dispatcher_caps_concurrency_at_five():
    backend = RecordingBackend()
    dispatcher = ReadinessAnalysisDispatcher(backend=backend, concurrency=10)
    snapshots = [_snapshot(f"TVP-{index}") for index in range(1, 13)]

    result = await dispatcher.analyze_many(snapshots, project_key="TVP", run_id="DA-1", force=True)

    assert result.summary.success == 12
    assert backend.max_running <= 5
```

- [ ] **Step 2: Run tests to verify the new/updated ones fail**

Run: `pytest tests/delivery_runtime/test_analysis_dispatcher.py -v`
Expected: `test_summary_to_dict_uses_spec_shape_with_durations` FAILS (still clamps to 3)

- [ ] **Step 3: Apply the concurrency change**

`delivery_runtime/readiness/analysis_dispatcher.py`:

```python
        concurrency: int = 5,
```

```python
        self._concurrency = min(max(1, concurrency), 5)
```

`delivery_runtime/readiness/scanner.py`:

```python
        analysis_concurrency: int = 5,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/delivery_runtime/test_analysis_dispatcher.py tests/delivery_runtime/test_readiness_scanner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add delivery_runtime/readiness/analysis_dispatcher.py delivery_runtime/readiness/scanner.py tests/delivery_runtime/test_analysis_dispatcher.py
git commit -m "perf: raise ticket analysis concurrency cap from 3 to 5"
```

---

### Task 4: Make the sprint payload honest about `sprintSelected`

**Files:**
- Modify: `delivery_runtime/pm_inbox/sprint_selection.py` (`build_selected_sprint_payload`, `_ticket_counts_toward_sprint_capacity`)
- Test: `tests/delivery_runtime/test_sprint_selection_task4.py`

- [ ] **Step 1: Rewrite the payload test to the new contract**

Replace `test_sprint_backlog_excludes_ready_overflow_tickets` in `tests/delivery_runtime/test_sprint_selection_task4.py` (keep the DB seeding block identical) with assertions for the new behavior:

```python
def test_sprint_payload_flags_selection_and_keeps_overflow_visible(_isolate_hermes_home):
    # ... identical seeding of RD-901/902/903 as today ...

    payload = build_selected_sprint_payload(project_key="TVP")
    tickets = {ticket["jiraKey"]: ticket for ticket in payload["tickets"]}

    assert tickets["TVP-901"]["sprintSelected"] is True
    # Overflow ready ticket is now visible, but not selected.
    assert tickets["TVP-902"]["sprintSelected"] is False
    assert tickets["TVP-902"]["readinessStatus"] == "ready"
    # Non-ready extras are visible and not selected.
    assert tickets["TVP-903"]["sprintSelected"] is False
    # Capacity math is untouched: only the selected ticket counts.
    assert payload["usedDays"] == 10.0
    assert payload["capacityDays"] == 15.0
```

Also add a used-days regression test in the same file:

```python
def test_used_days_counts_only_selected_tickets():
    from delivery_runtime.pm_inbox.sprint_selection import sprint_capacity_used_days

    tickets = [
        {"readinessStatus": "ready", "sprintSelected": True, "estimatedDays": 1.0},
        {"readinessStatus": "ready", "sprintSelected": False, "estimatedDays": 3.0},
        {"readinessStatus": "needs_clarification", "sprintSelected": False, "estimatedDays": 2.0},
    ]
    assert sprint_capacity_used_days(tickets) == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/delivery_runtime/test_sprint_selection_task4.py -v`
Expected: FAIL (TVP-902 missing from payload; extras carry `sprintSelected: True`)

- [ ] **Step 3: Implement in `sprint_selection.py`**

In `build_selected_sprint_payload`:

1. After computing `selected_ready_keys`, append overflow ready tickets to `backlog_extras` handling. Replace the current `backlog_extras` construction:

```python
    backlog_extras = [
        item
        for item in candidates
        if item.get("readinessStatus") != "ready" or item["jiraKey"] not in selected_ready_keys
    ]
```

2. In the extras loop, add a warning for overflow ready tickets and set `sprintSelected: False`:

```python
    for item in backlog_extras:
        status = str(item.get("readinessStatus") or "")
        warnings: list[str] = []
        if status == "needs_clarification":
            warnings.append("Needs clarification before development")
        elif status == "not_ready":
            warnings.append("Not ready for autonomous delivery")
        elif status == "analysis_failed":
            warnings.append(_ANALYSIS_FAILED_WARNING)
        elif status == "ready":
            warnings.append("Ready but over sprint capacity")
        _append_latest_analysis_warning(warnings, item)
        tickets_payload.append(
            {
                "readinessId": item["readinessId"],
                "jiraKey": item["jiraKey"],
                "title": item["title"],
                "estimatedDays": item["estimatedDays"],
                "priorityRank": _priority_rank(item.get("jiraSnapshot") or {}),
                "urgencyScore": 0.0,
                "sprintSelected": False,
                "warnings": warnings,
                "readinessStatus": status,
                "lastAnalysisError": item.get("lastAnalysisError"),
                "lastAnalysisFailedAt": item.get("lastAnalysisFailedAt"),
            }
        )
```

(The old `if item.get("readinessStatus") == "ready" and item["jiraKey"] in selected_ready_keys: continue` guard is no longer needed — the list comprehension already excludes selected ready tickets. Remove it.)

3. Tighten `_ticket_counts_toward_sprint_capacity` for non-in-development tickets:

```python
def _ticket_counts_toward_sprint_capacity(item: dict[str, Any]) -> bool:
    if item.get("inDevelopment"):
        if "sprintSelected" in item:
            return bool(item.get("sprintSelected"))
        # Legacy payloads: sprint-committed tickets stay ready in the panel after approve dev.
        return str(item.get("readinessStatus") or item.get("readiness_status") or "").strip().lower() == "ready"
    status = str(item.get("readinessStatus") or item.get("readiness_status") or "ready").strip().lower()
    if "sprintSelected" in item:
        return bool(item.get("sprintSelected")) and status == "ready"
    return status == "ready"
```

- [ ] **Step 4: Run the sprint test files**

Run: `pytest tests/delivery_runtime/test_sprint_selection.py tests/delivery_runtime/test_sprint_selection_task4.py tests/delivery_runtime/test_sprint_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add delivery_runtime/pm_inbox/sprint_selection.py tests/delivery_runtime/test_sprint_selection_task4.py
git commit -m "fix: stop flagging backlog extras as sprint-selected and keep overflow ready tickets visible"
```

---

### Task 5: Mirror the capacity rule in the UI counter

**Files:**
- Modify: `ui/src/app/delivery/sprint-capacity.ts`
- Test: `ui/src/app/delivery/sprint-capacity.test.ts`

- [ ] **Step 1: Add the failing test**

In `ui/src/app/delivery/sprint-capacity.test.ts`, add:

```typescript
it('does not count non-selected ready tickets (over capacity backlog)', () => {
  expect(
    ticketCountsTowardSprintCapacity({
      jiraKey: 'BN-3',
      title: 'Overflow',
      estimatedDays: 3,
      priorityRank: 1,
      urgencyScore: 0,
      warnings: [],
      readinessStatus: 'ready',
      sprintSelected: false
    } as never)
  ).toBe(false)
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ui && npx vitest run src/app/delivery/sprint-capacity.test.ts`
Expected: FAIL (non-dev ready tickets currently always count)

- [ ] **Step 3: Implement**

```typescript
export function ticketCountsTowardSprintCapacity(ticket: SprintTicket): boolean {
  const ready = (ticket.readinessStatus ?? 'ready').trim().toLowerCase() === 'ready'
  if (ticket.inDevelopment) {
    if (ticket.sprintSelected != null) {
      return ticket.sprintSelected
    }
    return (ticket.readinessStatus ?? '').trim().toLowerCase() === 'ready'
  }
  if (ticket.sprintSelected != null) {
    return ticket.sprintSelected && ready
  }
  return ready
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd ui && npx vitest run src/app/delivery/sprint-capacity.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ui/src/app/delivery/sprint-capacity.ts ui/src/app/delivery/sprint-capacity.test.ts
git commit -m "fix: mirror sprintSelected capacity rule in UI used-days counter"
```

---

### Task 6: Split the kanban into strict Sprint + Backlog columns

**Files:**
- Modify: `ui/src/app/delivery/kanban-routing.ts`
- Test: `ui/src/app/delivery/kanban-routing.test.ts` (existing "six columns" test + new routing test)

- [ ] **Step 1: Update/add tests**

In `kanban-routing.test.ts`:

- Update `returns six columns in pipeline order even when empty` to expect seven ids: `['sprint', 'backlog', 'plan', 'dev', 'code_mr', 'jira', 'done']` (rename the test accordingly).
- Add:

```typescript
it('routes non-selected and non-ready tickets to the backlog column', () => {
  const inbox = {
    waitingForApproval: [],
    activeDevelopments: [],
    selectedSprint: {
      sprintName: 'S',
      capacityDays: 2,
      usedDays: 2,
      durationDays: 14,
      overflowRisk: true,
      warnings: [],
      tickets: [
        { jiraKey: 'BN-1', title: 'Selected', readinessId: 'RD-1', estimatedDays: 1, priorityRank: 0, urgencyScore: 1, warnings: [], readinessStatus: 'ready', sprintSelected: true },
        { jiraKey: 'BN-2', title: 'Overflow', readinessId: 'RD-2', estimatedDays: 3, priorityRank: 1, urgencyScore: 0, warnings: [], readinessStatus: 'ready', sprintSelected: false },
        { jiraKey: 'BN-3', title: 'Clarify me', readinessId: 'RD-3', estimatedDays: 1, priorityRank: 2, urgencyScore: 0, warnings: [], readinessStatus: 'needs_clarification', sprintSelected: false }
      ]
    }
  } as never

  const columns = buildKanbanColumns(inbox, [])
  const byId = Object.fromEntries(columns.map(column => [column.id, column]))

  expect(byId.sprint.cards.map(card => card.jiraKey)).toEqual(['BN-1'])
  expect(byId.backlog.cards.map(card => card.jiraKey)).toEqual(['BN-2', 'BN-3'])
})
```

Adapt the inbox literal to the shape the existing tests in that file use (reuse their helper/fixture style if one exists).

- [ ] **Step 2: Run to verify failure**

Run: `cd ui && npx vitest run src/app/delivery/kanban-routing.test.ts`
Expected: FAIL (`backlog` column does not exist)

- [ ] **Step 3: Implement in `kanban-routing.ts`**

1. Extend the type and the accumulator:

```typescript
export type KanbanColumnId = 'sprint' | 'backlog' | 'plan' | 'dev' | 'code_mr' | 'jira' | 'done'
```

Add `backlog: []` to the `columns` record and `backlog: ''` to `GATE_CTA`.

2. In the final sprint-ticket loop, route strictly:

```typescript
  for (const ticket of inbox?.selectedSprint?.tickets ?? []) {
    if (gateJiraKeys.has(ticket.jiraKey) || devJiraKeys.has(ticket.jiraKey) || doneJiraKeys.has(ticket.jiraKey)) {
      continue
    }
    if (ticket.workOrderId || ticket.inDevelopment) {
      continue
    }
    const readinessId = ticket.readinessId?.trim()
    const isReady = (ticket.readinessStatus ?? 'ready').trim().toLowerCase() === 'ready'
    const isSelected = (ticket.sprintSelected ?? true) && isReady
    const targetColumn: KanbanColumnId = isSelected ? 'sprint' : 'backlog'
    columns[targetColumn].push({
      id: `${targetColumn}-${readinessId || ticket.jiraKey}`,
      jiraKey: ticket.jiraKey,
      title: ticket.title,
      readinessId: readinessId || undefined,
      estimatedDays: ticket.estimatedDays,
      priorityRank: ticket.priorityRank,
      readinessStatus: ticket.readinessStatus,
      warnings: ticket.warnings,
      ctaLabel: sprintCtaForTicket(ticket)
    })
  }
```

(`ticket.sprintSelected ?? true` keeps legacy persisted payloads — which only flagged selected ready tickets before this change — in the Sprint column.)

3. Add the column to the returned array, right after `sprint`:

```typescript
    { id: 'backlog', title: 'Backlog', accent: 'muted', cards: columns.backlog },
```

- [ ] **Step 4: Run UI tests and typecheck**

Run: `cd ui && npx vitest run src/app/delivery/ && npx tsc --noEmit`
Expected: PASS. If `kanban-board.tsx` or other consumers exhaustively switch on `KanbanColumnId`, fix the non-exhaustive spots the compiler reports (the board renders columns generically, so no change is expected there).

- [ ] **Step 5: Commit**

```bash
git add ui/src/app/delivery/kanban-routing.ts ui/src/app/delivery/kanban-routing.test.ts
git commit -m "feat: strict sprint column with separate backlog column in delivery kanban"
```

---

### Task 7: Rebuild the persisted sprint when capacity settings change

**Files:**
- Modify: `delivery_runtime/pm_inbox/sprint_selection.py` (new `rebuild_and_persist_selected_sprint`)
- Modify: `delivery_runtime/pm_inbox/daily_pipeline.py:386-411` (delegate to the new helper)
- Modify: `delivery_runtime/api/routes.py:604-646` (`update_project_config`)
- Test: `tests/delivery_runtime/test_delivery_api.py`

- [ ] **Step 1: Write the failing API tests**

Add a module-level seeding helper and two tests to `tests/delivery_runtime/test_delivery_api.py`. The test class already runs with `_isolate_hermes_home` and `install_phase25_project_mapping()` (default project `BN`), and existing config tests monkeypatch `automation_config.get_livingcolor_home` — follow `test_project_config_get_and_put` (line 179) for that setup.

```python
def _seed_estimated_ready_record(jira_key: str, estimated_days: float) -> str:
    init_db()
    with connect() as conn:
        record_id = next_public_id(conn, "RD")
        now = utc_now_iso()
        snapshot = {
            "key": jira_key,
            "summary": f"Ticket {jira_key}",
            "description": "Acceptance criteria: do the thing.",
            "status": "To Do",
            "issueType": "Story",
            "projectKey": "BN",
            "priority": "High",
            "assignee": "Tamsi Besson",
        }
        conn.execute(
            """
            INSERT INTO readiness_records (
                id, jira_key, project_key, title, readiness_score, readiness_status,
                analysis_summary, blockers_json, recommended_repos_json, confidence,
                estimated_days, jira_snapshot_json, analyzed_at, created_at, updated_at
            ) VALUES (?, ?, 'BN', ?, 82, 'ready', 'Ready', '[]', '[]', 0.82, ?, ?, ?, ?, ?)
            """,
            (record_id, jira_key, snapshot["summary"], estimated_days, json_dumps(snapshot), now, now, now),
        )
    return record_id
```

```python
    def test_put_project_config_rebuilds_selected_sprint(self, tmp_path, monkeypatch):
        from delivery_runtime.automation import config as automation_config
        from delivery_runtime.pm_inbox import store as pm_store

        home = tmp_path / "livingcolor"
        monkeypatch.setattr(automation_config, "get_livingcolor_home", lambda: home)
        _seed_estimated_ready_record("BN-901", 1.0)
        _seed_estimated_ready_record("BN-902", 3.0)

        response = self.client.put(
            "/api/delivery/project-config",
            json={"sprintCapacityDays": 1.0, "sprintDurationDays": 7},
        )
        assert response.status_code == 200

        state = pm_store.get_sprint_state(project_key="BN")
        recommendation = (state or {}).get("recommendation") or {}
        assert recommendation.get("capacityDays") == 1.0
        assert recommendation.get("usedDays", 0) <= 1.0
        selected = [
            ticket["jiraKey"]
            for ticket in recommendation.get("tickets") or []
            if ticket.get("sprintSelected") and ticket.get("readinessStatus") == "ready"
        ]
        assert selected == ["BN-901"]

    def test_put_project_config_respects_manual_override(self, tmp_path, monkeypatch):
        from delivery_runtime.automation import config as automation_config
        from delivery_runtime.pm_inbox import store as pm_store

        home = tmp_path / "livingcolor"
        monkeypatch.setattr(automation_config, "get_livingcolor_home", lambda: home)
        init_db()
        sentinel = {"sprintName": "Manual", "capacityDays": 9.0, "usedDays": 0.0, "tickets": []}
        with connect() as conn:
            pm_store.upsert_sprint_state(
                conn,
                project_key="BN",
                sprint_name="Manual",
                capacity_days=9.0,
                duration_days=14,
                recommendation=sentinel,
                memory_patch={"manualOverride": True},
            )

        response = self.client.put(
            "/api/delivery/project-config",
            json={"sprintCapacityDays": 1.0, "sprintDurationDays": 7},
        )
        assert response.status_code == 200

        state = pm_store.get_sprint_state(project_key="BN")
        assert (state or {}).get("recommendation") == sentinel
```

If `upsert_sprint_state` has a different signature in `delivery_runtime/pm_inbox/store.py`, adapt the call to the real one (check the function before writing the test).

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/delivery_runtime/test_delivery_api.py -k project_config -v`
Expected: the new tests FAIL (settings save does not rebuild)

- [ ] **Step 3: Extract the rebuild helper into `sprint_selection.py`**

Move the body of `DailyAnalysisPipeline._rebuild_selected_sprint` into:

```python
def rebuild_and_persist_selected_sprint(*, project_key: str) -> dict[str, Any]:
    """Rebuild the selected sprint from current settings and persist it.

    Respects auto-reset and manual override, mirroring the daily pipeline.
    """
    from delivery_runtime.pm_inbox.sprint_reset import maybe_auto_reset_sprint

    auto_reset = maybe_auto_reset_sprint(project_key=project_key)
    if auto_reset is not None:
        return auto_reset

    state = pm_store.get_sprint_state(project_key=project_key)
    memory = (state or {}).get("memory") or {}
    if isinstance(memory, dict) and memory.get("manualOverride"):
        return (state or {}).get("recommendation") or build_selected_sprint_payload(project_key=project_key)

    payload = build_selected_sprint_payload(project_key=project_key)
    payload = merge_active_work_orders_into_sprint(payload, project_key=project_key)
    persist_selected_sprint(
        project_key=project_key,
        payload=payload,
        memory_patch={"emptyBacklogUntilAnalysis": False},
    )
    return payload
```

Then reduce `DailyAnalysisPipeline._rebuild_selected_sprint` to:

```python
    def _rebuild_selected_sprint(self, *, project_key: str) -> dict[str, Any]:
        from delivery_runtime.pm_inbox.sprint_selection import rebuild_and_persist_selected_sprint

        return rebuild_and_persist_selected_sprint(project_key=project_key)
```

- [ ] **Step 4: Trigger the rebuild from the route**

In `update_project_config` (`routes.py`), after `save_delivery_project_config(...)` and before building the response:

```python
    if body.sprintCapacityDays is not None or body.sprintDurationDays is not None:
        try:
            from delivery_runtime.pm_inbox.sprint_selection import rebuild_and_persist_selected_sprint

            rebuild_and_persist_selected_sprint(project_key=target_key)
        except Exception:  # noqa: BLE001 - settings save must not fail on rebuild
            logger.warning("Sprint rebuild after config change failed", exc_info=True)
```

(Place it after `target_key` is computed. Use the module's existing `logger`; add `logger = logging.getLogger(__name__)` if the module has none.)

- [ ] **Step 5: Run the tests**

Run: `pytest tests/delivery_runtime/test_delivery_api.py -k project_config tests/delivery_runtime/test_daily_pipeline.py -v`
Expected: PASS (pipeline behavior unchanged — it now calls the shared helper)

- [ ] **Step 6: Commit**

```bash
git add delivery_runtime/pm_inbox/sprint_selection.py delivery_runtime/pm_inbox/daily_pipeline.py delivery_runtime/api/routes.py tests/delivery_runtime/test_delivery_api.py
git commit -m "feat: rebuild selected sprint when capacity settings change"
```

---

### Task 8: Targeted regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the touched Python test modules**

Run:

```bash
pytest tests/lc_server/test_moa_loader.py tests/lc_server/test_inference_config.py \
  tests/lc_server/test_provisioning.py tests/delivery_runtime/test_reporter_template.py \
  tests/delivery_runtime/test_analysis_dispatcher.py tests/delivery_runtime/test_sprint_selection.py \
  tests/delivery_runtime/test_sprint_selection_task4.py tests/delivery_runtime/test_sprint_report.py \
  tests/delivery_runtime/test_delivery_api.py tests/delivery_runtime/test_daily_pipeline.py -v
```

Expected: all PASS. (Per FAST DEV policy, do not run the full `tests/delivery_runtime/` suite or BN shadow evaluation.)

- [ ] **Step 2: Run the touched UI tests + typecheck**

Run: `cd ui && npx vitest run src/app/delivery/ && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 3: Fix any fallout and commit**

If other tests assert the old payload shape (`sprintSelected: True` on extras) or six kanban columns, update them to the new contract and commit:

```bash
git add -A tests/ ui/src/
git commit -m "test: align remaining fixtures with strict sprint selection contract"
```
