import json
from datetime import datetime
from typing import Optional, Type

import typer
from rich import print as rprint

from binarycookies import __version__, load
from binarycookies._output_handlers import OUTPUT_HANDLERS, OutputType


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Type) -> str:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


app = typer.Typer()


def version_callback(value: bool):  # noqa: FBT001
    """Callback to print version and exit."""
    if value:
        rprint(f"binarycookies version {__version__}")
        raise typer.Exit


@app.command()
def cli(
    file_path: str = typer.Argument(..., help="Path to binary cookies file"),
    output: OutputType = typer.Option(OutputType.json, "--output", "-o", help="Output format"),
    version: Optional[bool] = typer.Option(  # noqa: ARG001
        None, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit"
    ),
):
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
    app()


if __name__ == "__main__":
    main()
