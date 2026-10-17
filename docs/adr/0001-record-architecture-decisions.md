# 0001. Record architecture decisions

- Status: Accepted
- Date: 2026-10-17
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **an ecosystem of independent repositories**, facing
> **decisions that span all of them and are made in conversation**, we decided
> for **an Architecture Decision Log in the meta repository** and against **a
> wiki or no formal log**, to achieve **reviewable and durable reasoning shared
> by every repository**, accepting **the overhead of writing records**.

## Context

The Ingots ecosystem is a set of independent repositories in the
[ak-ingots](https://github.com/ak-ingots) organization, held together by the
`ingots-libs` meta repository. Decisions such as target platforms, project
layout, tooling and versioning apply to every repository, are expensive to
reverse, and would otherwise be lost between sessions or re-litigated in each
repository.

## Decision drivers

- Decisions must survive the people and sessions that made them.
- Rejected alternatives must be visible, so they are not proposed again blindly.
- Decisions must evolve together with code and go through the same review.
- An ecosystem-wide decision must have exactly one home.

## Considered options

1. ADRs as Markdown files in the meta repository.
2. ADRs duplicated in every repository.
3. Wiki or external document.
4. No formal log; rely on code and commit messages.

## Decision

Option 1, using a lightweight MADR format ([template.md](template.md)):

- Ecosystem-wide decisions live in `ingots-libs/docs/adr/NNNN-kebab-title.md`;
  [README.md](README.md) holds the index. A decision that concerns a single
  repository lives in that repository's own `docs/adr/` and may reference
  these records.
- One decision per record, written in English, 1–2 screens long.
- Lifecycle: `Draft` → `Proposed` → `Accepted` → `Deprecated` /
  `Superseded by NNNN`; `Rejected` is kept, not deleted.
- While a record is `Draft`, its number and content may change freely. A number
  is frozen when the record becomes `Proposed`.
- Once `Accepted`, the substance is immutable. A change of mind is a new record
  that supersedes the old one; only typos and links may be edited in place.
- Record decisions that are expensive to reverse: contracts, guarantees,
  boundaries, platforms, technology and tooling choices. Long analysis goes to
  separate documents.

## Consequences

### Positive

- Every repository follows one set of written decisions instead of folklore.
- Reviewers and future contributors can see why, not only what.

### Negative

- Writing discipline is required; stale drafts must be pruned.
- A repository's reader has to follow a link to the meta repository.

## Links

- Michael Nygard, "Documenting Architecture Decisions" (2011).
- MADR: https://adr.github.io/madr/
