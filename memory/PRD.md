# PRD — Automated PR Code Review Squad (CLI)

## Original Problem Statement
Build a 3-agent system that reviews a Git diff and produces a polished PR comment.

- **Agent 1: Security Auditor** — flags vulnerabilities & unsafe data handling.
- **Agent 2: Optimization Expert** — flags perf/clean-code issues (1-3 actionable suggestions).
- **Agent 3: Tech Lead (Synthesizer)** — merges both reports into one empathetic, Markdown-formatted PR comment.

Lightweight: text-only, no DB, no UI. Terminal-runnable.

## User Choices (locked-in)
- **Interface:** CLI only (no web app)
- **LLM:** Google Gemini via free Google AI Studio key (`google-genai` SDK)
- **Input mode:** GitHub PR URL (also supports `--file` and `--sample` for demos)
- **Outputs:** live terminal render + auto-save to `reviews/review_<timestamp>.md` + auto-copy to clipboard
- **Aesthetic:** Developer-focused dark IDE (rich-powered, monokai diff theme, cyan/red/yellow agent panels)

## Architecture
```
pr_review_squad/
├── cli.py              # argparse + rich UI + orchestration + save/clipboard
├── agents.py           # 3 system prompts + GeminiAgent wrapper (google-genai)
├── github_fetcher.py   # parses PR URL, fetches application/vnd.github.v3.diff
├── samples/sample_diff.txt
├── reviews/            # auto-generated PR-comment Markdown files
├── requirements.txt
├── .env.example        # GEMINI_API_KEY, optional GITHUB_TOKEN, optional GEMINI_MODEL
└── README.md
```

## Implemented (2026-05-22)
- ✅ Three-agent sequential pipeline with exact prompts from the brief
- ✅ Google Gemini via the official `google-genai` SDK (`gemini-2.0-flash` default)
- ✅ GitHub PR URL fetching via REST diff media type (supports optional `GITHUB_TOKEN`)
- ✅ File input (`--file`) and bundled vulnerable sample (`--sample`)
- ✅ Dark-IDE terminal UX: ASCII banner, syntax-highlighted diff panel, per-agent coloured panels, status spinners
- ✅ Auto-save synthesised PR comment to `reviews/review_<timestamp>.md`
- ✅ Auto-copy to clipboard (graceful fallback in headless envs)
- ✅ Clear, friendly error when `GEMINI_API_KEY` is missing (with link to free-tier key)
- ✅ End-to-end smoke test passing (rendering, save, clipboard fallback verified)

## Iteration 3 (2026-05-22) — Multi-provider mode 🎉
- ✅ Replaced `google-genai` with `openai` SDK as the **single unified client** for all providers
- ✅ New `providers.py` with a 6-provider catalog (gemini, grok, openrouter, openai, deepseek, groq) — each one a 5-line `ProviderSpec`, trivial to extend
- ✅ New `squad.toml` lets users assign a different provider+model to each agent
- ✅ Ships with `squad.multi-provider.toml.example` showing rationale-driven mixing (Claude for security, Gemini for optimization, Grok for prose)
- ✅ `cli.py` shows a **🪑 Round Table panel** at the start of every run with each agent's provider/model
- ✅ Per-agent footnote (`via <provider> · <model>`) inside each agent's output panel
- ✅ Final-comment subtitle (`synthesised by <provider> · <model>`)
- ✅ New CLI flags: `--config PATH`, `--provider NAME` (force all to one provider for quick tests)
- ✅ Clear, sectioned missing-key error showing exactly which env vars are needed + sign-up URLs
- ✅ Backwards-compatible: existing single-key Gemini users need zero config changes (default `squad.toml` is all-Gemini)
- ✅ README rewritten with a dedicated multi-provider section + provider comparison table
- ✅ All five flows smoke-tested: default Gemini, missing-key, multi-provider TOML, `--provider` override, `--model` override

## Backlog
### P1
- Streaming responses (token-by-token agent output)
- `--model` CLI flag override
- Markdown report includes both raw agent reports (collapsible `<details>`)

### P2
- `gh` CLI integration for auto-posting the comment to the PR
- Third input mode: `git diff HEAD~1` auto-pickup inside a repo
- Optional cost/latency summary at the end
- Pluggable provider abstraction (OpenAI/Anthropic/Grok) selectable via env

## Setup for the user
1. `cd pr_review_squad && pip install -r requirements.txt`
2. `cp .env.example .env` and paste a free Gemini key from <https://aistudio.google.com/apikey>
3. `python cli.py --sample` (or `--file my.diff`, or `--pr-url https://github.com/owner/repo/pull/123`)
