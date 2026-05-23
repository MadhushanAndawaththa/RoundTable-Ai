# Contributing to RoundTable AI

Thanks for considering a contribution! This project is intentionally small — the
goal is for the entire system to fit comfortably in someone's head. Please keep
changes focused and the surface area minimal.

## Quick setup

```bash
git clone https://github.com/MadhushanAndawaththa/RoundTable-Ai.git
cd RoundTable-Ai
make install
cp pr_review_squad/.env.example pr_review_squad/.env   # add at least GEMINI_API_KEY
make demo
```

## Project layout

See **[Project structure](README.md#-project-structure)** in the README.

## Filing an issue

When opening an issue, please include:

- The command you ran
- The full error / unexpected output
- Your `squad.toml` contents (redact any secrets)
- Output of `python --version`

## Submitting a PR

1. Fork the repo and create a feature branch (`git checkout -b feat/my-thing`)
2. Make your change. Keep it focused — one logical change per PR.
3. Make sure `ruff check pr_review_squad/` is clean.
4. Run `make demo` and confirm it still works end-to-end.
5. Open the PR. **Bonus:** the `RoundTable AI · PR Review` workflow will run on
   your PR and post the squad's own review of your change. Address its
   findings if any.

## Adding a new LLM provider

The provider catalog lives in
[`pr_review_squad/providers.py`](pr_review_squad/providers.py). Adding a new
OpenAI-compatible provider is one dict entry — see existing `ProviderSpec`
definitions as a template.

If the provider isn't OpenAI-compatible, please open an issue first to discuss
the integration approach before sending a PR.

## What's out of scope

- Heavy refactors of the agent prompts (they intentionally mirror the brief)
- Adding non-CLI interfaces beyond the existing GitHub Action (a separate web
  UI repo is fine, but it shouldn't live in this codebase)
- Dependencies on heavy multi-LLM libraries (the OpenAI-compat approach is
  deliberate — see `providers.py` docstring)

## Code style

- Python 3.11+, `ruff` for linting
- Type hints encouraged but not enforced
- Prefer small, named helper functions over big inline blocks
