import json

import pytest

from settings import ConfigError, load_settings


def test_valid_file_is_returned(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"mode": "live", "workers": 4}), encoding="utf-8")
    assert load_settings(str(path)) == {"mode": "live", "workers": 4}


def test_missing_file_defaults_to_empty_dict(tmp_path):
    assert load_settings(str(tmp_path / "absent.json")) == {}


def test_empty_file_is_an_error(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(str(path))


def test_error_message_names_the_path(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ConfigError) as excinfo:
        load_settings(str(path))
    assert str(path) in str(excinfo.value)


def test_directory_is_not_swallowed_as_a_missing_file(tmp_path):
    directory = tmp_path / "settings.json"
    directory.mkdir()
    with pytest.raises(Exception) as excinfo:
        load_settings(str(directory), default={"mode": "safe"})
    assert not isinstance(excinfo.value, AssertionError)


def test_default_is_not_returned_for_broken_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("[1, 2", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(str(path), default={"mode": "safe"})
