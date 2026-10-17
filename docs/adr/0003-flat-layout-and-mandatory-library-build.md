# 0003. Flat layout; libraries are tested as built wheels

- Status: Accepted
- Date: 2026-10-17
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **laying out Python repositories**, facing **the choice
> between the flat and the `src/` layout**, we decided for **the flat layout,
> with a mandatory build-and-test-the-wheel step for libraries** and against
> **`src/` as a default**, to achieve **less nesting and no layout ceremony
> while still testing what users install**, accepting **one more build step in
> every library's checks**.

## Context

The `src/` layout keeps the package off `sys.path`, so tests are forced to run
against an installed package. Its real benefit is catching packaging mistakes:
package data (`.proto`, fonts, templates), `py.typed`, generated modules or a
subpackage missing from the wheel. With the flat layout tests import the package
from the working tree and stay green while the published wheel is broken.

That benefit is weaker than it looks: `uv sync` installs the project in
editable mode, so even with `src/` tests import from the working tree. Other
arguments for `src/` (root-level modules shadowing dependencies, monorepos) do
not apply: repository roots hold only `Makefile`, docs and data.

## Decision drivers

- No nesting or configuration that exists only for the layout's sake.
- What users install must be what the tests exercised.
- One layout for every repository.

## Considered options

1. `src/` layout everywhere.
2. Flat layout everywhere, no build step.
3. Flat layout; libraries build their wheel and test it.

## Decision

Option 3.

- Every repository uses the flat layout: the import package lives at the
  repository root (`<module>/`), tests in `tests/`. With `uv_build` this is
  `module-root = ""` in `[tool.uv.build-backend]`.
- A *library* is a distribution meant to be installed by others (published to
  PyPI or depended on by another repository). For a library:
  - `make all` builds the distributions (`uv build`) into `dist/`;
  - `make check` also runs the tests against the built wheel: the wheel is
    installed into a fresh environment, and the tests run from a copy of
    `tests/` outside the repository, so the package can be imported only from
    the wheel;
  - CI runs the same `make check`; a release publishes exactly the wheel that
    passed it.
- A *tool* (an application of the ecosystem, not installed by others, e.g.
  `logo-gen`) needs no build step: its tests from the working tree suffice.

## Consequences

### Positive

- No `src/` nesting; `python -m unittest` and imports work from the root.
- Packaging mistakes are caught before a release, more strictly than `src/`
  with an editable install would.

### Negative

- Library checks are slower by a build and an install.
- The wheel test is plumbing every library has to carry (`Makefile`, CI).

### Open questions

- Whether the wheel test becomes a shared script in `ingots-libs` rather than
  being repeated in every library.

## Links

- [0002](0002-target-linux-macos-as-by-product.md): CI runs on Linux only.
- Packaging guide, "src layout vs flat layout":
  https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
