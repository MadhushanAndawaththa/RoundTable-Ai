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
import subprocess
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from agents import AgentResult, LLMAgent, build_agent, synthesize_input
from github_fetcher import GitHubFetchError, fetch_pr_diff
from providers import (
    MissingKeyError,
    ModelValidationIssue,
    SquadConfigError,
    build_client,
    find_default_config,
    load_squad_config,
    resolve_config_models,
    validate_keys_for_config,
    validate_model_selection,
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


def run_agent(
    agent: LLMAgent,
    user_input: str,
    title: str,
    color: str,
    *,
    stream: bool,
    spinner_label: str,
) -> AgentResult:
    """Run one agent, either streaming tokens live or with a spinner."""
    if not stream:
        with console.status(f"[bold {color}]{spinner_label}[/bold {color}]", spinner="dots"):
            result = agent.run(user_input)
        console.print(agent_panel(title, result.output, color, footnote=f"via {result.provider} · {result.model}"))
        return result

    # Streaming: stream raw tokens into a transient Live panel, then re-print
    # the final response as fully-rendered Markdown.
    streamed = Text()
    live_panel = Panel(
        streamed,
        title=f"[bold {color}]{title}[/bold {color}] [dim](streaming…)[/dim]",
        border_style=color,
        padding=(1, 2),
    )
    with Live(live_panel, console=console, refresh_per_second=20, transient=True):
        for delta in agent.stream(user_input):
            streamed.append(delta)
    final_text = str(streamed)
    result = AgentResult(agent.name, final_text, agent.provider, agent.model)
    console.print(agent_panel(title, result.output, color, footnote=f"via {result.provider} · {result.model}"))
    return result


SECURITY_PASS_TOKEN = "SECURITY CHECK: PASS"
OPTIMIZATION_PASS_TOKEN = "OPTIMIZATION CHECK: PASS"


def evaluate_fail_on(
    fail_on: str | None,
    security_output: str,
    optimization_output: str,
) -> tuple[bool, bool, bool]:
    """Returns (security_passed, optimization_passed, should_fail_exit)."""
    sec_passed = SECURITY_PASS_TOKEN in security_output
    opt_passed = OPTIMIZATION_PASS_TOKEN in optimization_output
    if fail_on == "security":
        should_fail = not sec_passed
    elif fail_on == "optimization":
        should_fail = not opt_passed
    elif fail_on == "any":
        should_fail = not (sec_passed and opt_passed)
    else:
        should_fail = False
    return sec_passed, opt_passed, should_fail


# ---------------------------------------------------------------------------
# Diff loading
# ---------------------------------------------------------------------------


def uses_local_git_diff(args: argparse.Namespace) -> bool:
    return bool(args.git_diff or args.cached or args.against)


def find_git_root(start: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or "Not inside a git repository."
        console.print(Panel(Text(msg, style="red"), border_style="red"))
        sys.exit(1)
    return Path(result.stdout.strip())


def run_git_command(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "git command failed"
        console.print(Panel(Text(msg, style="red"), border_style="red"))
        sys.exit(1)
    return result.stdout


def load_local_git_diff(args: argparse.Namespace) -> tuple[str, str]:
    git_root = find_git_root(Path.cwd())

    if args.against:
        merge_base = run_git_command(["git", "merge-base", args.against, "HEAD"], git_root).strip()
        diff = run_git_command(["git", "diff", merge_base], git_root)
        source_label = f"git diff against {args.against}"
    else:
        diff_args = ["git", "diff"]
        if args.cached:
            diff_args.append("--cached")
        diff = run_git_command(diff_args, git_root)
        source_label = "git diff --cached" if args.cached else "git diff"

    if not diff.strip():
        message = f"No diff found for {source_label}."
        console.print(Panel(Text(message, style="yellow"), border_style="yellow"))
        sys.exit(1)
    return diff, source_label


def load_diff(args: argparse.Namespace) -> tuple[str, str]:
    if args.sample:
        if not SAMPLE_PATH.exists():
            console.print(f"[red]Sample diff not found at {SAMPLE_PATH}[/red]")
            sys.exit(1)
        return SAMPLE_PATH.read_text(encoding="utf-8"), f"sample ({SAMPLE_PATH.name})"

    if args.file:
        path = Path(args.file).expanduser().resolve()
        if not path.exists():
            console.print(f"[red]File not found: {path}[/red]")
            sys.exit(1)
        return path.read_text(encoding="utf-8"), str(path)

    if uses_local_git_diff(args):
        return load_local_git_diff(args)

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


def build_markdown_body(
    final_markdown: str,
    source_label: str,
    security_report: str,
    optimization_report: str,
    squad_summary: str,
) -> str:
    """Format the final PR-comment markdown (used by both --save and --output)."""
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
    return header + final_markdown + raw_block + "\n"


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
    path.write_text(
        build_markdown_body(
            final_markdown,
            source_label,
            security_report,
            optimization_report,
            squad_summary,
        ),
        encoding="utf-8",
    )
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


def render_model_issues(issues: list[ModelValidationIssue], *, title: str) -> Panel:
    lines: list[Text] = []
    for issue in issues:
        marker = "!" if issue.level == "warning" else "x"
        style = "yellow" if issue.level == "warning" else "red"
        lines.append(
            Text.from_markup(
                f"[{style}]{marker}[/{style}] [bold]{issue.agent}[/bold] "
                f"({issue.provider}/{issue.model}) — {issue.message}"
            )
        )
    border_style = "yellow" if all(issue.level == "warning" for issue in issues) else "red"
    return Panel(Group(*lines), title=title, border_style=border_style)


def render_check_panel(
    config_path: Optional[Path],
    config: dict[str, dict[str, str]],
    missing_keys,
    model_issues: list[ModelValidationIssue],
) -> Panel:
    env_path = HERE / ".env"
    lines: list[Text] = [
        Text.from_markup(
            f"[bold]Config:[/bold] {config_path.name if config_path else 'built-in default'}"
        ),
        Text.from_markup(
            f"[bold].env:[/bold] {'found' if env_path.exists() else 'missing'}"
        ),
        Text(""),
        Text.from_markup("[bold]Resolved squad:[/bold]"),
    ]

    for agent, cfg in config.items():
        lines.append(
            Text.from_markup(
                f"  • [bold]{agent}[/bold] → {cfg['provider']} / {cfg['model']}"
            )
        )

    lines.append(Text(""))
    if missing_keys:
        lines.append(Text.from_markup("[bold red]Missing required provider keys:[/bold red]"))
        for spec in missing_keys:
            lines.append(
                Text.from_markup(
                    f"  • [bold]{spec.api_key_env}[/bold] — get one at [link]{spec.signup_url}[/link]"
                )
            )
    else:
        lines.append(Text.from_markup("[green]All required provider keys are present.[/green]"))

    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if github_token:
        lines.append(
            Text.from_markup(
                "[green]GITHUB_TOKEN is present.[/green] Useful for private PRs and higher GitHub API limits."
            )
        )
    else:
        lines.append(
            Text.from_markup(
                "[yellow]GITHUB_TOKEN is missing.[/yellow] Optional for public PRs; recommended for private PRs and rate limits."
            )
        )

    if model_issues:
        lines.append(Text(""))
        lines.append(Text.from_markup("[bold]Model validation:[/bold]"))
        for issue in model_issues:
            color = "yellow" if issue.level == "warning" else "red"
            lines.append(Text.from_markup(f"  [{color}]•[/{color}] {issue.message}"))
    else:
        lines.append(Text.from_markup("[green]All configured models match the built-in provider catalog.[/green]"))

    return Panel(Group(*lines), title="Configuration Check", border_style="cyan")


def run_check(
    config_path: Optional[Path],
    config: dict[str, dict[str, str]],
) -> int:
    missing = validate_keys_for_config(config)
    model_issues = validate_model_selection(config)
    banner()
    console.print(round_table_panel(config))
    console.print(render_check_panel(config_path, config, missing, model_issues))

    model_errors = [issue for issue in model_issues if issue.level == "error"]
    if missing or model_errors:
        return 2
    return 0


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.cached and args.against:
        parser.error("--cached and --against cannot be combined.")

    if (args.cached or args.against) and (args.sample or args.file or args.pr_url):
        parser.error("--cached and --against only apply to local git diff mode.")

    if args.check and (args.sample or args.file or args.pr_url or args.git_diff or args.cached or args.against):
        parser.error("--check validates configuration only; do not combine it with a diff source.")


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

    config = resolve_config_models(config)

    model_issues = validate_model_selection(config)
    model_errors = [issue for issue in model_issues if issue.level == "error"]
    if model_errors:
        banner()
        console.print(round_table_panel(config))
        console.print(render_model_issues(model_errors, title="Model Validation Errors"))
        return 4

    if args.check:
        return run_check(config_path, config)

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
    stream_mode = (not args.no_stream) and console.is_terminal
    try:
        sec = run_agent(
            security,
            diff,
            "🔐 Security Auditor",
            "red",
            stream=stream_mode,
            spinner_label=f"Security Auditor scanning… ({security.provider}/{security.model})",
        )

        opt = run_agent(
            optimizer,
            diff,
            "⚡ Optimization Expert",
            "yellow",
            stream=stream_mode,
            spinner_label=f"Optimization Expert profiling… ({optimizer.provider}/{optimizer.model})",
        )

        lead = run_agent(
            tech_lead,
            synthesize_input(sec.output, opt.output),
            "🧑‍💼 Tech Lead",
            "green",
            stream=stream_mode,
            spinner_label=f"Tech Lead synthesizing… ({tech_lead.provider}/{tech_lead.model})",
        )
    except Exception as exc:  # noqa: BLE001 - surface SDK errors as friendly text
        msg = str(exc)
        hint = ""
        if "404" in msg or "not found" in msg.lower() or "does not exist" in msg.lower():
            hint = "\n\n[dim]Tip: the model name might be wrong for that provider. Check the provider's docs.[/dim]"
        elif "401" in msg or "unauthorized" in msg.lower():
            hint = "\n\n[dim]Tip: your API key was rejected. Re-check the value in .env.[/dim]"
        elif "413" in msg or "request too large" in msg.lower() or "tokens per minute" in msg.lower():
            hint = (
                "\n\n[dim]Tip: this diff is too large for the current model. Try a larger model "
                "such as `--model default-best`, review a smaller slice with `--cached`, or use a narrower base ref with `--against`.[/dim]"
            )
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

    if args.output:
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        body = build_markdown_body(lead.output, source_label, sec.output, opt.output, squad_summary)
        out_path.write_text(body, encoding="utf-8")
        footer_lines.append(Text.from_markup(f"📤 Wrote PR comment to [bold]{out_path}[/bold]"))

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

    # --- Final verdict / --fail-on gate ---
    sec_passed, opt_passed, should_fail = evaluate_fail_on(args.fail_on, sec.output, opt.output)
    verdict_lines = [
        Text.from_markup(
            f"{'[green]✓[/green]' if sec_passed else '[red]✗[/red]'} Security check "
            f"{'[green]passed[/green]' if sec_passed else '[red]found issues[/red]'}"
        ),
        Text.from_markup(
            f"{'[green]✓[/green]' if opt_passed else '[yellow]✗[/yellow]'} Optimization check "
            f"{'[green]passed[/green]' if opt_passed else '[yellow]found suggestions[/yellow]'}"
        ),
    ]
    if args.fail_on:
        verdict_lines.append(
            Text.from_markup(
                f"\n[dim]--fail-on={args.fail_on}:[/dim] "
                + ("[red]exiting non-zero[/red]" if should_fail else "[green]gate satisfied[/green]")
            )
        )
    console.print(Panel(Group(*verdict_lines), title="Verdict", border_style="cyan" if not should_fail else "red"))

    return 1 if should_fail else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="roundtable-ai",
        description="Run a 3-agent multi-LLM code review squad over a git diff (GitHub PR, file, or sample).",
    )
    src = p.add_mutually_exclusive_group()
    src.add_argument("--pr-url", help="GitHub PR URL, e.g. https://github.com/psf/requests/pull/6800")
    src.add_argument("--file", help="Path to a .diff or .txt file containing a unified diff")
    src.add_argument("--sample", action="store_true", help="Use the bundled vulnerable sample diff")
    src.add_argument(
        "--git-diff",
        "--working-tree",
        dest="git_diff",
        action="store_true",
        help="Review local working-tree changes via git diff",
    )
    p.add_argument("--config", help="Path to a squad.toml (defaults to ./squad.toml)")
    p.add_argument("--provider", help="Force all three agents to use this provider (overrides squad.toml)")
    p.add_argument("--model", help="Force all three agents to use this model (overrides squad.toml); supports default-fast and default-best")
    p.add_argument("--cached", action="store_true", help="Review staged changes via git diff --cached")
    p.add_argument("--against", metavar="REF", help="Review your current branch and working tree against a base ref, e.g. --against main")
    p.add_argument("--check", "--doctor", dest="check", action="store_true", help="Validate .env, squad.toml, provider keys, and model selections without calling an LLM")
    p.add_argument("--no-save", action="store_true", help="Don't write the synthesised comment to reviews/")
    p.add_argument("--no-clipboard", action="store_true", help="Don't copy the synthesised comment to the clipboard")
    p.add_argument("--no-stream", action="store_true", help="Disable live token streaming (auto-disabled in non-TTY)")
    p.add_argument("--output", metavar="PATH", help="Also write the synthesised PR comment to this path (used by the GitHub Action)")
    p.add_argument(
        "--fail-on",
        choices=("security", "optimization", "any"),
        help="Exit non-zero if the chosen check fails (CI gate mode)",
    )
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(parser, args)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
