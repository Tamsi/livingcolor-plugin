"""hermes_cli.jira_dashboard shim points at jira_dashboard.service."""

import json


def test_shim_installs_hermes_cli_jira_dashboard():
    import hermes_cli
    from jira_dashboard import service
    from jira_dashboard.compat import install_hermes_cli_jira_dashboard_shim

    install_hermes_cli_jira_dashboard_shim()

    import hermes_cli.jira_dashboard as jira_mod

    assert jira_mod is service
    assert hermes_cli.jira_dashboard is service
    assert jira_mod.JIRA_MCP_NAME == "jira"


def test_parse_tool_payload_unwraps_mcp_atlassian_stringified_result():
    from jira_dashboard.service import _extract_single_issue, _parse_tool_payload

    issue = {
        "id": "30671",
        "key": "TVP-2254",
        "summary": "Airship country rename",
    }
    raw = {
        "result": json.dumps(issue),
        "structuredContent": {"result": json.dumps(issue)},
    }

    parsed = _parse_tool_payload(raw)

    assert parsed == issue
    assert _extract_single_issue(parsed) == issue
