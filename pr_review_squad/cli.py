"""
RoundTable AI — CLI entry point.

Three agents review a Git diff in sequence:
  1. Security Auditor
  2. Optimization Expert
  3. Tech Lead (synthesizes the final PR comment)

Each agent's LLM provider + model is chosen in `squad.toml`. All providers are
called via the OpenAI-compatible Chat Completions API.
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
from rich.table import Table
from rich.text import Text

from agents import build_agent, synthesize_input
from github_fetcher import GitHubFetchError, fetch_pr_diff
from providers import (
    MissingKeyError,
    SquadConfigError,
    build_client,
    find_default_config,
    load_squad_config,
    validate_keys_for_config,
)


console = Console(highlight=False)
HERE = Path(__file__).resolve().parent
REVIEWS_DIR = HERE / "reviews"
SAMPLE_PATH = HERE / "samples" / "sample_diff.txt"


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def banner() -> None:
    art = Text.from_markup(
        "[bold cyan]"
        "  ____                       _ _____     _     _        _    ___ \n"
        " |  _ \\ ___  _   _ _ __   __| |_   _|_ _| |__ | | ___  / \\  |_ _|\n"
        " | |_) / _ \\| | | | '_ \\ / _` | | |/ _` | '_ \\| |/ _ \\/ _ \\  | | \n"
        " |  _ < (_) | |_| | | | | (_| | | | (_| | |_) | |  __/ ___ \\ | | \n"
        " |_| \\_\\___/ \\__,_|_| |_|\\__,_| |_|\\__,_|_.__/|_|\\___/_/   \\_\\___|\n"
        "[/bold cyan]"
    )
    subtitle = Text(
        "  three seats · three agents · one PR comment",
        style="dim italic cyan",
    )
    console.print(art)
    console.print(subtitle)
    console.print(Rule(style="grey30"))


def round_table_panel(config: dict[str, dict[str, str]]) -> Panel:
    """Show which provider/model is sitting in each agent seat."""
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left", style="bold")
    table.add_column(justify="left", style="cyan")
    table.add_column(justify="left", style="dim")

    rows = [
        ("🔐 Security Auditor", "security_auditor"),
        ("⚡ Optimization Expert", "optimization_expert"),
        ("🧑‍💼 Tech Lead", "tech_lead"),
    ]
    for label, key in rows:
        provider = config[key]["provider"]
        model = config[key]["model"]
        table.add_row(label, provider, model)

    return Panel(table, title="[bold cyan]🪑 The Round Table[/bold cyan]", border_style="cyan")


def render_diff_preview(diff: str, max_lines: int = 40) -> None:
    lines = diff.splitlines()
    snippet = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        snippet += f"\n... ({len(lines) - max_lines} more lines)"
    syntax = Syntax(snippet, "diff", theme="monokai", line_numbers=False, word_wrap=False)
    console.print(Panel(syntax, title="[bold]git diff[/bold]", border_style="grey30"))


def agent_panel(title: str, body: str, color: str, footnote: str = "") -> Panel:
    inner: list = [Markdown(body) if body else Text("(empty)", style="dim")]
    if footnote:
        inner.append(Text(footnote, style="dim italic"))
    return Panel(
        Group(*inner),
        title=f"[bold {color}]{title}[/bold {color}]",
        border_style=color,
        padding=(1, 2),
    )


# ---------------------------------------------------------------------------
# Diff loading
# ---------------------------------------------------------------------------


def load_diff(args: argparse.Namespace) -> tuple[str, str]:
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


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


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
    security_report: str,
    optimization_report: str,
    squad_summary: str,
) -> Path:
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REVIEWS_DIR / f"review_{ts}.md"
    header = (
        f"<!-- RoundTable AI · {dt.datetime.now().isoformat(timespec='seconds')} -->\n"
        f"<!-- Source: {source_label} -->\n"
        f"<!-- Squad:  {squad_summary} -->\n\n"
    )
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


def render_missing_keys(missing) -> Panel:
    lines: list[Text] = [
        Text.from_markup(
            "[bold red]Missing API key(s) for your squad.toml[/bold red]\n"
        )
    ]
    for spec in missing:
        lines.append(
            Text.from_markup(
                f"  • [bold]{spec.api_key_env}[/bold]  →  "
                f"get one at [link]{spec.signup_url}[/link]  "
                f"[dim]({spec.notes})[/dim]"
            )
        )
    lines.append(Text.from_markup("\nAdd the missing keys to [bold].env[/bold] and re-run."))
    return Panel(Group(*lines), border_style="red")


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    load_dotenv(HERE / ".env")
    load_dotenv()  # also pick up cwd .env if present

    # --- Load squad config ---
    config_path = Path(args.config).resolve() if args.config else find_default_config(HERE)
    try:
        config = load_squad_config(config_path)
    except SquadConfigError as exc:
        console.print(Panel(Text(str(exc), style="red"), border_style="red"))
        return 4

    # --- Apply CLI overrides ---
    if args.model:
        for agent_key in config:
            config[agent_key]["model"] = args.model
    if args.provider:
        for agent_key in config:
            config[agent_key]["provider"] = args.provider

    # --- Validate keys ---
    missing = validate_keys_for_config(config)
    if missing:
        banner()
        console.print(round_table_panel(config))
        console.print(render_missing_keys(missing))
        return 2

    banner()
    console.print(round_table_panel(config))

    # --- Load diff ---
    diff, source_label = load_diff(args)
    console.print(f"\n[dim]source:[/dim] [bold]{source_label}[/bold]")
    if config_path:
        console.print(f"[dim]config:[/dim] [bold]{config_path.name}[/bold]\n")
    render_diff_preview(diff)

    # --- Build per-agent clients & agents ---
    # Cache one client per unique provider to avoid re-creating identical clients.
    client_cache: dict[str, object] = {}
    try:
        for cfg in config.values():
            p = cfg["provider"]
            if p not in client_cache:
                client_cache[p] = build_client(p)
    except MissingKeyError as exc:
        console.print(Panel(Text(str(exc), style="red"), border_style="red"))
        return 2

    security = build_agent(
        "security_auditor",
        client_cache[config["security_auditor"]["provider"]],  # type: ignore[arg-type]
        config["security_auditor"]["model"],
        config["security_auditor"]["provider"],
    )
    optimizer = build_agent(
        "optimization_expert",
        client_cache[config["optimization_expert"]["provider"]],  # type: ignore[arg-type]
        config["optimization_expert"]["model"],
        config["optimization_expert"]["provider"],
    )
    tech_lead = build_agent(
        "tech_lead",
        client_cache[config["tech_lead"]["provider"]],  # type: ignore[arg-type]
        config["tech_lead"]["model"],
        config["tech_lead"]["provider"],
    )

    # --- Run the agents ---
    try:
        with console.status(
            f"[bold red]Security Auditor scanning… ({security.provider}/{security.model})[/bold red]",
            spinner="dots",
        ):
            sec = security.run(diff)
        console.print(agent_panel(
            "🔐 Security Auditor", sec.output, "red",
            footnote=f"via {sec.provider} · {sec.model}",
        ))

        with console.status(
            f"[bold yellow]Optimization Expert profiling… ({optimizer.provider}/{optimizer.model})[/bold yellow]",
            spinner="dots",
        ):
            opt = optimizer.run(diff)
        console.print(agent_panel(
            "⚡ Optimization Expert", opt.output, "yellow",
            footnote=f"via {opt.provider} · {opt.model}",
        ))

        with console.status(
            f"[bold green]Tech Lead synthesizing… ({tech_lead.provider}/{tech_lead.model})[/bold green]",
            spinner="dots",
        ):
            lead = tech_lead.run(synthesize_input(sec.output, opt.output))
    except Exception as exc:  # noqa: BLE001 - surface SDK errors as friendly text
        msg = str(exc)
        hint = ""
        if "404" in msg or "not found" in msg.lower() or "does not exist" in msg.lower():
            hint = "\n\n[dim]Tip: the model name might be wrong for that provider. Check the provider's docs.[/dim]"
        elif "401" in msg or "unauthorized" in msg.lower():
            hint = "\n\n[dim]Tip: your API key was rejected. Re-check the value in .env.[/dim]"
        console.print(Panel(Text.from_markup(f"[red]LLM call failed:[/red] {msg}{hint}"), border_style="red"))
        return 3

    console.print(Rule("[bold cyan]Final PR Comment[/bold cyan]", style="cyan"))
    console.print(
        Panel(
            Markdown(lead.output),
            border_style="cyan",
            padding=(1, 2),
            subtitle=f"[dim]synthesised by {lead.provider} · {lead.model}[/dim]",
            subtitle_align="right",
        )
    )

    # --- Persist + clipboard ---
    squad_summary = ", ".join(
        f"{key}={cfg['provider']}/{cfg['model']}" for key, cfg in config.items()
    )
    footer_lines = []
    if args.no_save:
        footer_lines.append(Text.from_markup("📝 [dim]--no-save: skipped writing markdown file[/dim]"))
    else:
        saved_path = save_review(lead.output, source_label, sec.output, opt.output, squad_summary)
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
        prog="roundtable-ai",
        description="Run a 3-agent multi-LLM code review squad over a git diff (GitHub PR, file, or sample).",
    )
    src = p.add_mutually_exclusive_group()
    src.add_argument("--pr-url", help="GitHub PR URL, e.g. https://github.com/psf/requests/pull/6800")
    src.add_argument("--file", help="Path to a .diff or .txt file containing a unified diff")
    src.add_argument("--sample", action="store_true", help="Use the bundled vulnerable sample diff")
    p.add_argument("--config", help="Path to a squad.toml (defaults to ./squad.toml)")
    p.add_argument("--provider", help="Force all three agents to use this provider (overrides squad.toml)")
    p.add_argument("--model", help="Force all three agents to use this model (overrides squad.toml)")
    p.add_argument("--no-save", action="store_true", help="Don't write the synthesised comment to reviews/")
    p.add_argument("--no-clipboard", action="store_true", help="Don't copy the synthesised comment to the clipboard")
    return p


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    sys.exit(main())
