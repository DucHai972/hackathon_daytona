import pytest

from config import parse_config


def test_value_may_contain_equals_signs():
    text = "callback = https://example.com/hook?token=abc"
    assert parse_config(text) == {"callback": "https://example.com/hook?token=abc"}


def test_plain_settings():
    assert parse_config("region = eu-west-1") == {"region": "eu-west-1"}


def test_line_without_separator_is_rejected():
    with pytest.raises(ValueError):
        parse_config("region")
