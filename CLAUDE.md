# CLAUDE.md

Guidance for Claude Code in the Ingots meta repository and every ecosystem
repository cloned next to it. Keep it under 200 lines; link to the ADRs and
READMEs instead of repeating them. Each package repository has its own
`CLAUDE.md` that works without this one; rules stated here for the whole
ecosystem are repeated there only when a package needs them in isolation.

## Layout

This repository tracks only its own files (`.gitignore` starts with `/*` and
whitelists them). Sibling directories listed in `repos.txt` are independent
git repositories; `make clone`, `pull`, `status`, `check`, `prs`, `ci` run
over all of them. Directories not in `repos.txt` (e.g. `ingots-current/`, a
clone of the previous implementation, or `designs/`) are local scratch.

## GitHub access

The organization is `ak-ingots`. gh and git authenticate with a dedicated
token exported as `GH_TOKEN` by this repository's `.envrc` (git-ignored). The
Bash tool does not load direnv, so run network commands as

```bash
direnv exec /home/bee/work/ingots-libs gh ...
direnv exec /home/bee/work/ingots-libs git push ...
```

git uses `gh auth git-credential`, so pushes pick the token up too. Never read
`.envrc` files or the token file.

## Commits

Never commit, amend, push, open a pull request, tag or rewrite history on
your own initiative. Prepare the change, show a summary and the proposed
message, and wait for an explicit approval of that commit; one approval does
not extend to the next. Never merge a pull request: the user does
(`gh pr merge` is denied). This holds in every repository of the ecosystem.

## History

- `main` and `release/X.Y` are protected in every repository by the ruleset
  "Protect main and release branches": no direct push, force push or
  deletion; changes land through pull requests only, squash-merged, keeping
  the history linear. Where a repository has CI, its checks must pass on a
  branch up to date with `main`.
- Every change goes on its own branch and pull request, one reviewable change
  each. The squash commit takes the PR title and description, so write them
  as the commit message, attribution included; keep the branch to one commit
  so the PR shows what will land.
- Before pushing a branch, rebase it onto the current `main` and run
  `make check`; pushing what CI will reject only wastes a run.
- After the user merges, switch to `main`, pull and delete the local branch.
- A new repository gets the same ruleset and merge settings: squash merging
  only, PR title and description as the commit, head branches deleted after
  merge.

## Ecosystem rules

Decided in [docs/adr](docs/adr/README.md); the essentials:

- Linux is the target, macOS a by-product, Windows unsupported (0002).
- Flat layout; a library is built and tested as a wheel outside the
  repository (0003).
- Composition by inheritance and typed slots (0004); addons ship contract
  tests run by every consumer (0005); design principles and their priority
  (0006); code layout and naming: member and module order, verbs for
  methods, `Base` for incomplete classes, prefixed mixin members (0007).
- Tooling: uv with `uv_build`, `make` as the entrypoint (`make check` runs
  every check, `make all` builds), stdlib `unittest`, black, flake8,
  `mypy --strict`. Test coverage is a check too: `make coverage` (coverage.py,
  `branch = true`, `fail_under = 99`, `if t.TYPE_CHECKING:` and
  `raise NotImplementedError` excluded) runs in `make check` and in CI; copy
  the setup from `ingots`.
- Documentation: the meta repository lives on GitHub only. Packages publish
  Sphinx docs on Read the Docs: `ingots` is the parent project
  (`https://ingots.readthedocs.io/`), every addon a subproject under it
  (`https://ingots.readthedocs.io/projects/<addon>/`), linking to the
  framework's API through `intersphinx_mapping`.
- Versioning: a static `version` in `pyproject.toml`, bumped with
  `uv version --bump`; tags are `vX.Y.Z`.
- A decision that spans repositories gets an ADR here (process in 0001):
  written in English, `Proposed` until the user accepts it.
