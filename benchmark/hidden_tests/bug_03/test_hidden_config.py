import pytest

from config import parse_config


def test_many_equals_signs_in_value():
    result = parse_config("expr = a=b=c=d")
    assert result == {"expr": "a=b=c=d"}


def test_empty_config():
    assert parse_config("") == {}


def test_comments_and_blank_lines_ignored():
    text = "\n# a comment\n\nregion = eu-west-1\n   # indented comment\n"
    assert parse_config(text) == {"region": "eu-west-1"}


def test_hash_inside_value_is_not_a_comment():
    assert parse_config("colour = #ff0000") == {"colour": "#ff0000"}


def test_empty_value_allowed():
    assert parse_config("token =") == {"token": ""}


def test_whitespace_is_stripped():
    assert parse_config("   region   =   eu-west-1   ") == {"region": "eu-west-1"}


def test_later_line_wins():
    assert parse_config("a = 1\na = 2") == {"a": "2"}


def test_missing_separator_reports_line_number():
    with pytest.raises(ValueError) as excinfo:
        parse_config("a = 1\nbroken")
    assert "line 2" in str(excinfo.value)
