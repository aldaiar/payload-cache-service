
import json
import sys
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.cli_settings import CLISettings
from app.schemas.payload import PayloadCreate


def read_input(settings: CLISettings) -> PayloadCreate:
    if settings.json_input is not None:
        raw_data = settings.json_input
    elif settings.input_file == "-":
        raw_data = sys.stdin.read()
    else:
        raw_data = Path(settings.input_file).read_text(encoding="utf-8")

    return PayloadCreate.model_validate_json(raw_data)



def write_output(output: list[dict], destination: str) -> None:
    serialized = json.dumps(
        output,
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    if destination == "-":
        sys.stdout.write(serialized)
        sys.stdout.flush()
    else:
        Path(destination).write_text(
            serialized,
            encoding="utf-8",
        )


def run(settings: CLISettings) -> int:
    try:
        payload = read_input(settings)

        base_url = str(settings.host).rstrip("/")
        results = []

        with httpx.Client(timeout=30.0) as client:
            for _ in range(settings.repeat):
                # Create or reuse the payload.
                response = client.post(
                    f"{base_url}/payload",
                    json=payload.model_dump(),
                )
                response.raise_for_status()

                payload_id = response.json()["id"]

                # Read the processed result.
                read_response = client.get(
                    f"{base_url}/payload/{payload_id}"
                )
                read_response.raise_for_status()

                results.append({
                    "id": payload_id,
                    "created": response.json()["created"],
                    "output": read_response.json()["output"],
                })

        write_output(results, settings.output)
        return 0

    except (OSError, ValidationError, ValueError, KeyError) as exc:
        print(f"Input/output error: {exc}", file=sys.stderr)
        return 2

    except httpx.HTTPError as exc:
        print(f"HTTP request failed: {exc}", file=sys.stderr)
        return 1




def normalize_cli_args(argv: list[str]) -> list[str]:
    """Expand supported short options before Pydantic parses arguments."""
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

        if separator:
            normalized.append(f"{option}={value}")
        else:
            normalized.append(option)

    return normalized



def main() -> int:
    try:
        settings = CLISettings(
            _cli_parse_args=normalize_cli_args(sys.argv[1:])
        )
        return run(settings)
    except (ValidationError, ValueError) as exc:
        print(f"CLI error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())