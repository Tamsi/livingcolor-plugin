"""Jira REST fallback for readiness scans when MCP is unavailable."""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_READINESS_FIELDS = [
    "summary",
    "description",
    "status",
    "assignee",
    "priority",
    "issuetype",
    "labels",
    "comment",
    "attachment",
]


def _jira_rest_auth_headers() -> dict[str, str] | None:
    from lc_server.integrations.mcp_env_bootstrap import hydrate_cloud_credentials

    hydrate_cloud_credentials()
    jira_url = (os.environ.get("JIRA_URL") or "").strip().rstrip("/")
    token = (os.environ.get("JIRA_API_TOKEN") or "").strip()
    username = (os.environ.get("JIRA_USERNAME") or "").strip()
    if not jira_url or not token or not username:
        return None
    credentials = base64.b64encode(f"{username}:{token}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "LivingColor Server",
        "X-Atlassian-Request-Id": "livingcolor-readiness-rest",
    }


def _jira_rest_request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    headers = _jira_rest_auth_headers()
    if not headers:
        raise RuntimeError("Jira REST credentials are not configured")

    from lc_server.integrations.mcp_env_bootstrap import hydrate_cloud_credentials

    hydrate_cloud_credentials()
    jira_url = (os.environ.get("JIRA_URL") or "").strip().rstrip("/")
    url = f"{jira_url}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Jira REST {method} {path} failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Jira REST {method} {path} failed: {exc}") from exc

    if not raw:
        return {}
    return json.loads(raw)


def fetch_issues_for_readiness_via_rest(
    project_key: str,
    *,
    jql_variants: tuple[str, ...],
    max_results: int = 200,
) -> list[dict[str, Any]]:
    """Fetch Jira issues through REST when MCP is blocked or unreachable."""
    last_error: Exception | None = None
    for jql in jql_variants:
        try:
            payload = _jira_rest_request(
                "POST",
                "/rest/api/3/search/jql",
                {
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": _READINESS_FIELDS,
                },
            )
        except Exception as exc:
            last_error = exc
            logger.warning("Jira REST readiness search failed jql=%s: %s", jql[:120], exc)
            continue

        issues = payload.get("issues") if isinstance(payload, dict) else None
        if isinstance(issues, list) and issues:
            logger.info(
                "Jira REST readiness fallback returned %s issue(s) for project %s",
                len(issues),
                project_key,
            )
            return [issue for issue in issues if isinstance(issue, dict)]

    if last_error is not None:
        raise RuntimeError(str(last_error))
    return []
