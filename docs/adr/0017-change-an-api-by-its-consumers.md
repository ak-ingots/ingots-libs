# 0017. Change an API by its consumers: one release, or steps

- Status: Proposed
- Domains: process, design, grpc
- Date: 2026-11-23
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **an addon whose public API, its contract of gRPC and the
> classes of Python its consumers write against, changes under consumers**, facing
> **a change that breaks them in one release, even where the wire stays the same**,
> we decided for **one breaking release while no consumer is out of the
> ecosystem, the wire kept in three steps for clients of gRPC deployed apart, and
> steps for the consumers of a library, three to extend an API, five to swap one
> under the same names**, and against **steps for every change, and versions of
> classes kept for good**, to achieve **consumers moving on at their own pace where
> they exist, at the cost a rehearsal measured**, accepting **temporary names, two
> breaks for the laggards and six times the diff for a swap**.

## Context

ingot-auth moved its contract from `ingot_auth.<path>.v1` to
`ingot_auth.api.<path>.v1` ([ADR 0011](0011-mirror-the-packages-of-grpc-contracts.md),
item 5), rehearsed as releases would take it, without the tags, its examples the
consumers (ingot-auth#98 to #102). What it showed:

- The wire is not the whole API. A message of Python belongs to the package of its
  `.proto`: a stub of the new package takes no message of the old one, though their
  bytes are the same. The bindings of gRPC, a stub on a client and a servicer on a
  server, fix the types their consumers touch: a binding is either old or new.
- So a renamed package cannot slip under the names consumers use: the new one lives
  beside under other names first. Names kept in `__all__` are imported: a suffix
  `New` or `V2` would be versions of classes, there for good.
- ingot-grpcio forbids a service under two attributes, so the old names of a binding
  alias the new ones by a descriptor of their own (`AuthGrpcServiceAlias` in the
  rehearsal).
- `buf breaking` on `WIRE_JSON` alone sees no package, service or RPC deleted:
  every old name of gRPC went unnoticed. `PACKAGE_NO_DELETE`,
  `PACKAGE_SERVICE_NO_DELETE` and `RPC_NO_DELETE` catch it.

What it cost, by `git diff` (the handwritten code; the tokens of a diff, its
characters by 4; `_pb2*` apart):

| Step | Pull request | Files | Handwritten | Generated | Diff, tokens | Breaks |
|---|---|---|---|---|---|---|
| 1 add beside | #98 | 171 | +5 202 / −382 | +8 317 | ~58k | no |
| 2 consumers to `_temp` | #99 | 11 | +39 / −36 | — | ~2.5k | no |
| 3 remove the old | #100 | 170 | +291 / −4 617 | −8 317 | ~56k | yes: the old names of gRPC, `ingot_auth.<path>.v1`, `contract` |
| 4 consumers back | #101 | 6 | +16 / −17 | — | ~1.3k | no |
| 5 remove `_temp` | #102 | 43 | +909 / −1 361 | — | ~33k | yes: `*_temp`, `*Temp` |
| The five | | 401 | +6 457 / −6 413 | ±8 317 | ~151k | twice |
| One pull request, the same result | | 214, 105 renamed | +753 / −709 | ±804 | ~24k | once |

Beside the five, the rehearsal took two approaches dropped on the way, a move
under shims and a copy of the transports suffixed `New`, and five runs of
`make check` with Docker; the tokens of the work were many times those of the
diffs.

So the steps do not remove a break, they defer it and give a window: each removal
breaks whoever has not moved, and a swap removes twice, the old and the
temporary. The consumers changed their code twice, +55 / −53 in the examples,
for once (+39 / −36) in one pull request; the cost was six times the diff and
nine times its handwritten lines, five reviews, five runs of CI. What the window
gave: a server serving the old names of gRPC and the new ones at once, of worth
where the clients deploy apart from the server, mobile applications, services of
others; to the consumers of a library of Python, only "move on when you will".

## Decision drivers

- A consumer moves on by changing its own code, in a release of its own, never
  broken by the release of the addon.
- No version lives in the names of classes for good.
- Each step is checked by the consumers' code, the examples first.

## Considered options

1. One breaking release: the consumers move in the release that breaks them.
2. Versions in the names, `*V2`, kept.
3. Steps, the new beside the old, the old names reused once the old goes.

## Decision

Which way a change goes, by its consumers:

- **No consumer out of the ecosystem**, the pre-alpha: one breaking pull request
  and release (option 1), the ecosystem moved along the tree
  ([ADR 0008](0008-move-dependents-along-the-tree.md)). The rule until the first
  consumer out of it.
- **Clients of gRPC deployed apart from the server**: the wire kept in three
  steps, the API of Python broken once. The server serves the old names of gRPC by
  the handlers of the new ones, a generic handler of each old service, no
  second copy of the code; the clients move on; the old names go.
- **Consumers of the library out of the ecosystem**: option 3, three steps to
  extend an API, five to swap one under the same names.

Option 3, where it is taken: a step is a release; a rehearsal or a pre-alpha may
take it as a pull request.

**Extend an API**, the new under new names, an RPC, a service, a `v2`: three steps.

1. Add the new beside the old; the old deprecated (the changelog, the docs).
2. The consumers move on to the new.
3. Remove the old: the release breaks nothing that moved on.

**Swap an API**, the new under the names of the old, a package renamed, a type of
a message changed: five steps.

1. Add the new beside the old under temporary names, `*_temp` attributes and
   `*Temp` classes, which say they go; the old deprecated, served as it was.
2. The consumers move on to the temporary names.
3. Remove the old; its names alias the temporary ones.
4. The consumers move back to the names of the old.
5. Remove the temporary names and their aliases.

Where a step removes what the contract had, the old names of gRPC, `buf breaking`
fails, on purpose: that pull request alone skips it, by `BREAKING=skip` in its CI,
and its changelog says what is removed. `buf.yaml` of a contract adds
`PACKAGE_NO_DELETE`, `PACKAGE_SERVICE_NO_DELETE` and `RPC_NO_DELETE` to
`WIRE_JSON`.

## Consequences

### Positive

- A consumer is never broken by a release it takes; it moves on in its own.
- The steps are mechanical: the examples prove each.

### Negative

- A swap is five releases and two moves of each consumer, two breaks for those
  who lag; the code of the old and the new lives twice for a step: six times the
  diff of one pull request, in the rehearsal.

### Open questions

- The alias of a service of a binding belongs to ingot-grpcio, for the next swap.

## Links

- [ADR 0011](0011-mirror-the-packages-of-grpc-contracts.md): the API in `api/`.
- ingot-auth#98 to #102: the rehearsal.
