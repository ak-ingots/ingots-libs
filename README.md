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
| [ingots](https://github.com/ak-ingots/ingots) | `ingots` (not published yet) | — | rewrite in progress: the PUER core, the runner and the command line, the settings of `ingots.defaults` |

A new package: create the repository in
[ak-ingots](https://github.com/ak-ingots), add it to `repos.txt` (after its
dependencies), to this table and to `llms.txt`. An addon is named
`ingot-<name>`, in the singular: one ingot, an extension of the `ingots`
framework, not a framework of its own.

## Ideas

Packages not started yet, kept here until they get a repository.

- `ingot-settings`: sources and formats for the settings of `ingots.defaults`
  beyond the standard library. First YAML files (a `YamlFormat` slot of the
  file loader, on PyYAML); later loaders for cloud secret managers. One
  package, every integration behind an extra of its own, so an application
  installs only what it uses: `pip install "ingot-settings[yaml,aws,gcp]"`.
  Each integration lives in its own module, the only one importing its
  dependency; the package imports none of them.

## Working with the ecosystem

```sh
git clone https://github.com/ak-ingots/ingots-libs.git
cd ingots-libs
make clone      # missing repositories, via gh
make check      # lint + test everywhere
make status     # what is changed or unpushed, across all repositories
```

Commits, pushes and releases are done in each repository separately.
