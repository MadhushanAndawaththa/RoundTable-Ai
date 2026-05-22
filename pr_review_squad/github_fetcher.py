"""Fetch a unified diff from a GitHub Pull Request URL."""
from __future__ import annotations

import os
import re
from typing import Optional

import requests


PR_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)/?$"
)


class GitHubFetchError(Exception):
    pass


def parse_pr_url(url: str) -> tuple[str, str, int]:
    match = PR_URL_RE.match(url.strip())
    if not match:
        raise GitHubFetchError(
            f"Not a valid GitHub PR URL: {url!r}. "
            "Expected format: https://github.com/<owner>/<repo>/pull/<number>"
        )
    return match["owner"], match["repo"], int(match["number"])


def fetch_pr_diff(url: str, token: Optional[str] = None, timeout: int = 30) -> str:
    """Fetch a unified diff for a GitHub PR using the REST API's diff media type."""
    owner, repo, number = parse_pr_url(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"

    token = token or os.environ.get("GITHUB_TOKEN") or ""
    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "pr-review-squad",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(api_url, headers=headers, timeout=timeout)
    if response.status_code == 404:
        raise GitHubFetchError(
            f"PR not found (404): {url}. If it is private, set GITHUB_TOKEN in your .env."
        )
    if response.status_code == 403:
        raise GitHubFetchError(
            "GitHub rate-limited the request (403). Set GITHUB_TOKEN in your .env to raise the limit."
        )
    if not response.ok:
        raise GitHubFetchError(
            f"GitHub API error {response.status_code}: {response.text[:200]}"
        )

    diff = response.text
    if not diff.strip():
        raise GitHubFetchError("GitHub returned an empty diff.")
    return diff
