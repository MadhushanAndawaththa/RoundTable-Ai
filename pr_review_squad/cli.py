"""
Automated PR Code Review Squad - CLI entry point.

Three agents review a Git diff in sequence:
  1. Security Auditor
  2. Optimization Expert
  3. Tech Lead (synthesizes the final PR comment)
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

from agents import build_squad, configure_gemini, synthesize_input
from github_fetcher import GitHubFetchError, fetch_pr_diff


# Dark IDE aesthetic - "monokai" / cyan accent palette
console = Console(highlight=False)
HERE = Path(__file__).resolve().parent
REVIEWS_DIR = HERE / "reviews"
SAMPLE_PATH = HERE / "samples" / "sample_diff.txt"


def banner() -> None:
    art = Text.from_markup(
        "[bold cyan]"
        "  ____  ____    ____            _                ____                       _ \n"
        " |  _ \\|  _ \\  |  _ \\ _____   _(_) _____      __/ ___|  __ _ _   _  __ _  __| |\n"
        " | |_) | |_) | | |_) / _ \\ \\ / / |/ _ \\ \\ /\\ / /\\___ \\ / _` | | | |/ _` |/ _` |\n"
        " |  __/|  _ <  |  _ <  __/\\ V /| |  __/\\ V  V /  ___) | (_| | |_| | (_| | (_| |\n"
        " |_|   |_| \\_\\ |_| \\_\\___| \\_/ |_|\\___| \\_/\\_/  |____/ \\__, |\\__,_|\\__,_|\\__,_|\n"
        "                                                          |_|                   "
        "[/bold cyan]"
    )
    subtitle = Text(
        "  three agents · one verdict · zero merge regrets",
        style="dim italic cyan",
    )
    console.print(art)
    console.print(subtitle)
    console.print(Rule(style="grey30"))


def load_diff(args: argparse.Namespace) -> tuple[str, str]:
    """Returns (diff_text, source_label)."""
    if args.sample:
        if not SAMPLE_PATH.exists():
            console.print(f"[red]Sample diff not found at {SAMPLE_PATH}[/red]")
            sys.exit(1)
        return SAMPLE_PATH.read_text(), f"sample ({SAMPLE_PATH.name})"

    if args.file:
        path = Path(args.file).expanduser().resolve()
        if not path.exists():
            console.print(f"[red]File not found: {path}[/red]")
            sys.exit(1)
        return path.read_text(), str(path)

    if args.pr_url:
        with console.status(
            f"[cyan]Fetching diff from GitHub PR[/cyan] {args.pr_url}", spinner="dots"
        ):
            try:
                diff = fetch_pr_diff(args.pr_url)
            except GitHubFetchError as exc:
                console.print(f"[red]GitHub error:[/red] {exc}")
                sys.exit(1)
        return diff, args.pr_url

    console.print(
        "[red]No input provided.[/red] Use [bold]--pr-url[/bold], [bold]--file[/bold], or [bold]--sample[/bold]."
    )
    sys.exit(1)


def render_diff_preview(diff: str, max_lines: int = 40) -> None:
    lines = diff.splitlines()
    snippet = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        snippet += f"\n... ({len(lines) - max_lines} more lines)"
    syntax = Syntax(snippet, "diff", theme="monokai", line_numbers=False, word_wrap=False)
    console.print(Panel(syntax, title="[bold]git diff[/bold]", border_style="grey30"))


def agent_panel(title: str, body: str, color: str) -> Panel:
    return Panel(
        Markdown(body) if body else Text("(empty)", style="dim"),
        title=f"[bold {color}]{title}[/bold {color}]",
        border_style=color,
        padding=(1, 2),
    )


def copy_to_clipboard(text: str) -> bool:
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        return False


def save_review(
    final_markdown: str,
    source_label: str,
    security_report: str = "",
    optimization_report: str = "",
) -> Path:
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REVIEWS_DIR / f"review_{ts}.md"
    header = (
        f"<!-- PR Review Squad · {dt.datetime.now().isoformat(timespec='seconds')} -->\n"
        f"<!-- Source: {source_label} -->\n\n"
    )
    raw_block = ""
    if security_report or optimization_report:
        raw_block = (
            "\n\n---\n\n"
            "<details>\n<summary>🔐 Raw Security Auditor report</summary>\n\n"
            f"{security_report or '_(empty)_'}\n\n"
            "</details>\n\n"
            "<details>\n<summary>⚡ Raw Optimization Expert report</summary>\n\n"
            f"{optimization_report or '_(empty)_'}\n\n"
            "</details>\n"
        )
    path.write_text(header + final_markdown + raw_block + "\n")
    return path


def run(args: argparse.Namespace) -> int:
    load_dotenv(HERE / ".env")
    load_dotenv()  # also pick up cwd .env if present

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        console.print(
            Panel(
                Text.from_markup(
                    "[bold red]Missing GEMINI_API_KEY[/bold red]\n\n"
                    "Grab a free key at [link]https://aistudio.google.com/apikey[/link] "
                    "and add it to [bold].env[/bold] next to this script:\n\n"
                    "  [green]GEMINI_API_KEY=your_key_here[/green]"
                ),
                border_style="red",
            )
        )
        return 2

    configure_gemini(api_key)

    banner()

    model_name = args.model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    diff, source_label = load_diff(args)
    console.print(f"[dim]source:[/dim] [bold]{source_label}[/bold]   "
                  f"[dim]model:[/dim] [bold]{model_name}[/bold]\n")
    render_diff_preview(diff)

    security, optimizer, tech_lead = build_squad(model_name=model_name)

    try:
        # --- Agent 1: Security Auditor ---
        with console.status("[bold red]Security Auditor scanning for vulnerabilities…[/bold red]", spinner="dots"):
            sec = security.run(diff)
        console.print(agent_panel("🔐 Security Auditor", sec.output, "red"))

        # --- Agent 2: Optimization Expert ---
        with console.status("[bold yellow]Optimization Expert profiling the change…[/bold yellow]", spinner="dots"):
            opt = optimizer.run(diff)
        console.print(agent_panel("⚡ Optimization Expert", opt.output, "yellow"))

        # --- Agent 3: Tech Lead ---
        with console.status("[bold green]Tech Lead synthesizing the PR comment…[/bold green]", spinner="dots"):
            lead = tech_lead.run(synthesize_input(sec.output, opt.output))
    except Exception as exc:  # noqa: BLE001 - surface SDK errors as friendly text
        msg = str(exc)
        hint = ""
        if "404" in msg or "not found" in msg.lower():
            hint = (
                f"\n\n[dim]The model [bold]{model_name}[/bold] was not found. "
                "Try [bold]--model gemini-2.5-flash[/bold] or "
                "[bold]--model gemini-2.0-flash[/bold].[/dim]"
            )
        console.print(Panel(Text.from_markup(f"[red]Gemini call failed:[/red] {msg}{hint}"), border_style="red"))
        return 3

    console.print(Rule("[bold cyan]Final PR Comment[/bold cyan]", style="cyan"))
    console.print(
        Panel(
            Markdown(lead.output),
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # --- Persist + clipboard ---
    footer_lines = []
    if args.no_save:
        footer_lines.append(Text.from_markup("📝 [dim]--no-save: skipped writing markdown file[/dim]"))
    else:
        saved_path = save_review(lead.output, source_label, sec.output, opt.output)
        footer_lines.append(Text.from_markup(f"📝 Saved to [bold]{saved_path}[/bold]"))

    if args.no_clipboard:
        footer_lines.append(Text.from_markup("📋 [dim]--no-clipboard: skipped clipboard copy[/dim]"))
    else:
        clipboard_ok = copy_to_clipboard(lead.output)
        footer_lines.append(
            Text.from_markup(
                "📋 Copied to clipboard"
                if clipboard_ok
                else "📋 [dim]Clipboard unavailable on this system (install xclip/xsel or run in a desktop session)[/dim]"
            )
        )

    console.print(Panel(Group(*footer_lines), border_style="grey30"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pr-review-squad",
        description="Run a 3-agent code review squad over a git diff (GitHub PR, file, or sample).",
    )
    src = p.add_mutually_exclusive_group()
    src.add_argument("--pr-url", help="GitHub PR URL, e.g. https://github.com/psf/requests/pull/6800")
    src.add_argument("--file", help="Path to a .diff or .txt file containing a unified diff")
    src.add_argument("--sample", action="store_true", help="Use the bundled vulnerable sample diff")
    p.add_argument("--model", help="Gemini model name (overrides GEMINI_MODEL env). e.g. gemini-2.5-flash")
    p.add_argument("--no-save", action="store_true", help="Don't write the synthesised comment to reviews/")
    p.add_argument("--no-clipboard", action="store_true", help="Don't copy the synthesised comment to the clipboard")
    return p


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    sys.exit(main())
