# 0016. Run the feature addons as applications in examples

- Status: Proposed
- Domains: process, tooling
- Date: 2026-11-17
- Deciders: TBD
- Supersedes / Superseded by: —

> In the context of **addons proven by unit, contract and integration tests
> only**, facing **no application composing them for real**, we decided for
> **examples of applications in the repository of the feature addon they
> show, and in the meta repository only those joining several feature
> addons, each run end to end by scenarios of a client**, and against **one
> demo of everything** and **every example in the meta repository**, to
> achieve **the composition of an addon checked as an application meets it,
> on the code of the same commit**, accepting **a CI of Docker in the
> feature addons**.

## Context

Every addon is tested alone: its units, its contracts, its storage against
a real server. None is run as an application runs it: an `AppProject`
joining `AuthProject`, `GrpcProject`, `MongoDbProject`, `RedisProject`,
configured by the environment, two processes sharing a cache, a client
calling it over the network. What breaks there, a slot of two bases, a
config of two addons, a release of one not taking another, nothing finds
today.

The addons are of two kinds. An infrastructure addon gives a transport, a
storage, a cache, a mailer: `ingot-grpcio`, `ingot-pymongo`, `ingot-redis`,
`ingot-mail`. A feature addon gives a domain and takes those as its
extras: `ingot-auth` already takes five. An application of a feature addon
is that addon with its infrastructure; the feature addons to come, the
profiles, the leaderboards, depend on the auth and meet in applications of
several.

One demo of every addon grows into a product of its own and needs the
addons it has not yet; examples kept apart from the addon they show find
its breakage only after its release.

## Decision drivers

- An addon is proven as an application composes it, before its release.
- An example shows one kind of application, small enough to read.
- The checks are those of the ecosystem: `make`, `unittest`, Docker for
  the servers; no other runner.

## Considered options

1. One demo application of every addon, in the meta repository.
2. Every example in the meta repository, pinning the releases.
3. Examples in the repository of the feature addon they show; in the meta
   repository those of several feature addons.

## Decision

Option 3.

- **An application of a feature addon**: `examples/<name>/` of the
  repository of that addon, named by the kind of application, `game`,
  `web`. It takes the addon of the same commit and the infrastructure the
  addon takes as extras:
  - its `docker-compose.yml` runs the application and its servers, the
    application as an image installing the wheel the addon builds,
    configured by the environment;
  - its scenarios are `unittest` cases of a client of the application,
    the end user's calls in order, against what `docker-compose.yml`
    runs; their shared steps are plain functions and mixins, called by
    name;
  - a job of the CI of the addon runs them, required by its ruleset; so a
    release of an infrastructure addon runs them too, as `dep-try` and the
    dependents of ADR 0008 run the checks of the feature addon;
  - its code is checked by the lint of the addon and stays out of its
    coverage and its wheel;
  - it is the first consumer of the starter of the addon for its kind
    of application: an extra named by the kind, `ingot-auth[game]`, the
    stack the image installs, then the composition the example shares
    with any such application, moved into the package under that extra.
- **An application of several feature addons**: `examples/<name>/` of the
  meta repository, built when two feature addons first meet. It pins the
  releases on PyPI as an application does, runs as above, and its CI job
  runs on its change and after a release of an addon it pins.
- An infrastructure addon needs no example: the feature addons run it.

## Consequences

### Positive

- A change that breaks an application is found in its own pull request,
  not by the first application of a user.
- The starters of a feature addon grow out of its examples: the
  composition an application writes today is what its starter writes for
  it tomorrow.
- The design of a feature has a living consumer next to its prototype.

### Negative

- A CI of Docker in each feature addon, a job slower than its tests.
- An extra named by a kind of application stays: removing it breaks the
  applications installing it.
- The examples of the meta repository move their pins on each release.

### Open questions

- Whether an example runs on a schedule as well, to see a server image
  change.

## Links

- [ADR 0008](0008-move-dependents-along-the-tree.md): the tree of the
  dependents.
- [ADR 0012](0012-design-a-feature-before-building-it.md): an example of an
  application is designed first, in the design of the addon it shows,
  `docs/design/<addon>/examples/<application>.md`, one of several
  feature addons in `docs/design/<application>/`.
- [The design of the game](../design/auth/examples/game.md): the first
  one, in ingot-auth.
