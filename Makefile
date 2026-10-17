# Commands over every repository of the ecosystem (see repos.txt).
OWNER := ak-ingots
REPOS := $(shell grep -v '^\#' repos.txt)

.PHONY: help clone pull status check prs ci

help:
	@echo "clone   clone missing repositories (gh, uses gh auth)"
	@echo "pull    fast-forward every repository"
	@echo "status  branch, local changes and divergence of every repository"
	@echo "check   make check (lint, test) everywhere, dependencies first"
	@echo "prs     open pull requests across the ecosystem (gh)"
	@echo "ci      last workflow run of every repository (gh)"

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
