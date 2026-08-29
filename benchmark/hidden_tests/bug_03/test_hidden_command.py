import pytest

from command import CommandError, split_command


def test_double_quoted_path_stays_together():
    line = 'pg_dump --out "/var/My Backups/db.sql"'
    assert split_command(line) == ["pg_dump", "--out", "/var/My Backups/db.sql"]


def test_single_quotes_group_too():
    assert split_command("echo 'hello world'") == ["echo", "hello world"]


def test_quote_may_open_mid_argument():
    assert split_command('pg_dump --out="/var/My Backups"') == [
        "pg_dump",
        "--out=/var/My Backups",
    ]


def test_backslash_escapes_a_space():
    assert split_command("cat a\\ b") == ["cat", "a b"]


def test_backslash_escapes_a_quote():
    assert split_command('echo \\"quoted\\"') == ["echo", '"quoted"']


def test_backslash_is_literal_inside_single_quotes():
    assert split_command("echo 'a\\b'") == ["echo", "a\\b"]


def test_empty_quoted_argument_is_preserved():
    assert split_command("echo '' end") == ["echo", "", "end"]


def test_adjacent_quoted_sections_join():
    assert split_command("""echo 'a b'"c d\"""") == ["echo", "a bc d"]


def test_runs_of_whitespace_collapse():
    assert split_command("  ls   -la\t/tmp  ") == ["ls", "-la", "/tmp"]


def test_empty_line():
    assert split_command("") == []
    assert split_command("   ") == []


def test_unterminated_double_quote_is_rejected():
    with pytest.raises(CommandError):
        split_command('echo "oops')


def test_unterminated_single_quote_is_rejected():
    with pytest.raises(CommandError):
        split_command("echo 'oops")


def test_trailing_backslash_is_rejected():
    with pytest.raises(CommandError):
        split_command("echo a\\")
