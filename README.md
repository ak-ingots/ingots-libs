# ingots-libs

Meta repository of the Ingots ecosystem: the catalogue of packages, the
principles they share, and commands over all of them. Package repositories
are cloned next to this file and stay independent: this repository ignores
them, their changes never show up here.

```
ingots-libs/          # this repository
├── repos.txt         # ecosystem repositories, dependencies first
├── Makefile          # clone / pull / status / all / prs / ci
├── llms.txt          # entry point for AI agents
└── <repo>/           # independent repositories, cloned by `make clone`
```

## Catalogue

| Repository | Distributions | Depends on | Status |
|---|---|---|---|

A new package: create the repository in
[ak-ingots](https://github.com/ak-ingots), add it to `repos.txt` (after its
dependencies), to this table and to `llms.txt`.

## Working with the ecosystem

```sh
git clone https://github.com/ak-ingots/ingots-libs.git
cd ingots-libs
make clone      # missing repositories, via gh
make all        # gen + lint + test everywhere
make status     # what is changed or unpushed, across all repositories
```

Commits, pushes and releases are done in each repository separately.
