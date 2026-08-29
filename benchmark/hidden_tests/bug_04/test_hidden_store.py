import json

import pytest

import store
from errors import CorruptRecord, StoreError
from service import load_profile


def test_store_raises_on_a_corrupt_record(tmp_path):
    path = tmp_path / "record.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(CorruptRecord):
        store.read(str(path))


def test_store_returns_none_for_an_absent_record(tmp_path):
    assert store.read(str(tmp_path / "absent.json")) is None


def test_store_returns_the_parsed_record(tmp_path):
    path = tmp_path / "record.json"
    path.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert store.read(str(path)) == {"a": 1}


def test_an_empty_file_is_corrupt_not_absent(tmp_path):
    path = tmp_path / "record.json"
    path.write_text("", encoding="utf-8")
    with pytest.raises(CorruptRecord):
        store.read(str(path))


def test_corrupt_record_names_the_path(tmp_path):
    path = tmp_path / "record.json"
    path.write_text("[1,", encoding="utf-8")
    with pytest.raises(CorruptRecord) as excinfo:
        store.read(str(path))
    assert str(path) in str(excinfo.value)


def test_corrupt_record_is_a_store_error(tmp_path):
    path = tmp_path / "record.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(StoreError):
        store.read(str(path))


def test_service_still_reports_corrupt_profiles(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text('{"plan": "pro"', encoding="utf-8")
    with pytest.raises(CorruptRecord):
        load_profile(str(path))


def test_service_still_defaults_for_absent_profiles(tmp_path):
    assert load_profile(str(tmp_path / "absent.json")) == {"plan": "free"}
    assert load_profile(str(tmp_path / "absent.json"), default={"plan": "trial"}) == {
        "plan": "trial"
    }


def test_service_returns_a_valid_profile(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"plan": "enterprise"}), encoding="utf-8")
    assert load_profile(str(path)) == {"plan": "enterprise"}


def test_default_is_not_shared_between_calls(tmp_path):
    first = load_profile(str(tmp_path / "absent.json"))
    first["plan"] = "mutated"
    assert load_profile(str(tmp_path / "absent.json")) == {"plan": "free"}
