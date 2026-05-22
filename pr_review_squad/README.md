# pr_review_squad

The Python package that powers RoundTable AI.

👉 **See the top-level [README](../README.md) for setup, usage, and CLI reference.**

## Module map

| File | Responsibility |
| --- | --- |
| `cli.py` | Argument parsing, terminal UI, orchestration, save & clipboard |
| `agents.py` | The three system prompts + `GeminiAgent` wrapper (uses `google-genai`) |
| `github_fetcher.py` | Parses a PR URL and pulls the unified diff from GitHub's REST API |
| `samples/` | Bundled demo diff(s) used by `--sample` |
| `reviews/` | Auto-generated PR-comment markdown files (gitignored) |
| `.env.example` | Copy to `.env` and paste your Gemini key |
