.PHONY: help install demo review clean

PY ?= python
DIR := pr_review_squad

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python dependencies
	cd $(DIR) && $(PY) -m pip install -r requirements.txt

demo:  ## Run the squad on the bundled vulnerable sample diff
	cd $(DIR) && $(PY) cli.py --sample

review:  ## Run on a file: make review FILE=path/to.diff
	cd $(DIR) && $(PY) cli.py --file $(FILE)

pr:  ## Run on a GitHub PR: make pr URL=https://github.com/owner/repo/pull/123
	cd $(DIR) && $(PY) cli.py --pr-url $(URL)

clean:  ## Remove generated review markdown files
	rm -f $(DIR)/reviews/review_*.md
