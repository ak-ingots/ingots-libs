# Commands over every repository of the ecosystem (see repos.txt).
SHELL := /bin/bash
OWNER := ak-ingots
REPOS := $(shell grep -v '^\#' repos.txt)

.PHONY: help clone pull status check prs ci check-prototypes

help:
	@echo "clone   clone missing repositories (gh, uses gh auth)"
	@echo "pull    fast-forward every repository"
	@echo "status  branch, local changes and divergence of every repository"
	@echo "check   make check (lint, test) everywhere, dependencies first"
	@echo "prs     open pull requests across the ecosystem (gh)"
	@echo "ci      last workflow run of every repository (gh)"
	@echo "check-prototypes  run the design prototypes, compare mypy with their marks"

clone:
	@for r in $(REPOS); do [ -d $$r ] || gh repo clone $(OWNER)/$$r; done

pull:
	@git pull --ff-only
	@for r in $(REPOS); do echo "== $$r"; git -C $$r pull --ff-only || exit 1; done

status:
	@echo "== (meta)"; git status -sb | head -5
	@for r in $(REPOS); do echo "== $$r"; git -C $$r status -sb | head -5; done

check:
	@for r in $(REPOS); do $(MAKE) -C $$r check || exit 1; done

prs:
	@for r in $(REPOS); do echo "== $$r"; gh pr list -R $(OWNER)/$$r; done

ci:
	@for r in $(REPOS); do echo "== $$r"; gh run list -R $(OWNER)/$$r -L 1; done

# The design prototypes are frozen: each runs, and mypy reports exactly the
# lines marked "# error:", no more, no fewer. This is what CI checks here.
PROTOTYPES := $(wildcard docs/design/*/*/check_types.py)
MYPY := uvx --python 3.14 mypy==2.4.0

check-prototypes:
	@for f in $(PROTOTYPES); do \
		d=$$(dirname $$f); echo "== $$d"; \
		(cd $$d && uv run --python 3.14 --no-project python check_types.py >/dev/null) || exit 1; \
		expected=$$(cd $$d && grep -Hn '# error:' *.py | cut -d: -f1,2 | sort); \
		actual=$$(cd $$d && $(MYPY) --strict . | grep ': error:' | cut -d: -f1,2 | sort); \
		if [ "$$expected" != "$$actual" ]; then \
			echo "mypy errors differ from the marks:"; \
			diff <(echo "$$expected") <(echo "$$actual"); exit 1; \
		fi; \
	done
