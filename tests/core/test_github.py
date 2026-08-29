from __future__ import annotations

import io
import json
import urllib.error

import pytest

from darwin_debugger.github import GitHubClient, GitHubError


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_fetch_issue_and_open_pull_request_use_rest_contract() -> None:
    calls = []
    responses = iter(
        [
            {
                "title": "Fix totals",
                "body": "The total is wrong.",
                "html_url": "https://github.com/acme/widgets/issues/7",
            },
            {"html_url": "https://github.com/acme/widgets/pull/9"},
        ]
    )

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return FakeResponse(json.dumps(next(responses)).encode())

    client = GitHubClient(token="github_pat_not-a-real-secret", opener=opener)

    issue = client.fetch_issue("acme/widgets", 7)
    pull_url = client.open_pull_request(
        "acme/widgets", "darwin/issue-7", "main", "Fix #7", "Fixes #7"
    )

    assert issue.title == "Fix totals"
    assert issue.body == "The total is wrong."
    assert pull_url.endswith("/pull/9")
    assert calls[0][0].method == "GET"
    assert calls[1][0].method == "POST"
    assert json.loads(calls[1][0].data) == {
        "head": "darwin/issue-7",
        "base": "main",
        "title": "Fix #7",
        "body": "Fixes #7",
    }
    assert calls[0][1] == 30


def test_github_http_error_never_echoes_token_or_operational_url() -> None:
    token = "github_pat_this-is-a-secret-value"
    body = io.BytesIO(f'{{"message":"token {token}; see https://github.example/private"}}'.encode())

    def opener(request, *, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, body)

    client = GitHubClient(token=token, opener=opener)

    with pytest.raises(GitHubError) as captured:
        client.fetch_issue("acme/widgets", 7)

    message = str(captured.value)
    assert "HTTP 403" in message
    assert token not in message
    assert "https://" not in message


@pytest.mark.parametrize("repo", ["missing-slash", "a/b/c", "../owner/repo"])
def test_github_rejects_invalid_repository_names(repo: str) -> None:
    client = GitHubClient(token="secret")

    with pytest.raises(GitHubError, match="owner/name"):
        client.fetch_issue(repo, 1)
