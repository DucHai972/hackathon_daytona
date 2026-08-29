from __future__ import annotations

import io
import json
import urllib.error

import pytest

from darwin_debugger.provider import OpenAICompatibleProvider, PatchProposal, ProviderError


def test_patch_proposal_parses_fenced_json() -> None:
    proposal = PatchProposal.parse(
        "```json\n"
        '{"summary":"fix boundary","files":'
        '[{"path":"src/a.py","content":"x = 2\\n"}]}\n'
        "```"
    )

    assert proposal.summary == "fix boundary"
    assert proposal.files[0].path == "src/a.py"
    assert proposal.files[0].content == "x = 2\n"


@pytest.mark.parametrize("path", ["/etc/passwd", "../secret", "src/../../secret"])
def test_patch_proposal_rejects_unsafe_paths(path: str) -> None:
    raw = f'{{"summary":"bad","files":[{{"path":"{path}","content":"x"}}]}}'

    with pytest.raises(ProviderError, match="unsafe replacement path"):
        PatchProposal.parse(raw)


def test_patch_proposal_rejects_unbounded_file_count() -> None:
    files = ",".join(f'{{"path":"file_{index}.py","content":"x"}}' for index in range(9))

    with pytest.raises(ProviderError, match="more than 8"):
        PatchProposal.parse(f'{{"summary":"too many","files":[{files}]}}')


def test_provider_caps_completion_tokens(monkeypatch) -> None:
    captured = {}

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse(b'{"choices":[{"message":{"content":"ok"}}]}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(
        api_key="secret",
        model="model",
        timeout_seconds=12,
        max_completion_tokens=2048,
    )

    assert provider.complete(system="system", user="user") == "ok"
    assert captured["body"]["max_completion_tokens"] == 2048
    assert captured["timeout"] == 12


def test_provider_rejects_non_positive_completion_cap() -> None:
    with pytest.raises(ProviderError, match="must be positive"):
        OpenAICompatibleProvider(api_key="secret", model="model", max_completion_tokens=0)


def test_provider_sanitizes_operational_details_from_http_errors(monkeypatch) -> None:
    body = io.BytesIO(
        b'{"error":"visit https://provider.example/team/'
        b'88aa4233-04c3-4161-a738-da044c55759b using xai-secretcredential123"}'
    )

    def reject(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, body)

    monkeypatch.setattr("urllib.request.urlopen", reject)
    provider = OpenAICompatibleProvider(api_key="secret", model="model")

    with pytest.raises(ProviderError) as captured:
        provider.complete(system="system", user="user")

    message = str(captured.value)
    assert "HTTP 403" in message
    assert "https://" not in message
    assert "88aa4233" not in message
    assert "xai-secretcredential123" not in message
