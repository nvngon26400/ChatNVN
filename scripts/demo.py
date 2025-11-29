from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from mock_project.chatbot import CustomerSupportChatbot
from mock_project.config import get_settings

console = Console()
app = typer.Typer(add_completion=False)


@app.command()
def run(
    docs_path: Path = typer.Option(Path("data/docs"), "--docs-path", help="Folder containing PDF/DOCX files")
) -> None:
    """Start an interactive CLI session with the chatbot."""

    settings = get_settings()
    settings.docs_path = docs_path.resolve()
    bot = CustomerSupportChatbot(settings=settings)
    console.print(Panel.fit("[bold cyan]Customer Support Chatbot[/bold cyan]\nNhập 'quit' để thoát."))

    while True:
        try:
            question = console.input("[bold green]Bạn:[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold yellow]Kết thúc phiên làm việc.[/bold yellow]")
            break

        if question.strip().lower() in {"quit", "exit"}:
            console.print("[bold yellow]Tạm biệt![/bold yellow]")
            break

        try:
            answer = bot.ask(question)
            console.print(Panel(answer, title="Chatbot", style="magenta"))
        except Exception as exc:  # noqa: BLE001
            console.print(f"[bold red]Lỗi:[/bold red] {exc}")


if __name__ == "__main__":
    try:
        app()
    except Exception as exc:  # noqa: BLE001
        Console().print(f"[bold red]Demo failed:[/bold red] {exc}")
        sys.exit(1)


