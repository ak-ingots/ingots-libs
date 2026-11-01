# 0008. Move the addons onto a new ingots at once

- Status: Proposed
- Date: 2026-11-01
- Deciders: TBD
- Supersedes / Superseded by: —

> In the context of **addons pinned to a minor version of ingots**, facing
> **applications that cannot combine addons on different minors**, we decided
> for **moving every addon right after each minor, in its own pull request and
> release** and against **moving an addon with its next feature**, to achieve
> **addons that can always be installed together**, accepting **a release of
> every addon per minor of ingots**.

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

Option 3:

1. A patch release of ingots needs nothing: the pins cover it.
2. Before a minor release, `make try-ingots` runs the tests of the addons on
   the `main` of ingots. A break is fixed or recorded in the changelog of ingots
   before the release.
3. Right after the release, each addon gets a pull request "Move on to ingots
   X.Y" and a release of its own, a minor version: an application on the older
   ingots cannot take it. The move is not combined with a feature.
4. The order is that of `repos.txt`: an addon comes after the addons it depends
   on, an optional extra included.
5. The pin and the lock file name the version, and a news fragment records the
   move. `CLAUDE.md`, the README and the canary test do not repeat the number.
6. `make pins` shows what `main` of every addon pins, and fails when one is
   behind. A new minor of ingots does not wait for the addons: a red run of the
   automation is the signal to release them.

## Consequences

### Positive

- Ingots is not held back by its slowest addon.
- The rollout is mechanical, so it can be automated later.

### Negative

- A release of every addon per minor of ingots, even with no other change.
- `make try-ingots` runs what the local checkouts hold, without the services
  of integration tests unless they are up: it is an early warning, and the CI
  of each pull request is still the check.

### Open questions

- What to automate as addons multiply: nothing runs `make pins` and
  `make try-ingots` on a schedule yet, so the signal is manual until a job does;
  then a workflow opening the pull requests of a move.

## Links

- [ADR 0005](0005-addons-ship-contract-tests.md): the contract tests a move runs.
