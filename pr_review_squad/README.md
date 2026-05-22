# pr_review_squad

The Python package that powers RoundTable AI.

👉 **See the top-level [README](../README.md) for setup, usage, and the
multi-provider configuration guide.**

## Module map

| File | Responsibility |
| --- | --- |
| `cli.py` | Argument parsing, terminal UI (Round Table panel, agent panels), orchestration, save & clipboard |
| `agents.py` | The three system prompts + `LLMAgent` wrapper (OpenAI-compatible API) |
| `providers.py` | Catalog of supported providers + `squad.toml` loader + client factory |
| `github_fetcher.py` | Parses a PR URL and pulls the unified diff from GitHub's REST API |
| `squad.toml` | Which provider+model each agent uses (edit me!) |
| `squad.multi-provider.toml.example` | Ready-to-cp config that mixes providers |
| `samples/` | Bundled demo diff(s) used by `--sample` |
| `reviews/` | Auto-generated PR-comment markdown files (gitignored) |
| `.env.example` | Copy to `.env` and paste the API keys for the providers you use |
