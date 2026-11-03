# Commands over every repository of the ecosystem (see repos.txt).
SHELL := /bin/bash
OWNER := ak-ingots
REPOS := $(shell grep -v '^\#' repos.txt)
DEPENDENTS := uv run --quiet --python 3.14 --no-project --with packaging python .github/scripts/dependents.py

.PHONY: help clone pull status check prs ci dep-tree dep-behind dep-next dep-try check-prototypes check-prototype

help:
	@echo "clone   clone missing repositories (gh, uses gh auth)"
	@echo "pull    fast-forward every repository"
	@echo "status  branch, local changes and divergence of every repository"
	@echo "check   make check (lint, test) everywhere, dependencies first"
	@echo "prs     open pull requests across the ecosystem (gh)"
	@echo "ci      last workflow run of every repository (gh)"
	@echo "dep-tree    who depends on whom in the ecosystem"
	@echo "dep-behind  who does not take the latest releases, of OF alone if given; fails then"
	@echo "dep-next    what can move or be released right now"
	@echo "dep-try     the tests of what depends on OF on WITH, its checkout by default"
	@echo "check-prototypes  run the design prototypes, compare mypy with their marks"
	@echo "check-prototype   the same for one, P=docs/design/<topic>/<concept>"

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

# From the last fetch of main of each repository: `git fetch` refreshes it. See
# ADR 0008. OF=ingot-grpcio asks about one package, WITH='ingots==0.32.2' tries
# a published version.
OF ?=
WITH ?= $(CURDIR)/$(OF)

dep-tree:
	@$(DEPENDENTS) tree

dep-behind:
	@$(DEPENDENTS) behind $(OF)

dep-next:
	@$(DEPENDENTS) next

dep-try:
	@test -n "$(OF)" || { echo "OF=<package> is required"; exit 1; }
	@failed=""; for r in $$($(DEPENDENTS) list $(OF)); do \
		echo "== $$r ($$(git -C $$r branch --show-current))"; \
		(cd $$r && uv run --quiet --with "$(WITH)" python -m unittest discover -s tests -t .) \
			|| failed="$$failed $$r"; \
	done; \
	if [ -n "$$failed" ]; then echo "failed:$$failed"; exit 1; fi

# The design prototypes are frozen: each runs, and mypy reports exactly the
# lines marked "# error:", no more, no fewer. This is what CI checks here.
PROTOTYPES := $(wildcard docs/design/*/*/check_types.py)
MYPY := uvx --python 3.14 mypy==2.4.0

check-prototypes:
	@for f in $(PROTOTYPES); do \
		$(MAKE) --no-print-directory check-prototype P=$$(dirname $$f) || exit 1; \
	done

# One prototype, P its directory or its check_types.py.
check-prototype:
	@if [ -z "$(P)" ]; then \
		echo "usage: make check-prototype P=docs/design/<topic>/<concept>"; exit 1; \
	fi
	@d=$(P); d=$${d%/}; d=$${d%/check_types.py}; echo "== $$d"; \
	[ -f $$d/check_types.py ] || { echo "no $$d/check_types.py"; exit 1; }; \
	(cd $$d && uv run --python 3.14 --no-project python check_types.py >/dev/null) || exit 1; \
	expected=$$(cd $$d && grep -Hn '# error:' *.py | cut -d: -f1,2 | sort); \
	actual=$$(cd $$d && $(MYPY) --strict . | grep ': error:' | cut -d: -f1,2 | sort); \
	if [ "$$expected" != "$$actual" ]; then \
		echo "mypy errors differ from the marks:"; \
		diff <(echo "$$expected") <(echo "$$actual"); exit 1; \
	fi
