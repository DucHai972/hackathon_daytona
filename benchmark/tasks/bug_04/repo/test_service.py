import json

import pytest

from errors import CorruptRecord
from service import load_profile


def test_corrupt_profile_reaches_the_caller(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text('{"plan": "pro"', encoding="utf-8")
    with pytest.raises(CorruptRecord):
        load_profile(str(path))


def test_absent_profile_falls_back_to_the_default(tmp_path):
    assert load_profile(str(tmp_path / "absent.json")) == {"plan": "free"}


def test_valid_profile_is_returned(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"plan": "pro"}), encoding="utf-8")
    assert load_profile(str(path)) == {"plan": "pro"}
