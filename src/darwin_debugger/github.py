"""Small, credential-safe GitHub REST adapter."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .provider import _sanitize_error_detail


class GitHubError(RuntimeError):
    """Raised when GitHub rejects a request or returns an invalid response."""


class UrlOpener(Protocol):
    def __call__(self, request: urllib.request.Request, *, timeout: int) -> Any: ...


@dataclass(frozen=True, slots=True)
class GitHubIssue:
    repo: str
    number: int
    title: str
    body: str
    url: str


def validate_repo(repo: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise GitHubError("repo must use the owner/name form")
    return repo


class GitHubClient:
    def __init__(
        self,
        *,
        token: str,
        api_url: str = "https://api.github.com",
        timeout_seconds: int = 30,
        opener: UrlOpener = urllib.request.urlopen,
    ) -> None:
        if not token:
            raise GitHubError("GITHUB_TOKEN is required")
        self._token = token
        self._api_url = api_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._opener = opener

    @classmethod
    def from_environment(cls) -> GitHubClient:
        return cls(
            token=os.environ.get("GITHUB_TOKEN", ""),
            api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
            timeout_seconds=int(os.environ.get("GITHUB_TIMEOUT_SECONDS", "30")),
        )

    def fetch_issue(self, repo: str, number: int) -> GitHubIssue:
        repo = validate_repo(repo)
        if number < 1:
            raise GitHubError("issue number must be positive")
        payload = self._request("GET", f"/repos/{repo}/issues/{number}")
        title = payload.get("title")
        body = payload.get("body")
        url = payload.get("html_url")
        if not isinstance(title, str) or not isinstance(url, str):
            raise GitHubError("GitHub issue response is missing title or URL")
        return GitHubIssue(
            repo=repo,
            number=number,
            title=title,
            body=body if isinstance(body, str) else "",
            url=url,
        )

    def open_pull_request(
        self,
        repo: str,
        head: str,
        base: str,
        title: str,
        body: str,
    ) -> str:
        repo = validate_repo(repo)
        if not all(isinstance(value, str) and value.strip() for value in (head, base, title)):
            raise GitHubError("pull request head, base, and title must be non-empty")
        payload = self._request(
            "POST",
            f"/repos/{repo}/pulls",
            {"head": head, "base": base, "title": title, "body": body},
        )
        url = payload.get("html_url")
        if not isinstance(url, str) or not url:
            raise GitHubError("GitHub pull request response is missing its URL")
        return url

    def _request(
        self, method: str, path: str, payload: dict[str, object] | None = None
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self._api_url + path,
            data=data,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "User-Agent": "darwin-debugger/0.1",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method=method,
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace")
            safe = _sanitize_error_detail(detail, secrets=(self._token,))
            raise GitHubError(f"GitHub API returned HTTP {exc.code}: {safe}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            safe = _sanitize_error_detail(str(exc), secrets=(self._token,))
            raise GitHubError(f"GitHub API request failed: {safe}") from exc
        if not isinstance(result, dict):
            raise GitHubError("GitHub API returned a non-object response")
        return result
