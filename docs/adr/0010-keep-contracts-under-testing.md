# 0010. Keep the contracts of a package under testing

- Status: Accepted
- Domains: design
- Date: 2026-11-01
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: supersedes the location in 0005, the rest of it stands

> In the context of **packages shipping contract tests**, facing **a directory
> `contracts` that sits among the business domains of a package**, we decided for
> **`<package>/testing/contracts`** and against **`<package>/contracts`**, to achieve
> **room for a domain of contracts and a location telling what it is for**, accepting
> **a longer import path**.

## Context

[ADR 0005](0005-addons-ship-contract-tests.md) puts contract tests into
`<package>/contracts`. The top level of a package holds its domains, and a package
may well have a domain of contracts of its own: agreements, say, in a billing addon.
The directory of the tests would take its name. No package ships contracts yet, and
the procedure of `ingots` collecting them does not exist, so moving costs nothing now.

## Decision drivers

- The top level of a package belongs to its domains.
- What nothing needs at runtime says so by where it lies.

## Considered options

1. `<package>/contracts`, as ADR 0005 has it.
2. `<package>/testing/contracts`.
3. A distribution of its own for the tests: a package more for every addon.

## Decision

Option 2. The contracts of a package are in `<package>/testing/contracts`, and the
procedure of `ingots`, when it comes, looks there. `<package>/testing` may hold other
helpers for testing what is built on the package. Everything else in ADR 0005 stands.

## Consequences

### Positive

- A package is free to have a domain of contracts.
- The import tells a test helper from the business logic.

### Negative

- A longer import path.

### Open questions

## Links

- [ADR 0005](0005-addons-ship-contract-tests.md): the contracts themselves.
