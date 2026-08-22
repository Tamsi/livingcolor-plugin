"""Tests for MCP Jira originalEstimate invoker argument shaping."""

from __future__ import annotations

import json
from unittest.mock import patch

from lc_server.integrations.jira_estimate_invoker import McpJiraEstimateInvoker


def test_update_estimate_prefers_json_string_fields_for_mcp_atlassian():
    calls: list[dict] = []

    def fake_invoke(tool: str, args: dict) -> dict:
        calls.append(args)
        fields = args.get("fields")
        if isinstance(fields, str):
            return {"result": "ok"}
        raise RuntimeError("fields must be a string")

    def fake_find_tool(tool_names, *candidates):
        return "jira_update_issue"

    invoker = McpJiraEstimateInvoker()
    with patch.object(
        McpJiraEstimateInvoker,
        "_connect",
        return_value=(["jira_update_issue"], fake_invoke, None),
    ), patch(
        "hermes_cli.jira_dashboard._find_tool",
        fake_find_tool,
    ), patch.object(
        McpJiraEstimateInvoker,
        "_invoke_parsed",
        side_effect=lambda invoke, tool, args: invoke(tool, args),
    ):
        invoker.update_estimate("TVP-10", "1d")

    assert calls
    first = calls[0]
    assert first["issue_key"] == "TVP-10"
    assert isinstance(first["fields"], str)
    parsed = json.loads(first["fields"])
    assert parsed["timetracking"]["originalEstimate"] == "1d"
