# 0006. Design principles: SOLID, DRY, KISS, YAGNI, the Zen of Python

- Status: Accepted
- Date: 2026-10-18
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **code written across many repositories, by people and AI
> agents, over many sessions**, facing **reviews that otherwise argue taste and
> principles that conflict with each other**, we decided for **the commonly
> accepted design principles as review criteria, with an explicit priority and
> stated deviations** and against **unstated conventions or principles applied
> as dogma**, to achieve **a shared vocabulary for design decisions and
> predictable trade-offs**, accepting **that every deviation has to be argued
> and written down**.

## Context

Ingots code is written by different authors, including AI agents that start
each session without memory of the previous one. Without a stated baseline,
the same design question is decided differently in each repository, and a
review comment is a matter of taste.

The principles themselves pull in different directions. [0004](0004-static-composition-with-typed-slots.md)
already chose explicitness over DRY: one short class per level and explicit
join classes, so that mypy sees the composed types. Such choices must follow
a known priority rather than be made case by case.

## Decision drivers

- One vocabulary for design in code review: a request names the principle.
- Predictable resolution when principles conflict.
- No dogma: a principle serves the code, not the other way round.

## Considered options

1. No stated principles; rely on each author's judgement.
2. Adopt the principles as strict rules.
3. Adopt them as defaults with a priority order and written deviations.

## Decision

Option 3.

- The baseline is the Zen of Python (PEP 20), PEP 8 (enforced by the
  formatter and the linter), SOLID, DRY, KISS and YAGNI.
- How they apply to Ingots:
  - **Single responsibility:** a unit groups, an entity does one job; a class
    that needs "and" in its docstring is split.
  - **Open/closed:** an addon is extended by subclassing and narrowing its
    slots, never by editing it ([0004](0004-static-composition-with-typed-slots.md)).
  - **Liskov substitution:** a subclass keeps every guarantee of its base;
    contract tests check it ([0005](0005-addons-ship-contract-tests.md)).
  - **Interface segregation:** depend on the narrowest type that serves: an
    addon's entity narrows `project` to its own addon's project, not the
    application's; a consumer of a capability takes a `typing.Protocol`.
  - **Dependency inversion:** code depends on the classes declared in slots
    and protocols; the concrete classes are chosen where the project is
    composed.
  - **DRY** is about knowledge, not similar-looking code: one fact has one
    home. Repetition that carries types (per-level classes, join classes) is
    accepted; similar code is merged at the third occurrence, not the second.
  - **KISS, YAGNI:** no abstraction, option or extension point without a
    current user; prototype before generalizing.
- On conflict the priority is: correctness, then explicitness and
  readability (what mypy, the IDE and a reader see), then simplicity, then
  DRY.
- A deviation is allowed when argued: a comment where it happens, or an ADR
  when it spans repositories.

## Consequences

### Positive

- Review comments point to a principle and its priority instead of taste.
- New authors and agents get the expected design style from one page.

### Negative

- Principles are interpreted; a written priority narrows disputes but does
  not end them.
- Writing down deviations is extra work.

## Links

- PEP 20, "The Zen of Python"; PEP 8, "Style Guide for Python Code".
- R. C. Martin, "Design Principles and Design Patterns" (2000).
- A. Hunt, D. Thomas, "The Pragmatic Programmer" (DRY).
