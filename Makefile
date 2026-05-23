.PHONY: help install demo review review-staged review-against pr check clean

PY ?= python
DIR := pr_review_squad
BASE ?= main

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python dependencies
	cd $(DIR) && $(PY) -m pip install -r requirements.txt

demo:  ## Run the squad on the bundled vulnerable sample diff
	cd $(DIR) && $(PY) cli.py --sample

review:  ## Run on working-tree changes, or FILE=path/to.diff for a saved diff
	cd $(DIR) && $(PY) cli.py $(if $(FILE),--file $(FILE),--git-diff)

review-staged:  ## Run on staged changes via git diff --cached
	cd $(DIR) && $(PY) cli.py --cached

review-against:  ## Run against BASE=main using merge-base + current branch/worktree
	cd $(DIR) && $(PY) cli.py --against $(BASE)

pr:  ## Run on a GitHub PR: make pr URL=https://github.com/owner/repo/pull/123
	cd $(DIR) && $(PY) cli.py --pr-url $(URL)

check:  ## Validate .env, squad.toml, keys, and model setup without calling an LLM
	cd $(DIR) && $(PY) cli.py --check

clean:  ## Remove generated review markdown files
	rm -f $(DIR)/reviews/review_*.md
