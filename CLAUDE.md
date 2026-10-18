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

Never commit, amend, push, tag or rewrite history on your own initiative.
Prepare the change, show a summary and the proposed message, and wait for an
explicit approval of that commit; one approval does not extend to the next.
This holds in every repository of the ecosystem.

## History

- Linear history only: no merge commits; main moves by `--ff-only`.
- Development may take many small commits; what lands on `main` is squashed
  into commits that each bring one reviewable change, readable from its diff.
- While only the user and Claude work on a repository, work goes to `main`
  directly, without branches or pull requests; the same rules apply. Run
  `make check` before pushing: on a direct push `cl-check` in CI compares
  `main` with itself and passes, so the news fragment is checked locally only.

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
  `mypy --strict`.
- Documentation: the meta repository lives on GitHub only. Packages publish
  Sphinx docs on Read the Docs: `ingots` is the parent project
  (`https://ingots.readthedocs.io/`), every addon a subproject under it
  (`https://ingots.readthedocs.io/projects/<addon>/`), linking to the
  framework's API through `intersphinx_mapping`.
- Versioning: a static `version` in `pyproject.toml`, bumped with
  `uv version --bump`; tags are `vX.Y.Z`.
- A decision that spans repositories gets an ADR here (process in 0001):
  written in English, `Proposed` until the user accepts it.
