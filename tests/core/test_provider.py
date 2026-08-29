from __future__ import annotations

import pytest

from darwin_debugger.provider import PatchProposal, ProviderError


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
