# PR Review Squad

A lightweight, terminal-only multi-agent code reviewer.

The full project lives in **[`./pr_review_squad/`](./pr_review_squad/)** — see its
[README](./pr_review_squad/README.md) for setup and usage.

```bash
make install                  # install deps
cp pr_review_squad/.env.example pr_review_squad/.env   # paste a free Gemini key
make demo                     # run the squad on the bundled sample diff
```

Other commands:

```bash
make review FILE=my.diff                                      # review a local diff
make pr URL=https://github.com/psf/requests/pull/6800         # review a live PR
make help                                                     # list all targets
```
