from sys import stdout
from unittest.mock import patch

from binarycookies import dump
from binarycookies.__main__ import cli


def test_cli_json_output(tmp_path, capsys):
    file_path = tmp_path / "Cookies.binarycookies"
    data = {
        "name": "name",
        "value": "value",
        "url": "example.com",
        "path": "/",
        "create_datetime": 2032,
        "expiry_datetime": 2032,
        "flag": "Secure",
    }
    with open(file_path, "wb") as f:
        dump(data, f)

    with patch("binarycookies.__main__.json.dump") as mock_json_dump:
        mock_json_dump.return_value = None  # Prevent actual output
        cli(str(file_path), output="json")

        # Assert json.dump was called with the correct arguments
        mock_json_dump.assert_called_once()
        args, kwargs = mock_json_dump.call_args
        assert isinstance(kwargs["fp"], type(stdout))  # Ensure it writes to stdout


def test_cli_ascii_output(tmp_path, capsys):
    file_path = tmp_path / "Cookies.binarycookies"
    data = {
        "name": "name",
        "value": "value",
        "url": "example.com",
        "path": "/",
        "create_datetime": 2032,
        "expiry_datetime": 2032,
        "flag": "Secure",
    }
    with open(file_path, "wb") as f:
        # Call the dump method
        dump(data, f)
    cli(str(file_path), output="ascii")
    output = capsys.readouterr().out

    assert "Name:" in output
    assert "Value:" in output
    assert "URL:" in output
    assert "Path:" in output
    assert "Created:" in output
    assert "Expires:" in output
    assert "Flag:" in output
    assert "-" * 40 in output
    assert "Flag.SECURE" not in output
    assert "Secure" in output


def test_cli_netscape_output(tmp_path, capsys):
    file_path = tmp_path / "Cookies.binarycookies"
    data = {
        "name": "name",
        "value": "value",
        "url": ".example.com",
        "path": "/",
        "create_datetime": 2032,
        "expiry_datetime": 2032,
        "flag": "Secure",
    }
    with open(file_path, "wb") as f:
        # Call the dump method
        dump(data, f)
    cli(str(file_path), output="netscape")
    output = capsys.readouterr().out

    assert "# Netscape HTTP Cookie File" in output
    assert "example.com\tTRUE\t/\tTRUE\t2032\tname\tvalue" in output
