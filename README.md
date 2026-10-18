# ingots-libs

![Ingots logo](https://raw.githubusercontent.com/ak-ingots/logo-gen/main/final-pyramid@256.png)

Meta repository of the Ingots ecosystem: the catalogue of packages, the
principles they share, and commands over all of them. Package repositories
are cloned next to this file and stay independent: this repository ignores
them, their changes never show up here.

```
ingots-libs/          # this repository
├── repos.txt         # ecosystem repositories, dependencies first
├── Makefile          # clone / pull / status / check / prs / ci
├── llms.txt          # entry point for AI agents
├── docs/adr/         # ecosystem-wide architecture decisions
├── logo-gen/         # independent repositories, cloned by `make clone`
└── ingots/
```

Ecosystem-wide decisions are recorded in [docs/adr](docs/adr/README.md).

## Catalogue

| Repository | Distributions | Depends on | Status |
|---|---|---|---|
| [logo-gen](https://github.com/ak-ingots/logo-gen) | — (tool, not published) | — | done: the ecosystem logo |
| [ingots](https://github.com/ak-ingots/ingots) | `ingots` (not published yet) | — | rewrite started: empty package, dev automation |

A new package: create the repository in
[ak-ingots](https://github.com/ak-ingots), add it to `repos.txt` (after its
dependencies), to this table and to `llms.txt`.

## Working with the ecosystem

```sh
git clone https://github.com/ak-ingots/ingots-libs.git
cd ingots-libs
make clone      # missing repositories, via gh
make check      # lint + test everywhere
make status     # what is changed or unpushed, across all repositories
```

Commits, pushes and releases are done in each repository separately.
