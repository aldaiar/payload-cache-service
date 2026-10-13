
import json

import pytest
from pydantic import ValidationError

from app.cli_settings import CLISettings
from app.cli import read_input, write_output


def test_short_arguments_are_supported():
    settings = CLISettings(
        _cli_parse_args=[
            "-r", "3",
            "-j", '{"list_1":["a"],"list_2":["b"]}',
        ]
    )

    assert settings.repeat == 3
    assert settings.json is not None


def test_repeat_must_be_positive():
    with pytest.raises(ValidationError):
        CLISettings(
            _cli_parse_args=[
                "--repeat", "0",
                "--json", '{"list_1":[],"list_2":[]}',
            ]
        )


def test_input_and_json_cannot_be_used_together():
    with pytest.raises(ValidationError):
        CLISettings(
            _cli_parse_args=[
                "--input", "input.json",
                "--json", '{"list_1":[],"list_2":[]}',
            ]
        )


def test_read_json_input():
    settings = CLISettings(
        _cli_parse_args=[
            "--json", '{"list_1":["hello"],"list_2":["world"]}',
        ]
    )

    payload = read_input(settings)

    assert payload.list_1 == ["hello"]
    assert payload.list_2 == ["world"]


def test_write_output_to_file(tmp_path):
    destination = tmp_path / "output.json"
    expected = [{"id": "test-id"}]

    write_output(expected, str(destination))

    assert json.loads(destination.read_text(encoding="utf-8")) == expected