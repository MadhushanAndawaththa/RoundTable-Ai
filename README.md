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

Powered by **Google Gemini** via the official `google-genai` SDK. **Free to run**
with a Google AI Studio key. Pure-Python CLI — no DB, no server, no UI dependency.

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
| `--model NAME` | Override the Gemini model for this run (e.g. `--model gemini-2.5-flash`) |
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
<summary><b>"Missing GEMINI_API_KEY"</b></summary>

The CLI couldn't read your key. Make sure:
- `pr_review_squad/.env` exists (you copied it from `.env.example`)
- The line is `GEMINI_API_KEY=AIzaSy...` with **no quotes, no spaces**
- You didn't leave the literal placeholder `your_gemini_api_key_here`
</details>

<details>
<summary><b>"Gemini call failed: 404 ... model not found"</b></summary>

The model name in `.env` (or your `--model` flag) isn't available on your key.
Try one of these widely-available names:
- `gemini-2.0-flash` (default — fast & free)
- `gemini-2.5-flash` (newer)
- `gemini-2.5-pro` (slower, higher quota tier)

```bash
python pr_review_squad/cli.py --sample --model gemini-2.5-flash
```
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
├── Makefile                      # one-command shortcuts
├── README.md                     # ← you're reading it
├── .python-version               # pyenv hint (3.11)
└── pr_review_squad/
    ├── cli.py                    # argparse + rich UI + orchestration
    ├── agents.py                 # the three system prompts + GeminiAgent wrapper
    ├── github_fetcher.py         # GitHub REST API → unified diff
    ├── requirements.txt
    ├── .env.example              # copy → .env, paste your key
    ├── samples/sample_diff.txt   # deliberately vulnerable demo file
    └── reviews/                  # auto-generated PR-comment markdown (gitignored)
```

---

## 🧭 Roadmap

- [ ] **Streaming output** — agent responses stream token-by-token to the terminal
- [ ] **`pip install .` entry-point** so `pr-review-squad` is a real binary on `$PATH`
- [ ] **GitHub Actions workflow** that runs RoundTable AI on every PR opened against this repo
- [ ] **Token / cost summary** displayed at the end of each run
- [ ] **Provider abstraction** so OpenAI, Anthropic, or xAI Grok keys can swap in via env
- [ ] **`gh` CLI integration** to auto-post the synthesised comment to the PR

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
