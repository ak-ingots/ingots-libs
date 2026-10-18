# 0005. Addons ship contract tests; consumers run them

- Status: Accepted
- Date: 2026-10-18
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **applications and addons composed from other addons**,
> facing **customizations that can silently break the behaviour an addon
> guarantees**, we decided for **contract tests shipped in every addon's
> distribution and run by every consumer against its own composed project**
> and against **tests kept only in the addon's repository, or its whole test
> suite shipped**, to achieve **a consumer that learns from its own checks that
> it broke an addon**, accepting **contract tests as public API to design,
> version and keep fast**.

## Context

Under [0004](0004-static-composition-with-typed-slots.md) a consumer (an
application, or an addon built from other addons) customizes an addon by
subclassing its classes and narrowing its slots. mypy and the slots check
catch type and structure errors, but not behaviour: an override that forgets
`super()`, changes a result, or breaks an invariant passes both. An addon's
own tests run on the addon's own project and stay green; the breakage appears
only in the consumer's composed project.

This is the Liskov substitution principle applied to composition: wherever an
addon expects its project, units and entities, the consumer's subclasses must
behave as the addon guarantees. A guarantee that is checked must be checked
on the consumer's classes, by the addon's own tests.

Shipping tests in the distribution was tried before (`ingots/tests`, dropped
in 2025) and found of no use: the shipped tests ran on the library's own
classes, re-checking what the library's CI had already checked. The
difference here is what the tests run on.

## Decision drivers

- A consumer breaking an addon's guarantee fails its own `make check`.
- The addon's author defines its guarantees; consumers don't re-derive them.
- One procedure for every consumer, whatever addons it combines.
- No test-only dependencies or cost for those who only use an addon.

## Considered options

1. Tests stay in the addon's repository; consumers write their own
   integration tests.
2. The addon ships its whole test suite.
3. The addon ships contract tests, parametrized by the project they run on;
   consumers run the contracts of all addons they combine.

## Decision

Option 3.

- An addon's tests are of two kinds:
  - internal tests in `tests/`: implementation details, fixtures, edge
    cases; not shipped;
  - contract tests in the package (`<package>/contracts`): the addon's
    behavioural guarantees, written against its public API only and shipped
    in the wheel.
- A contract test case does not create a project itself: it receives one from
  a factory supplied by whoever runs it. The addon runs its contracts on its
  own project in its own `make check`, and so through the built wheel
  ([0003](0003-flat-layout-and-mandatory-library-build.md)).
- A consumer runs the contracts of every addon its project is composed of on
  its own project. `ingots` provides the procedure: it collects the contracts
  of the addons found in the project class's MRO, binds them to the
  consumer's project factory, and exposes them through the standard
  `unittest` `load_tests` protocol, so `python -m unittest` and `make check`
  run them with no extra tooling. A consumer that is itself an addon also
  ships contracts and runs its dependencies' ones.
- Contract tests use only the standard library and the addon's runtime
  dependencies, are not imported at runtime, and are fast enough for every
  `make check`.
- Contracts are public API: removing or tightening a guarantee is a breaking
  change and follows the versioning scheme; adding one is not.

## Consequences

### Positive

- A broken guarantee is found by the consumer that broke it, in its own
  checks, before release.
- A consumer combining addons gets their checks for free: one hook supplying
  its project.
- Contracts document what an addon guarantees, executably.

### Negative

- Addon authors design and maintain a second, public test API.
- A contract that needs external resources (a database, a broker) depends on
  the consumer's project being able to provide them in tests.
- The consumer's checks grow with every addon it combines.

### Open questions

- How a contract declares what it needs from the project (settings, external
  resources), and how a consumer skips a contract it cannot satisfy, with the
  reason shown.
- How contracts are associated with an addon's project class (an attribute,
  a naming convention).

## Links

- [0003](0003-flat-layout-and-mandatory-library-build.md): libraries are
  tested as built wheels.
- [0004](0004-static-composition-with-typed-slots.md): composition by
  inheritance and slots.
- Liskov, Wing, "A Behavioral Notion of Subtyping" (1994).
