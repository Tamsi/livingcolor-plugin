"""Tests for Hermes tools.mcp_tool compatibility shims."""

from __future__ import annotations

import inspect


def test_reconnect_mcp_server_shim_accepts_config(monkeypatch):
    import tools.mcp_tool as mcp

    monkeypatch.setattr(mcp, "reconnect_mcp_server", lambda server_name: True, raising=False)
    monkeypatch.setattr("jira_dashboard.mcp_compat._installed", False, raising=False)

    from jira_dashboard.mcp_compat import install_mcp_tool_shims

    install_mcp_tool_shims()

    sig = inspect.signature(mcp.reconnect_mcp_server)
    params = list(sig.parameters)
    assert "server_name" in params
    assert "config" in params


def test_call_tool_result_iserror_compat_patch():
    from jira_dashboard.mcp_compat import install_mcp_tool_shims

    install_mcp_tool_shims()
    from mcp.types import CallToolResult, TextContent

    ok = CallToolResult(content=[TextContent(type="text", text="ok")], is_error=False)
    err = CallToolResult(content=[TextContent(type="text", text="bad")], is_error=True)
    assert ok.isError is False
    assert err.isError is True
