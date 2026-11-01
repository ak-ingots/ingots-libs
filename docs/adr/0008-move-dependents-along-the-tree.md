# 0008. Move the dependents of a package along the tree

- Status: Accepted
- Date: 2026-11-01
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **packages pinned to a minor version of what they depend
> on**, facing **applications that cannot combine addons on different minors**,
> we decided for **moving the dependents along the tree, signalled by the release
> of each package, each in its own pull request and release** and against
> **moving an addon with its next feature**, to achieve **addons that can always
> be installed together**, accepting **a release of every dependent per minor**.

## Context

Before 1.0 a minor version of ingots may break its addons, so each pins one:
`ingots>=0.32.2,<0.33`. Two addons on different minors cannot be installed
together, and an application learns that only when it installs them.

For 0.31 the addons could carry the move with their first feature. No feature
came for ingot-sql, which stayed on 0.30 while ingots reached 0.32, and
ingot-grpcio on 0.31 blocked the extra `grpcio` of ingot-auth on 0.32. Moving
on took no change of the code in any of them, only of the places naming the
version.

## Decision drivers

- Any addons of the ecosystem install together.
- A break is found while it can still be fixed in ingots.
- The work per addon stays small: there will be many of them.

## Considered options

1. Move an addon with its next feature, as for 0.31.
2. No upper bound on ingots: an addon claims a compatibility nobody tested.
3. Move every addon right after each minor.

## Decision

Option 3, along the tree of the ecosystem: a package pins the minor versions of
what it depends on, ingots or another addon, and the rules hold for each.

1. The tree is read from the `pyproject.toml` of the repositories, extras
   included: `make dep-tree`. No list of it is kept by hand.
2. A patch release needs nothing: the pins cover it.
3. The `release` workflow of every package calls the reusable workflow
   `dependents` of this repository, with no dependents yet as well: the calls are
   there when the first one comes. `dep-try` runs the tests of everything
   depending on the package, through others too, on its build, in a rehearsal as
   well, so that a break is seen before the release reaches PyPI. `dep-behind`
   runs after the release and fails when a direct dependent does not take it.
4. Neither holds the release back: a package does not wait for its dependents.
   A red `dep-behind` is the signal to move them.
5. Each dependent gets a pull request "Move on to X Y.Z" and a release of its
   own, a minor version: an application on the older package cannot take it. The
   move is not combined with a feature. A package moves once, after all it
   depends on has moved and been released: `make dep-next` names who can go.
6. The pin and the lock file name the version, and a news fragment records the
   move. `CLAUDE.md`, the README and the canary test do not repeat the number.

## Consequences

### Positive

- Ingots is not held back by its slowest addon.
- The rollout is mechanical, so it can be automated later.

### Negative

- A release of every addon per minor of ingots, even with no other change.
- `make dep-try` runs without the services of integration tests unless they
  are up: it is an early warning, and the CI of each pull request is still the
  check.
- A release of a minor ends with a red run by design, until the dependents move.
- The release of every package depends on `main` of this repository, its
  workflow and its targets. It reads them without a token only as long as this
  repository is public. The jobs get no right to publish.

### Open questions

- What to automate as addons multiply: a workflow opening the pull requests of
  a move. The template of a new addon could carry the calls from the start.

## Links

- [ADR 0005](0005-addons-ship-contract-tests.md): the contract tests a move runs.
