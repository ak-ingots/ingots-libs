# ingots-libs

![Ingots logo](https://raw.githubusercontent.com/ak-ingots/logo-gen/main/final-pyramid@256.png)

Meta repository of the Ingots ecosystem: the catalogue of packages, the
principles they share, and commands over all of them. Package repositories
are cloned next to this file and stay independent: this repository ignores
them, their changes never show up here.

```
ingots-libs/          # this repository
├── repos.txt         # ecosystem repositories, dependencies first
├── Makefile          # clone / pull / status / check / prs / ci / dep-*
├── scripts/          # the routine: pr / ci / merged / release / tag
├── hooks/            # git hooks of every repository, set by `make hooks`
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
| [ingots](https://github.com/ak-ingots/ingots) | [`ingots`](https://pypi.org/project/ingots/) 0.35.0 | — | alpha: the PUER core, each entity knowing its place, its parents and its full name, the runner and the command line, the components, the operations, their permissions bound by the slots of their units, and their groups run together, the settings and the logging of `ingots.defaults`, the project of a test case as a fixture of `ingots.testing` |
| [ingot-settings](https://github.com/ak-ingots/ingot-settings) | [`ingot-settings`](https://pypi.org/project/ingot-settings/) 0.5.0 | `ingots` | pre-alpha: YAML files; next, loaders for cloud secret managers |
| [ingot-grpcio](https://github.com/ak-ingots/ingot-grpcio) | [`ingot-grpcio`](https://pypi.org/project/ingot-grpcio/) 0.13.0 | `ingots` | pre-alpha: the servers, the servicers running operations for their callers, the clients, the errors and the export of the services of grpcio |
| [ingot-pymongo](https://github.com/ak-ingots/ingot-pymongo) | [`ingot-pymongo`](https://pypi.org/project/ingot-pymongo/) 0.14.0 | `ingots` | pre-alpha: the clients of MongoDB servers, as components, on PyMongo |
| [ingot-redis](https://github.com/ak-ingots/ingot-redis) | [`ingot-redis`](https://pypi.org/project/ingot-redis/) 0.2.0 | `ingots` | pre-alpha: the clients of Redis servers, as components, on redis-py |
| [ingot-mail](https://github.com/ak-ingots/ingot-mail) | [`ingot-mail`](https://pypi.org/project/ingot-mail/) 0.2.0 | `ingots` | pre-alpha, for the mail of applications: the mail of plain text with its headers, the mailer, its contract, the mailer in memory and the mailer of SMTP on aiosmtplib, STARTTLS by default; next, a mail of HTML, copies, attachments |
| [ingot-auth](https://github.com/ak-ingots/ingot-auth) | [`ingot-auth`](https://pypi.org/project/ingot-auth/) 0.6.0 | `ingots`, `ingot-mail` | pre-alpha, for the sign-up, the sign-in and the sessions of the users of an application: the sign-up and the sign-in by methods in steps, a nickname and a password, an email and a code sent in the background by the mailer of ingot-mail; the policies, the sessions, fixed or sliding, listed and revoked by their users, the place of each derived from its IP, the record of the sign-ins, the sign-out, every session of a profile revoked by an operator, the expired ones swept, the groups of the users in the units of their domains, the registries of the profiles and the sessions, the values of a profile, the profile of the caller and its hash in every reply, the metadata, the activity log of every change of state, read by the auditors; the storage in memory and in MongoDB, the cache in memory and in Redis, gRPC; [documented](https://ingots.readthedocs.io/projects/ingot-auth/); next, the limit of the sessions |

A new package: create the repository in
[ak-ingots](https://github.com/ak-ingots), add it to `repos.txt` (after its
dependencies), to this table and to `llms.txt`. An addon is named
`ingot-<name>`, in the singular: one ingot, an extension of the `ingots`
framework, not a framework of its own. The name is what the code of its
user is written against: a library the addon integrates, whose API the
user writes to (`ingot-grpcio`, `ingot-pymongo`), or the domain of an
abstraction of the addon's own (`ingot-settings`, `ingot-mail`). A name
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
make check      # lint + test everywhere, with the Buf CLI the ecosystem pins
make status     # what is changed or unpushed, across all repositories
```

Commits, pushes and releases are done in each repository separately.
