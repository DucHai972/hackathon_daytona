"""Provider-neutral JSON model adapter."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Raised when the model provider fails or returns an invalid proposal."""


def _sanitize_error_detail(detail: str, *, secrets: tuple[str, ...] = ()) -> str:
    for secret in secrets:
        if secret:
            detail = detail.replace(secret, "[credential]")
    sanitized = re.sub(r"https?://\S+", "[url]", detail)
    sanitized = re.sub(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        "[id]",
        sanitized,
    )
    sanitized = re.sub(
        r"\b(?:sk|xai)-[A-Za-z0-9_-]{12,}\b|\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{12,}\b|\bAIza[A-Za-z0-9_-]{20,}\b",
        "[credential]",
        sanitized,
    )
    sanitized = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", "Bearer [credential]", sanitized)
    return " ".join(sanitized.split())[-500:]


class ModelProvider(Protocol):
    def complete(self, *, system: str, user: str) -> tuple[str, TokenUsage]: ...


@dataclass(frozen=True, slots=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )

    def to_journal(self, *, calls: int = 1) -> dict[str, int]:
        return {
            "prompt": self.prompt_tokens,
            "completion": self.completion_tokens,
            "total": self.total_tokens,
            "calls": calls,
        }

    @classmethod
    def from_payload(cls, payload: object) -> TokenUsage:
        usage = payload if isinstance(payload, dict) else {}

        def count(name: str) -> int:
            value = usage.get(name, 0)
            valid = isinstance(value, int) and not isinstance(value, bool) and value >= 0
            return value if valid else 0

        prompt = count("prompt_tokens")
        completion = count("completion_tokens")
        total = count("total_tokens")
        if total == 0 and (prompt or completion):
            total = prompt + completion
        return cls(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


@dataclass(frozen=True, slots=True)
class FileReplacement:
    path: str
    content: str


@dataclass(frozen=True, slots=True)
class PatchProposal:
    summary: str
    files: tuple[FileReplacement, ...]

    @classmethod
    def parse(cls, raw: str, *, max_files: int = 8) -> PatchProposal:
        text = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1)
        else:
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"model response is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ProviderError("model response must be a JSON object")
        summary = payload.get("summary", "")
        raw_files = payload.get("files")
        if not isinstance(summary, str) or not summary.strip():
            raise ProviderError("model response requires a non-empty summary")
        if not isinstance(raw_files, list) or not raw_files:
            raise ProviderError("model response requires at least one file replacement")
        if len(raw_files) > max_files:
            raise ProviderError(f"model tried to replace more than {max_files} files")
        replacements: list[FileReplacement] = []
        seen: set[str] = set()
        for item in raw_files:
            if not isinstance(item, dict):
                raise ProviderError("each file replacement must be an object")
            path = item.get("path")
            content = item.get("content")
            if not isinstance(path, str) or not isinstance(content, str):
                raise ProviderError("file replacements require string path and content")
            pure = PurePosixPath(path)
            if pure.is_absolute() or ".." in pure.parts or not pure.parts:
                raise ProviderError(f"unsafe replacement path: {path}")
            normalized = pure.as_posix()
            if normalized in seen:
                raise ProviderError(f"duplicate replacement path: {normalized}")
            seen.add(normalized)
            replacements.append(FileReplacement(path=normalized, content=content))
        return cls(summary=summary.strip(), files=tuple(replacements))


class OpenAICompatibleProvider:
    """Minimal adapter for OpenRouter and other Chat Completions-compatible APIs."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: int = 90,
        max_completion_tokens: int = 4096,
    ) -> None:
        if not api_key:
            raise ProviderError("MODEL_API_KEY is required")
        if not model:
            raise ProviderError("MODEL_NAME is required")
        if max_completion_tokens < 1:
            raise ProviderError("MODEL_MAX_COMPLETION_TOKENS must be positive")
        self.api_key = api_key
        self.model = model
        self.endpoint = base_url.rstrip("/") + "/chat/completions"
        self.timeout_seconds = timeout_seconds
        self.max_completion_tokens = max_completion_tokens

    @classmethod
    def from_environment(cls) -> OpenAICompatibleProvider:
        return cls(
            api_key=os.environ.get("MODEL_API_KEY", ""),
            model=os.environ.get("MODEL_NAME", ""),
            base_url=os.environ.get("MODEL_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout_seconds=int(os.environ.get("MODEL_TIMEOUT_SECONDS", "90")),
            max_completion_tokens=int(os.environ.get("MODEL_MAX_COMPLETION_TOKENS", "4096")),
        )

    def complete(self, *, system: str, user: str) -> tuple[str, TokenUsage]:
        body = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "max_completion_tokens": self.max_completion_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "darwin-debugger/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload: dict[str, Any] = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace")
            raise ProviderError(
                f"model API returned HTTP {exc.code}: "
                f"{_sanitize_error_detail(detail, secrets=(self.api_key,))}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"model API request failed: {exc}") from exc
        try:
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message content is not text")
            return content, TokenUsage.from_payload(payload.get("usage"))
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("model API response did not contain message content") from exc
