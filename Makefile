# Commands over every repository of the ecosystem (see repos.txt).
SHELL := /bin/bash
OWNER := ak-ingots
REPOS := $(shell grep -v '^\#' repos.txt)
ADDONS := $(filter ingot-%,$(REPOS))

.PHONY: help clone pull status check prs ci pins try-ingots check-prototypes

help:
	@echo "clone   clone missing repositories (gh, uses gh auth)"
	@echo "pull    fast-forward every repository"
	@echo "status  branch, local changes and divergence of every repository"
	@echo "check   make check (lint, test) everywhere, dependencies first"
	@echo "prs     open pull requests across the ecosystem (gh)"
	@echo "ci      last workflow run of every repository (gh)"
	@echo "pins    what main of every addon pins of ingots, and which are behind"
	@echo "try-ingots  the tests of the addons on INGOTS, the checkout by default"
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

# The pins of the last fetch of main: `git fetch` in a repository refreshes it.
# Fails when an addon is behind, see ADR 0008.
pins:
	@latest=$$(git -C ingots tag --sort=-v:refname | head -1 | sed 's/^v//'); \
	echo "ingots $$latest"; \
	behind=0; for r in $(ADDONS); do \
		pin=$$(git -C $$r show origin/main:pyproject.toml | grep -oE '"ingots[<>=][^"]*"' | tr -d '"'); \
		case "$$pin" in *">=$${latest%.*}."*) mark="";; *) mark=" <- behind"; behind=1;; esac; \
		printf '%-16s %s%s\n' "$$r" "$$pin" "$$mark"; \
	done; \
	exit $$behind

# The tests as checked out in each addon, on another ingots: an early warning,
# see ADR 0008. INGOTS='ingots==0.32.2' takes a published one.
INGOTS ?= $(CURDIR)/ingots

try-ingots:
	@failed=""; for r in $(ADDONS); do \
		echo "== $$r ($$(git -C $$r branch --show-current))"; \
		(cd $$r && uv run --quiet --with "$(INGOTS)" python -m unittest discover -s tests -t .) \
			|| failed="$$failed $$r"; \
	done; \
	if [ -n "$$failed" ]; then echo "failed:$$failed"; exit 1; fi

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
