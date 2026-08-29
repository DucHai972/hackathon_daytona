import pytest

from command import CommandError, split_command


def test_double_quoted_path_stays_together():
    line = 'pg_dump --out "/var/My Backups/db.sql"'
    assert split_command(line) == ["pg_dump", "--out", "/var/My Backups/db.sql"]


def test_plain_arguments():
    assert split_command("ls -la /tmp") == ["ls", "-la", "/tmp"]


def test_unterminated_quote_is_rejected():
    with pytest.raises(CommandError):
        split_command('echo "oops')
