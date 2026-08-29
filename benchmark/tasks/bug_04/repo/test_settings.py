import pytest

from settings import ConfigError, load_settings


def test_broken_file_raises(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(str(path))


def test_missing_file_uses_default(tmp_path):
    path = tmp_path / "absent.json"
    assert load_settings(str(path), default={"mode": "safe"}) == {"mode": "safe"}
