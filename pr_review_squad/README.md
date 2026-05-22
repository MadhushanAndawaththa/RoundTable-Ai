# PR Review Squad

A lightweight CLI that runs **three specialised AI agents** over a Git diff and
synthesises a single, polished Pull-Request comment.

```
  Security Auditor  →  Optimization Expert  →  Tech Lead (synthesizer)
       (Gemini)             (Gemini)               (Gemini)
```

The final Markdown comment is printed in the terminal, **saved to
`reviews/review_<timestamp>.md`**, and **auto-copied to your clipboard** so you
can paste it straight into GitHub.

---

## Why it's nice

- **Zero infra** — single Python script, no DB, no server.
- **Free LLM tier** — uses Google AI Studio's free Gemini key.
- **Three input modes** — GitHub PR URL, local diff file, or a bundled
  vulnerability-rich sample.
- **Dark IDE aesthetic** — `rich`-powered terminal output with syntax-highlighted diffs.

---

## Setup

```bash
cd pr_review_squad
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# then edit .env and paste your Gemini key
```

Get a **free** Gemini API key at <https://aistudio.google.com/apikey>.
For private repos or to dodge GitHub's 60-req/hour anonymous limit, add a
`GITHUB_TOKEN` from <https://github.com/settings/tokens> (no scopes required for
public repos).

---

## Usage

```bash
# 1. Bundled sample (great for a quick demo / screenshot)
python cli.py --sample

# 2. Local diff file
git diff main..feature/login > my.diff
python cli.py --file my.diff

# 3. Live GitHub PR
python cli.py --pr-url https://github.com/psf/requests/pull/6800
```

You'll see each agent's verdict appear live, followed by the synthesised PR
comment. The Markdown is saved under `reviews/` and copied to your clipboard.

---

## Architecture

| File                  | Responsibility                                                  |
| --------------------- | --------------------------------------------------------------- |
| `cli.py`              | Argument parsing, terminal UI, orchestration, persistence       |
| `agents.py`           | The three system prompts + `GeminiAgent` wrapper                |
| `github_fetcher.py`   | Pulls `application/vnd.github.v3.diff` for a given PR URL       |
| `samples/`            | A vulnerable + inefficient sample diff for demos                |
| `reviews/`            | Auto-generated PR-comment Markdown files                        |

The agents pass information **sequentially**: the Security Auditor and
Optimization Expert each read the raw diff; the Tech Lead then receives both of
their reports and produces the final, empathetic PR comment.

---

## Resume talking points

- Designed a **multi-agent LLM workflow** with clearly bounded responsibilities.
- Integrated with **GitHub's REST API** (diff media type) and the **Gemini SDK**.
- Built a polished terminal UX with `rich` (panels, spinners, syntax highlighting).
- Output is **persisted and clipboard-ready** — a real developer-workflow tool.
