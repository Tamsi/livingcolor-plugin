#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Hermes-free unit tests exercised in CI (no hermes_cli / live MCP required).
PASSING_DELIVERY_RUNTIME_TESTS=(
  tests/delivery_runtime/test_analysis_dispatcher.py
  tests/delivery_runtime/test_analyst_prompt.py
  tests/delivery_runtime/test_communication_language.py
  tests/delivery_runtime/test_context_engine.py
  tests/delivery_runtime/test_developer_phases.py
  tests/delivery_runtime/test_fast_dev_mode.py
  tests/delivery_runtime/test_gates_estimation_writeback.py
  tests/delivery_runtime/test_git_branch.py
  tests/delivery_runtime/test_git_branch_commit.py
  tests/delivery_runtime/test_hermes_messaging.py
  tests/delivery_runtime/test_jira_delivery_writeback.py
  tests/delivery_runtime/test_jira_estimation_format.py
  tests/delivery_runtime/test_jira_project_link.py
  tests/delivery_runtime/test_livingcolor_paths.py
  tests/delivery_runtime/test_local_projects.py
  tests/delivery_runtime/test_orchestration_background.py
  tests/delivery_runtime/test_orchestration_resume.py
  tests/delivery_runtime/test_pending_events.py
  tests/delivery_runtime/test_project_mapping_integration_branch.py
  tests/delivery_runtime/test_readiness_scoring.py
  tests/delivery_runtime/test_repo_architecture.py
  tests/delivery_runtime/test_repo_resolver.py
  tests/delivery_runtime/test_reporter_template.py
  tests/delivery_runtime/test_scope_contract.py
  tests/delivery_runtime/test_scope_validator.py
  tests/delivery_runtime/test_shadow_guards_publisher.py
  tests/delivery_runtime/test_skills_context.py
  tests/delivery_runtime/test_sprint_invoice.py
  tests/delivery_runtime/test_sprint_invoice_validation.py
  tests/delivery_runtime/test_sprint_selection.py
  tests/delivery_runtime/test_test_runner.py
  tests/delivery_runtime/test_ticket_quality.py
  tests/delivery_runtime/test_todo_filter.py
)

ROOT_TESTS=(
  tests/test_lc_constants.py
  tests/test_livingcolor_pm_tools.py
  tests/test_plugin_firebase_routes.py
  tests/test_plugin_load.py
)

python3 -m pytest \
  tests/cloud_api/ \
  "${PASSING_DELIVERY_RUNTIME_TESTS[@]}" \
  "${ROOT_TESTS[@]}" \
  "$@"
