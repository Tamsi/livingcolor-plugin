"""Tests for Hermes tools.mcp_tool compatibility shims."""

from __future__ import annotations

import inspect


def test_reconnect_mcp_server_shim_accepts_config(monkeypatch):
    import tools.mcp_tool as mcp

    monkeypatch.setattr(mcp, "reconnect_mcp_server", lambda server_name: True, raising=False)

    from jira_dashboard.mcp_compat import _installed, install_mcp_tool_shims

    monkeypatch.setattr("jira_dashboard.mcp_compat._installed", False, raising=False)
    install_mcp_tool_shims()

    sig = inspect.signature(mcp.reconnect_mcp_server)
    params = list(sig.parameters)
    assert "server_name" in params
    assert "config" in params

    calls: list[tuple[str, dict | None]] = []
    registered: list[dict] = []

    def fake_shutdown(name: str) -> None:
        calls.append((name, None))

    def fake_register(servers: dict) -> list[str]:
        registered.append(servers)
        return list(servers)

    monkeypatch.setattr(mcp, "shutdown_mcp_server", fake_shutdown, raising=False)
    monkeypatch.setattr(mcp, "register_mcp_servers", fake_register, raising=False)

    cfg = {"command": "uvx", "args": ["mcp-atlassian"]}
    mcp.reconnect_mcp_server("jira", cfg)

    assert calls == [("jira", None)]
    assert registered == [{"jira": cfg}]


def test_call_tool_result_iserror_compat_patch():
    from jira_dashboard.mcp_compat import install_mcp_tool_shims

    install_mcp_tool_shims()
    from mcp.types import CallToolResult, TextContent

    ok = CallToolResult(content=[TextContent(type="text", text="ok")], is_error=False)
    err = CallToolResult(content=[TextContent(type="text", text="bad")], is_error=True)
    assert ok.isError is False
    assert err.isError is True
