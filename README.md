<h1 align="center">🪑 RoundTable AI</h1>

<p align="center">
  <em>Three specialised LLM agents sit at a round table and review your pull requests.</em><br/>
  <em>One reads it for security, one for performance, the third writes the comment.</em>
</p>

<p align="center">
  <a href="https://github.com/MadhushanAndawaththa/RoundTable-Ai/actions/workflows/roundtable.yml"><img src="https://img.shields.io/github/actions/workflow/status/MadhushanAndawaththa/RoundTable-Ai/roundtable.yml?branch=main&label=PR%20review&logo=githubactions&logoColor=white" alt="GitHub Action status"/></a>
  <a href="#-license"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"/></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg?logo=python&logoColor=white" alt="Python 3.11+"/>
  <img src="https://img.shields.io/badge/providers-Gemini%20·%20Grok%20·%20OpenRouter%20·%20OpenAI%20·%20DeepSeek%20·%20Groq-7c3aed" alt="Supported providers"/>
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs welcome"/>
</p>

<p align="center">
  <a href="#-quick-start-60-seconds"><b>Quick start</b></a> ·
  <a href="#-the-six-supported-providers"><b>Providers</b></a> ·
  <a href="#-mixing-providers-per-agent"><b>Multi-provider</b></a> ·
  <a href="#-github-action-auto-review-every-pr"><b>GitHub Action</b></a> ·
  <a href="#-cli-reference"><b>CLI</b></a> ·
  <a href="#-troubleshooting"><b>Troubleshooting</b></a>
</p>

---

```
            ┌────────────────────────┐
            │      git diff          │
            └───────────┬────────────┘
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
 ┌────────────────┐             ┌────────────────┐
 │  🔐 Security   │             │ ⚡ Optimization │
 │    Auditor     │             │    Expert      │
 └────────┬───────┘             └────────┬───────┘
          │                              │
          └──────────────┬───────────────┘
                         ▼
                ┌─────────────────┐
                │  🧑‍💼 Tech Lead   │  ← synthesises both reports
                └────────┬────────┘
                         ▼
                Polished PR comment
              (terminal + .md + 📋 clipboard)
```

---

## ✨ Features

- **3-agent review pipeline** — Security · Optimization · Tech Lead synthesiser
- **6 LLM providers supported** — Gemini, xAI Grok, OpenRouter, OpenAI, DeepSeek, Groq
- **Per-agent provider mixing** — different model per role via one TOML file
- **Live token streaming** in the terminal (auto-disables in CI)
- **GitHub Action included** — opens every PR? gets a review comment in ~30 s
- **CI-gate mode** (`--fail-on`) — block merges on security findings
- **Three input modes** — bundled sample, local `.diff` file, live GitHub PR URL
- **GitHub-ready output** — final markdown saved to disk + auto-copied to clipboard
- **Single dependency for LLMs** — `openai` SDK + base-URL switching, no LiteLLM bloat

## 📺 What a run looks like

```
🪑 The Round Table
  🔐 Security Auditor      groq         llama-3.1-8b-instant
  ⚡ Optimization Expert   groq         llama-3.1-8b-instant
  🧑‍💼 Tech Lead             groq         llama-3.3-70b-versatile

[ syntax-highlighted git diff appears here ]

🔐 Security Auditor finds: SQL injection, MD5 hashing, hardcoded credential
⚡ Optimization Expert finds: O(n²) lookup, redundant loops, naming smells
🧑‍💼 Tech Lead writes a friendly, sectioned PR comment with both findings

📝 Saved to pr_review_squad/reviews/review_20260523_142211.md
📋 Copied to clipboard

Verdict
  ✓ Security check passed
  ✓ Optimization check passed
```

---

## 🚀 Quick start (60 seconds)

> **Prerequisites:** Python 3.11+ and `make` (macOS/Linux ship with `make`;
> Windows users: use WSL or follow the [Manual setup](#manual-setup) section.)

```bash
# 1. Clone
git clone https://github.com/MadhushanAndawaththa/RoundTable-Ai.git
cd RoundTable-Ai

# 2. Install Python deps
make install

# 3. Create your .env (then paste the key for the provider(s) your squad.toml uses)
cp pr_review_squad/.env.example pr_review_squad/.env

# 4. Run the demo on a bundled vulnerable sample diff
make demo
```

That's it. You'll see the three agents take turns in the terminal and a final
PR comment will land in `pr_review_squad/reviews/`.

---

## 🔑 API keys

You only need a key for the providers you actually use in `squad.toml`.

Any supported AI provider key can be used here: Gemini, Groq, xAI Grok,
OpenRouter, DeepSeek, or OpenAI. The only rule is that the key in `.env` must
match the `provider` values in `pr_review_squad/squad.toml`.

### Current repo default (Groq)

The current `pr_review_squad/squad.toml` in this repo uses **Groq for all three
agents**, so **one free key is enough to run everything as-is:**

1. Go to <https://console.groq.com/keys> → sign in → **Create API key**
2. Paste it into `pr_review_squad/.env`:
   ```ini
  GROQ_API_KEY=gsk_...your-key-here
   ```

### Want to use a different provider or mix providers?

RoundTable AI is not locked to one vendor. You can use one provider for all
three agents, or mix providers per agent, by editing `pr_review_squad/squad.toml`.
After that, add only the matching key(s) to `.env`.

For example, if you want the included free-tier Gemini + Groq preset, activate it:

```bash
cp pr_review_squad/squad.gemini-groq.toml.example pr_review_squad/squad.toml
```

Then add both keys to `.env`:

```ini
GEMINI_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...
```

Run `make demo` again — the round-table panel will now show two different
providers in the seats.

If you prefer a single-provider setup instead, set all three `provider =` values
in `pr_review_squad/squad.toml` to the same provider and add that provider's key
to `.env`.

---

## 🌐 The six supported providers

| Provider     | Env var               | Free tier?    | Sign-up                                                |
|--------------|-----------------------|---------------|--------------------------------------------------------|
| Gemini       | `GEMINI_API_KEY`      | ✅ generous   | <https://aistudio.google.com/apikey>                   |
| Groq         | `GROQ_API_KEY`        | ✅ generous   | <https://console.groq.com/keys>                        |
| xAI Grok     | `XAI_API_KEY`         | small credit  | <https://console.x.ai/>                                |
| OpenRouter   | `OPENROUTER_API_KEY`  | some free models | <https://openrouter.ai/keys>                        |
| DeepSeek     | `DEEPSEEK_API_KEY`    | small credit  | <https://platform.deepseek.com/api_keys>               |
| OpenAI       | `OPENAI_API_KEY`      | ❌ paid       | <https://platform.openai.com/api-keys>                 |

All six are reached through the OpenAI-compatible Chat Completions API — RoundTable
AI just swaps `base_url` per provider. Adding a 7th provider is a 5-line dict entry
in [`pr_review_squad/providers.py`](pr_review_squad/providers.py).

---

## 🎛️ Mixing providers per agent

Edit `pr_review_squad/squad.toml`. Each agent gets its own `provider` and `model`:

```toml
[security_auditor]
provider = "openrouter"
model = "anthropic/claude-3.5-haiku"

[optimization_expert]
provider = "gemini"
model = "gemini-2.0-flash"

[tech_lead]
provider = "grok"
model = "grok-2-latest"
```

You can also use provider-aware model aliases when you do not want to memorize
specific model IDs:

```toml
[security_auditor]
provider = "groq"
model = "default-fast"

[tech_lead]
provider = "groq"
model = "default-best"
```

`default-fast` and `default-best` resolve to a built-in recommended model for
that provider.

Two ready-made presets ship with the repo — copy whichever you like over `squad.toml`:

| Preset file | What it does |
|---|---|
| `squad.gemini-groq.toml.example` | Free-tier-only mix (Gemini + Groq Llama) |
| `squad.multi-provider.toml.example` | Showcase mix (Claude · Gemini · Grok) |

Don't forget to add the matching keys to `.env`.

---

## 🧑‍💻 Usage

### Bundled sample (great for demos)

```bash
make demo
# equivalent to:
python pr_review_squad/cli.py --sample
```

Reviews `pr_review_squad/samples/sample_diff.txt` — a deliberately vulnerable file
containing SQL injection, MD5 password hashing, command injection, hardcoded
credentials, an O(n²) lookup, and redundant loops.

### Current working tree (no temp `.diff` file needed)

```bash
python pr_review_squad/cli.py --git-diff

# or:
make review
```

This reviews your current unstaged working-tree changes directly via `git diff`.

### Only staged changes

```bash
python pr_review_squad/cli.py --cached

# or:
make review-staged
```

This reviews only what you have already staged with `git add`.

### Current branch/worktree against a base ref

```bash
python pr_review_squad/cli.py --against main

# or:
make review-against BASE=main
```

This compares your current branch and working tree against the merge-base with
the base ref, which is useful before opening a PR.

### A local diff file

```bash
git diff main..my-feature > my.diff
make review FILE=my.diff
```

### A live GitHub PR

```bash
make pr URL=https://github.com/owner/repo/pull/123
```

For private PRs, add a `GITHUB_TOKEN` to `.env` (create at <https://github.com/settings/tokens>).

### Preflight check

```bash
python pr_review_squad/cli.py --check

# or:
make check
```

This validates your `.env`, `squad.toml`, required API keys, alias resolution,
and provider/model combinations without making any LLM calls.

---

## 🤖 GitHub Action (auto-review every PR)

The repo ships a ready-to-use workflow at
[`.github/workflows/roundtable.yml`](.github/workflows/roundtable.yml). Once
installed on your repo, **every pull request gets a round-table review posted
as a comment** within ~30 seconds of being opened.

### Setup (one-time, 60 seconds)

1. Push this repo (or fork it) to GitHub.
2. **Settings → Secrets and variables → Actions → New repository secret** — add
   the keys for the providers your `squad.toml` uses. With the current repo
   default, that means `GROQ_API_KEY`.
3. Open a pull request. The squad's comment lands within a minute.

### Make it a merge gate

Append `--fail-on any` to the workflow's run step:

```yaml
- run: |
    python pr_review_squad/cli.py \
      --pr-url "${{ github.event.pull_request.html_url }}" \
      --no-clipboard --no-save --no-stream \
      --output "${{ runner.temp }}/review.md" \
      --fail-on any
```

Then require this check in **Settings → Branches → Branch protection rules**.

### Local CI gate (no Action needed)

```bash
# Exits 1 if security issues are found, 0 otherwise
python pr_review_squad/cli.py --file my.diff --fail-on security --no-clipboard
```

---

## 🎛️ CLI reference

```text
roundtable-ai [--sample | --file FILE | --pr-url URL | --git-diff]
              [--config PATH] [--provider NAME] [--model NAME]
              [--cached] [--against REF] [--check]
              [--no-stream] [--output PATH]
              [--fail-on {security,optimization,any}]
              [--no-save] [--no-clipboard]
```

| Flag | Description |
|---|---|
| `--sample` | Use the bundled vulnerable sample diff |
| `--git-diff`, `--working-tree` | Review current unstaged working-tree changes |
| `--file PATH` | Review a unified diff from a local file |
| `--pr-url URL` | Review a live GitHub PR |
| `--config PATH` | Use a non-default `squad.toml` |
| `--provider NAME` | Force all three agents to one provider |
| `--model NAME` | Force all three agents to one model; supports `default-fast` and `default-best` |
| `--cached` | Review staged changes via `git diff --cached` |
| `--against REF` | Review your current branch/worktree against a base ref such as `main` |
| `--check`, `--doctor` | Validate config and keys without calling an LLM |
| `--no-stream` | Disable live token streaming (auto-off outside a TTY) |
| `--output PATH` | Also write the PR comment to an explicit path |
| `--fail-on …` | **CI gate** — exit non-zero when the check fails |
| `--no-save` | Skip writing the markdown to `reviews/` |
| `--no-clipboard` | Skip clipboard copy |
| `-h, --help` | Show built-in help |

### Make targets

| Command | What it does |
|---|---|
| `make install` | Install Python dependencies |
| `make demo` | Run on the bundled sample diff |
| `make review` | Run on current unstaged working-tree changes |
| `make review FILE=path.diff` | Run on a saved local diff file |
| `make review-staged` | Run on staged changes |
| `make review-against BASE=main` | Run against a base ref such as `main` |
| `make pr URL=...` | Run on a live GitHub PR |
| `make check` | Validate keys, config, and model setup |
| `make clean` | Delete generated review markdown |
| `make help` | List all targets |

---

## 🛠️ Troubleshooting

<details>
<summary><b>"Missing API key(s) for your squad.toml"</b></summary>

The CLI lists exactly which env var is missing and where to sign up. Open
`pr_review_squad/.env`, paste the missing key, save, and re-run.

If you only want one provider, make sure all three sections in `squad.toml` use
that provider and that the matching key is present in `.env`. The current repo
default uses Groq.
</details>

<details>
<summary><b>"LLM call failed: 404 ... model not found"</b></summary>

The model name in `squad.toml` (or your `--model` flag) doesn't exist for that
provider. Try a known-good model from this table:

| Provider | Known-good model |
|---|---|
| `gemini` | `gemini-2.0-flash`, `gemini-2.5-flash` |
| `groq` | `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `qwen/qwen3-32b` |
| `grok` | `grok-2-latest`, `grok-3` |
| `openrouter` | `anthropic/claude-3.5-haiku`, `meta-llama/llama-3.3-70b-instruct` |
| `openai` | `gpt-4o-mini`, `gpt-4o` |
| `deepseek` | `deepseek-chat`, `deepseek-reasoner` |

Quick test without editing TOML:

```bash
python pr_review_squad/cli.py --sample --provider groq --model default-fast
```
</details>

<details>
<summary><b>"LLM call failed: 401 ... unauthorized"</b></summary>

The API key for that provider is wrong/expired. Re-check `.env` (no quotes, no
trailing spaces) and confirm you're using the matching env var (e.g.
`XAI_API_KEY` for Grok, not `GROK_API_KEY`).
</details>

<details>
<summary><b>"Clipboard unavailable on this system"</b></summary>

You're in a headless environment (SSH, Docker, WSL without an X server).
The markdown is still saved to `reviews/` — open it and copy manually.
On Linux desktops: `sudo apt-get install xclip` enables clipboard support.
</details>

<details>
<summary><b>"GitHub rate-limited the request (403)"</b></summary>

Anonymous GitHub API access is capped at 60 requests/hour. Add a personal
access token (no scopes needed for public repos) to `.env`:

```ini
GITHUB_TOKEN=ghp_yourtokenhere
```
</details>

<details>
<summary><b>"PR not found (404)"</b></summary>

Either the URL is malformed (expected `https://github.com/<owner>/<repo>/pull/<n>`)
or the PR is private. For private repos add a `GITHUB_TOKEN` with `repo` scope.
</details>

---

## ❓ FAQ

<details>
<summary><b>Why three agents instead of one big prompt?</b></summary>

Specialised personas give measurably more focused output than a single
generalist prompt. The Security agent ignores naming, the Optimization agent
ignores security, and the Tech Lead doesn't have to do raw analysis — it only
synthesises. Each piece does one job well.
</details>

<details>
<summary><b>Why OpenAI-compatible base-URL switching instead of LiteLLM?</b></summary>

Zero dependency bloat and a clearer mental model. Every major provider already
exposes an OpenAI-compatible endpoint; swapping `base_url` is enough to talk to
six providers with one SDK. Adding a seventh is a 5-line dict entry in
[`providers.py`](pr_review_squad/providers.py).
</details>

<details>
<summary><b>Does this send my private code to a third party?</b></summary>

Only if you point it at a hosted LLM provider — which is what every agent in
the shipped config in this repo does today. The unified diff (added/removed
lines only) is sent to
whichever provider that agent uses. Inspect `agents.py` to confirm. If your
threat model forbids cloud LLMs, point all three agents at a local
OpenAI-compatible endpoint (Ollama, LM Studio, vLLM) by adding a new
`ProviderSpec`.
</details>

<details>
<summary><b>Can I add more agents (e.g. an Accessibility Auditor)?</b></summary>

Yes — see the dictionary `AGENT_PROMPTS` in
[`pr_review_squad/agents.py`](pr_review_squad/agents.py). Add a new key + system
prompt, then wire it into `cli.py`'s `run()`. The current trio is the minimum
useful set, not a hard limit.
</details>

---

## 🏗️ How it works

```
cli.py        ─┬─→  loads squad.toml + .env
               ├─→  builds one OpenAI client per unique provider
               ├─→  runs Security → Optimization → Tech Lead in sequence
               └─→  saves markdown + copies to clipboard + (optional) --output

agents.py     ─→ LLMAgent: a (system_prompt, OpenAI client, model) bundle
                 with .run() and .stream() methods.

providers.py  ─→ Catalog of 6 ProviderSpecs + squad.toml loader + client factory.
                 Adding a provider = one dict entry.

github_fetcher.py ─→ Parses a PR URL, fetches `application/vnd.github.v3.diff`.

.github/workflows/roundtable.yml ─→ The Action that runs the squad on PRs and
                                    posts the comment.
```

## 📁 Project structure

```
RoundTable-Ai/
├── .github/workflows/roundtable.yml      # auto-reviews every PR on this repo
├── CONTRIBUTING.md
├── LICENSE
├── Makefile                              # one-command shortcuts
├── README.md                             # ← you're reading it
├── .python-version                       # pyenv hint (3.11)
└── pr_review_squad/
    ├── cli.py                            # argparse + rich UI + orchestration
    ├── agents.py                         # 3 system prompts + LLMAgent wrapper
    ├── providers.py                      # provider catalog + squad.toml loader
    ├── github_fetcher.py                 # GitHub REST API → unified diff
    ├── squad.toml                        # which provider+model each agent uses
    ├── squad.gemini-groq.toml.example    # free-tier preset (Gemini + Groq)
    ├── squad.multi-provider.toml.example # showcase preset (Claude + Gemini + Grok)
    ├── requirements.txt
    ├── .env.example                      # copy → .env, paste your keys
    ├── samples/sample_diff.txt           # deliberately vulnerable demo file
    └── reviews/                          # auto-generated PR-comment markdown
```

## <a name="manual-setup"></a>📦 Manual setup (no `make`)

```bash
git clone https://github.com/MadhushanAndawaththa/RoundTable-Ai.git
cd RoundTable-Ai/pr_review_squad
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then paste your keys
python cli.py --sample
```

---

## 🧭 Roadmap

- [x] **3-agent pipeline** (Security · Optimization · Tech Lead)
- [x] **Six providers** via OpenAI-compatible base-URL switching
- [x] **Per-agent provider mixing** via `squad.toml`
- [x] **Live token streaming** in the terminal
- [x] **GitHub Action** that auto-reviews PRs
- [x] **CI gate mode** (`--fail-on`)
- [ ] `pip install .` entry-point so `roundtable-ai` is on `$PATH`
- [ ] Token / cost summary per agent at end of run
- [ ] `gh` CLI integration to auto-post comments from local CLI
- [ ] Optional web UI (paste-diff / PR-URL form, BYO key)

---

## 🙌 Contributing

PRs and issues welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
Be aware: every PR you open on this repo gets reviewed by the squad itself.

## 📜 License

[MIT](LICENSE) — do whatever you like, attribution appreciated.

## 🙏 Acknowledgments

Inspired by the [Build3rs Stack](https://build3rs.dev) prompt format. The
three-agent architecture mirrors how real engineering teams already split a
code review between security, performance, and team-lead sign-off.
