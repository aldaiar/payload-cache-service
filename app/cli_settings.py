
from typing import Self

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_cli_args(argv: list[str]) -> list[str]:
    aliases = {
        "-r": "--repeat",
        "-i": "--input",
        "-j": "--json",
        "-o": "--output",
    }

    normalized = []

    for arg in argv:
        option, separator, value = arg.partition("=")
        option = aliases.get(option, option)
        normalized.append(
            f"{option}={value}" if separator else option
        )

    return normalized


class CLISettings(BaseSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
        cli_prog_name="cache-cli",
        cli_kebab_case=True,
        cli_hide_none_type=True,
        validate_default=True,
        extra="forbid",
    )


    def __init__(self, **values):
        args = values.get("_cli_parse_args")

        if isinstance(args, list):
            values["_cli_parse_args"] = normalize_cli_args(args)

        super().__init__(**values)

    host: AnyHttpUrl = Field(
        default="http://localhost:8000",
        description="Base URL of the payload cache service.",
    )

    repeat: int = Field(
        default=1,
        ge=1,
        description="Number of request iterations.",
    )

    input_file: str | None = Field(
        default=None,
        alias="input",
        description="Input file path, or '-' for stdin.",
    )

    json_input: str | None = Field(
        default=None,
        alias="json",
        description="Input JSON passed directly as an argument.",
    )

    output: str = Field(
        default="-",
        description="Output file path, or '-' for stdout.",
    )

    @model_validator(mode="after")
    def validate_input_source(self) -> Self:
        if (self.input_file is None) == (self.json_input is None):
            raise ValueError(
                "Provide exactly one of --input or --json."
            )
        return self