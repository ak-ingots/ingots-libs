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
| [ingots](https://github.com/ak-ingots/ingots) | [`ingots`](https://pypi.org/project/ingots/) 0.30.1 | — | alpha: the PUER core, the runner and the command line, the components, the settings and the logging of `ingots.defaults` |
| [ingot-settings](https://github.com/ak-ingots/ingot-settings) | [`ingot-settings`](https://pypi.org/project/ingot-settings/) 0.1.0 | `ingots` | the skeleton of the addon; next, YAML files (0.2.0) |
| [ingot-grpcio](https://github.com/ak-ingots/ingot-grpcio) | [`ingot-grpcio`](https://pypi.org/project/ingot-grpcio/) 0.9.0 | `ingots` | the skeleton of the addon integrating grpcio; next, its servers and clients |
| [ingot-pymongo](https://github.com/ak-ingots/ingot-pymongo) | [`ingot-pymongo`](https://pypi.org/project/ingot-pymongo/) 0.10.0 | `ingots` | the skeleton of the addon integrating PyMongo; next, the clients of MongoDB servers |
| [ingot-sql](https://github.com/ak-ingots/ingot-sql) | [`ingot-sql`](https://pypi.org/project/ingot-sql/) 0.7.0 | `ingots` | the skeleton of the addon for SQL databases; next, typed tables, typical queries and raw SQL |

A new package: create the repository in
[ak-ingots](https://github.com/ak-ingots), add it to `repos.txt` (after its
dependencies), to this table and to `llms.txt`. An addon is named
`ingot-<name>`, in the singular: one ingot, an extension of the `ingots`
framework, not a framework of its own. The name is what the code of its
user is written against: a library the addon integrates, whose API the
user writes to (`ingot-grpcio`, `ingot-pymongo`), or the domain of an
abstraction of the addon's own (`ingot-settings`, `ingot-sql`). A name
already on the package indexes continues above its last version there,
as a version is published only once.

## Ideas

Packages not started yet, kept here until they get a repository. None at the
moment: `ingot-settings`, the first idea, has its repository.

## Working with the ecosystem

```sh
git clone https://github.com/ak-ingots/ingots-libs.git
cd ingots-libs
make clone      # missing repositories, via gh
make check      # lint + test everywhere
make status     # what is changed or unpushed, across all repositories
```

Commits, pushes and releases are done in each repository separately.
