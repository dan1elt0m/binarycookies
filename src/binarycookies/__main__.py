import json
from datetime import datetime
from typing import Type

import typer
from rich import print as rprint

from binarycookies import load
from binarycookies._output_handlers import OUTPUT_HANDLERS, OutputType


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Type) -> str:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def cli(file_path: str, output: OutputType = OutputType.json):
    """CLI entrypoint for reading Binary Cookies"""
    with open(file_path, "rb") as f:
        cookies = load(f)

    handler = OUTPUT_HANDLERS.get(output)
    if not handler:
        rprint(f"[red]Error:[/red] Unsupported output type: {output}")
        raise typer.Exit(code=1)

    handler(cookies)


def main():
    """CLI entrypoint for reading Binary Cookies"""
    typer.run(cli)


if __name__ == "__main__":
    main()
