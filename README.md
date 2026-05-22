# RoundTable AI

> Three specialised AI agents review your Git diff at a virtual round table,
> then your Tech Lead writes the Pull-Request comment for you.

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

Powered by **any OpenAI-compatible LLM provider** — Google Gemini, xAI Grok,
OpenRouter, OpenAI, DeepSeek, Groq, and more. **One agent, one provider, one
model — your call.** No third-party multi-LLM library required; we just swap
`base_url` per provider and call it a day. Pure-Python CLI — no DB, no server,
no UI dependency.

---

## ✨ What it does

For any unified diff (a GitHub PR URL, a local `.diff` file, or the bundled
sample) RoundTable AI:

1. **Security Auditor** scans for vulnerabilities, unsafe data handling and leaked secrets
2. **Optimization Expert** finds perf issues, dead code, DRY violations and naming smells
3. **Tech Lead** merges the two reports into a single, empathetic, Markdown-formatted
   PR comment ready to paste into GitHub

You get:
- 🎨 A dark-IDE-styled terminal walkthrough (syntax-highlighted diff + colour-coded agent panels)
- 📝 The final PR comment saved to `pr_review_squad/reviews/review_<timestamp>.md`
- 📋 The final PR comment automatically copied to your clipboard
- 🔍 The raw Security & Optimization reports stashed at the bottom of the `.md` (collapsible `<details>` blocks) so you can audit what each agent actually said

---

## 🚀 Quick start (under a minute)

> **Prerequisites:** Python 3.10+ and `make` (already on macOS & Linux; on
> Windows use `wsl` or run the raw python commands from the "Manual" section below).

```bash
# 1. Clone
git clone https://github.com/MadhushanAndawaththa/RoundTable-Ai.git
cd RoundTable-Ai

# 2. Install Python deps
make install

# 3. Paste your free Gemini key (see next section for how to get one)
cp pr_review_squad/.env.example pr_review_squad/.env
$EDITOR pr_review_squad/.env        # or: nano / code / vim

# 4. Run the demo
make demo
```

That's it. You'll see the three agents take turns in the terminal and a final
PR comment will land in `pr_review_squad/reviews/`.

---

## 🔑 Getting your free Gemini API key

> By default RoundTable AI uses **Google Gemini for all three agents** — so you
> only need one key to get started. To mix providers, see the
> [Multi-provider section](#-multi-provider-mode-the-fun-part) below.

1. Go to **<https://aistudio.google.com/apikey>**
2. Sign in with a Google account
3. Click **"Create API key"** → "Create API key in new project"
4. Copy the key (starts with `AIza…`)
5. Open `pr_review_squad/.env` and paste it:

   ```bash
   GEMINI_API_KEY=AIzaSy...your-key-here
   ```

Google AI Studio's free tier currently includes generous quota on
`gemini-2.0-flash` — plenty for running this tool dozens of times a day.

---

## 🌐 Multi-provider mode (the fun part)

RoundTable AI talks to LLMs via the **OpenAI-compatible Chat Completions API**,
so any provider that speaks it works out of the box. Six are pre-wired:

| Provider | Env var | Free tier? | Notes |
|---|---|---|---|
| Google Gemini | `GEMINI_API_KEY` | ✅ generous | Fast, great at code |
| xAI Grok | `XAI_API_KEY` | small credit | Conversational, witty |
| OpenRouter | `OPENROUTER_API_KEY` | some free models | Aggregator: Claude, GPT, Llama, … |
| OpenAI | `OPENAI_API_KEY` | ❌ paid | GPT-4o, o1, … |
| DeepSeek | `DEEPSEEK_API_KEY` | small credit | deepseek-chat, deepseek-reasoner |
| Groq | `GROQ_API_KEY` | ✅ generous | Sub-second inference on Llama/Mixtral |

### Pick a model per agent — edit `pr_review_squad/squad.toml`

```toml
[security_auditor]
# Anthropic Claude is famously careful — ideal for security review.
provider = "openrouter"
model = "anthropic/claude-3.5-haiku"

[optimization_expert]
# Gemini Flash has strong, fast code reasoning.
provider = "gemini"
model = "gemini-2.0-flash"

[tech_lead]
# Grok writes warm, conversational prose — great for PR comments.
provider = "grok"
model = "grok-2-latest"
```

Then drop the matching keys into `pr_review_squad/.env` and run `make demo`.

A ready-to-use config ships at
[`pr_review_squad/squad.multi-provider.toml.example`](pr_review_squad/squad.multi-provider.toml.example) —
just `cp` it over `squad.toml` to activate.

### What you'll see

```
╭───────────── 🪑 The Round Table ──────────────╮
│ 🔐 Security Auditor    openrouter  anthropic/claude-3.5-haiku │
│ ⚡ Optimization Expert  gemini      gemini-2.0-flash           │
│ 🧑‍💼 Tech Lead            grok        grok-2-latest              │
╰───────────────────────────────────────────────╯
```

Each agent's panel labels which provider/model produced its output, and the
final synthesised PR comment is tagged with the Tech Lead's model in its
subtitle — so when you screen-record a demo, the multi-provider story is
visible at a glance.

---

## 🧑‍💻 Usage

### Mode 1 — Bundled sample (no setup, great for demos)

```bash
make demo
# equivalent to:
python pr_review_squad/cli.py --sample
```

Runs the agents over `pr_review_squad/samples/sample_diff.txt`, a deliberately
vulnerable Python file (SQL injection, MD5 password hashing, command injection,
hardcoded credentials, O(n²) lookup, redundant loops). Perfect for a screen-recorded demo.

### Mode 2 — A local diff file

```bash
# generate a diff first
git diff main..my-feature > my.diff

# review it
make review FILE=my.diff
# equivalent to:
python pr_review_squad/cli.py --file my.diff
```

Accepts any unified diff — output of `git diff`, `git show`, `git format-patch`, etc.

### Mode 3 — A live GitHub Pull Request

```bash
make pr URL=https://github.com/psf/requests/pull/6800
# equivalent to:
python pr_review_squad/cli.py --pr-url https://github.com/psf/requests/pull/6800
```

Fetches the unified diff straight from GitHub's REST API.
- **Public PRs:** works out of the box (anonymous, 60 requests/hour).
- **Private PRs or higher rate limit:** add a `GITHUB_TOKEN` to `.env`. Generate one at
  <https://github.com/settings/tokens> — no scopes needed for public repos; the `repo`
  scope is enough for private ones.

---

## 🎛️ CLI reference

```text
pr-review-squad [--sample | --file FILE | --pr-url URL]
                [--model MODEL] [--no-save] [--no-clipboard]
```

| Flag | Description |
|---|---|
| `--sample` | Use the bundled vulnerable sample diff |
| `--file PATH` | Review a unified diff from a local file |
| `--pr-url URL` | Review a live GitHub PR (`https://github.com/<owner>/<repo>/pull/<n>`) |
| `--config PATH` | Use a non-default `squad.toml` (defaults to `pr_review_squad/squad.toml`) |
| `--provider NAME` | Force **all three** agents to one provider (`gemini` / `grok` / `openrouter` / `openai` / `deepseek` / `groq`) |
| `--model NAME` | Force **all three** agents to one model |
| `--no-save` | Skip writing the markdown file (useful in CI) |
| `--no-clipboard` | Skip copying to clipboard (useful in CI / headless) |
| `-h, --help` | Show the built-in help |

### Make targets

| Command | What it does |
|---|---|
| `make install` | Install Python dependencies |
| `make demo` | Run on the bundled sample diff |
| `make review FILE=path.diff` | Run on a local diff file |
| `make pr URL=https://github.com/.../pull/N` | Run on a live GitHub PR |
| `make clean` | Delete generated review markdown files |
| `make help` | List all targets |

---

## 📤 What you'll see

A run looks roughly like this in your terminal:

```
  ____  ____    ____            _                ____                       _
 |  _ \|  _ \  |  _ \ _____   _(_) _____      __/ ___|  __ _ _   _  __ _  __| |
 | |_) | |_) | | |_) / _ \ \ / / |/ _ \ \ /\ / /\___ \ / _` | | | |/ _` |/ _` |
 |  __/|  _ <  |  _ <  __/\ V /| |  __/\ V  V /  ___) | (_| | |_| | (_| | (_| |
 |_|   |_| \_\ |_| \_\___| \_/ |_|\___| \_/\_/  |____/ \__, |\__,_|\__,_|\__,_|
                                                          |_|

source: sample (sample_diff.txt)    model: gemini-2.0-flash

┌── git diff ───────────────────────────────────────────────────────────┐
│  + def get_user_by_email(email):                                      │
│  +     query = "SELECT ... WHERE email = '" + email + "'"             │
│  ...                                                                  │
└───────────────────────────────────────────────────────────────────────┘

┌── 🔐 Security Auditor ─────────────────────────────────────────────────┐
│  • SQL Injection in get_user_by_email                                  │
│  • Hardcoded API key leaked in source                                  │
│  • MD5 password hashing is broken                                      │
└───────────────────────────────────────────────────────────────────────┘

┌── ⚡ Optimization Expert ──────────────────────────────────────────────┐
│  1. list_active_users makes two passes; merge into one comprehension.  │
│  2. find_user is O(n²); replace inner loop or use a dict lookup.       │
└───────────────────────────────────────────────────────────────────────┘

─────────────────────── Final PR Comment ───────────────────────────────

┌───────────────────────────────────────────────────────────────────────┐
│  Great work pushing this feature forward! 🎉                          │
│                                                                       │
│  🚨 Security                                                          │
│  • SQL injection in get_user_by_email – use parameterised queries.    │
│  • Hardcoded API key must be revoked and moved to env vars.           │
│  • Switch MD5 → bcrypt/argon2 for password hashing.                   │
│                                                                       │
│  💡 Suggestions for Improvement                                       │
│  • Collapse list_active_users into one comprehension.                 │
│  • find_user is O(n²); a single loop is enough.                       │
└───────────────────────────────────────────────────────────────────────┘

📝 Saved to pr_review_squad/reviews/review_20260522_204521.md
📋 Copied to clipboard
```

The saved `.md` file is **GitHub-ready** — paste it straight into a PR comment.

---

## 🛠️ Troubleshooting

<details>
<summary><b>"Missing API key(s) for your squad.toml"</b></summary>

The CLI lists exactly which env var is missing and where to sign up. Open
`pr_review_squad/.env`, paste the missing key, and re-run.

If you only want to run with Gemini, make sure your `squad.toml` still uses
`provider = "gemini"` for all three agents (that's the default).
</details>

<details>
<summary><b>"LLM call failed: 404 ... not found"</b></summary>

The model name in `squad.toml` (or your `--model` flag) doesn't exist for that
provider. A few safe defaults per provider:

| Provider | Known-good model |
|---|---|
| `gemini` | `gemini-2.0-flash`, `gemini-2.5-flash` |
| `grok` | `grok-2-latest`, `grok-3` |
| `openrouter` | `anthropic/claude-3.5-haiku`, `meta-llama/llama-3.3-70b-instruct` |
| `openai` | `gpt-4o-mini`, `gpt-4o` |
| `deepseek` | `deepseek-chat`, `deepseek-reasoner` |
| `groq` | `llama-3.3-70b-versatile`, `mixtral-8x7b-32768` |

Quick override without editing TOML:

```bash
python pr_review_squad/cli.py --sample --provider gemini --model gemini-2.5-flash
```
</details>

<details>
<summary><b>"LLM call failed: 401 ... unauthorized"</b></summary>

The API key for that provider is wrong/expired. Re-check `.env` (no quotes, no
trailing spaces) and that you're using the matching env var (e.g. `XAI_API_KEY`
not `GROK_API_KEY`).
</details>

<details>
<summary><b>"Clipboard unavailable on this system"</b></summary>

You're running in a headless environment (SSH, Docker, WSL without an X server).
The markdown is still saved to `reviews/` — just `cat` it and copy by hand.
On Linux desktops you can install `xclip` or `xsel` to enable clipboard support:

```bash
sudo apt-get install xclip
```
</details>

<details>
<summary><b>"GitHub rate-limited the request (403)"</b></summary>

Anonymous GitHub API access is capped at 60 requests/hour. Generate a personal
access token at <https://github.com/settings/tokens> (no scopes needed for
public repos) and add it to `.env`:

```bash
GITHUB_TOKEN=ghp_yourtokenhere
```

This raises the limit to 5,000/hour.
</details>

<details>
<summary><b>"PR not found (404)"</b></summary>

Either the URL is wrong (expected format: `https://github.com/<owner>/<repo>/pull/<number>`)
or the PR is in a private repo. For private repos add a `GITHUB_TOKEN` with the `repo` scope.
</details>

---

## 📁 Project layout

```
RoundTable-Ai/
├── Makefile                              # one-command shortcuts
├── README.md                             # ← you're reading it
├── .python-version                       # pyenv hint (3.11)
└── pr_review_squad/
    ├── cli.py                            # argparse + rich UI + orchestration
    ├── agents.py                         # 3 system prompts + LLMAgent wrapper
    ├── providers.py                      # provider catalog + squad config loader
    ├── github_fetcher.py                 # GitHub REST API → unified diff
    ├── squad.toml                        # which provider+model each agent uses
    ├── squad.multi-provider.toml.example # ready-to-cp multi-provider config
    ├── requirements.txt
    ├── .env.example                      # copy → .env, paste your keys
    ├── samples/sample_diff.txt           # deliberately vulnerable demo file
    └── reviews/                          # auto-generated PR-comment markdown
```

---

## 🧭 Roadmap

- [ ] **Streaming output** — agent responses stream token-by-token to the terminal
- [ ] **`pip install .` entry-point** so `roundtable-ai` is a real binary on `$PATH`
- [ ] **GitHub Actions workflow** that runs RoundTable AI on every PR opened against this repo
- [ ] **Token / cost summary** displayed at the end of each run (now that we have multiple providers, this is extra interesting)
- [ ] **`gh` CLI integration** to auto-post the synthesised comment to the PR
- [x] ~~**Pluggable provider abstraction** (Grok / OpenAI / Anthropic) — done in v2~~

---

## 📜 Manual setup (no `make`)

If you can't or don't want to use `make`:

```bash
git clone https://github.com/MadhushanAndawaththa/RoundTable-Ai.git
cd RoundTable-Ai/pr_review_squad
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then paste your Gemini key
python cli.py --sample
```

---

## 📄 License

MIT — do whatever you like, attribution appreciated.
