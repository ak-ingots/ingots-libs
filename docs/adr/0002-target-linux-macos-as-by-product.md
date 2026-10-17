# 0002. Target Linux; macOS as a by-product

- Status: Accepted
- Date: 2026-10-17
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **choosing target platforms for the ecosystem**, facing
> **the cost of supporting and testing several operating systems**, we decided
> for **Linux as the only target, with macOS working as a by-product of POSIX**
> and against **Windows and first-class macOS support**, to achieve **one
> platform to design, test and deploy on**, accepting **that macOS may break
> without notice and Windows users need WSL or containers**.

## Context

Ingots packages are developed and deployed on Linux. macOS is close enough
(POSIX: signals, sockets, file paths, asyncio event loop) that most code
runs on it unchanged, which is useful for local development. Windows differs in
the asyncio event loop, signals, process model and paths; supporting it means a
second set of code paths and CI jobs for a platform nobody deploys on.

## Decision drivers

- Design and test for a single platform.
- Freedom to use POSIX- and Linux-only facilities without workarounds.
- Keep macOS usable for development when it costs nothing.

## Considered options

1. Linux, macOS and Windows.
2. Linux and macOS, both first-class.
3. Linux only; macOS as a by-product.
4. Linux only; macOS explicitly unsupported.

## Decision

Option 3.

- Linux is the only target: CI runs on Linux only, and a change is done when it
  works on Linux.
- macOS is not tested and not guaranteed. Code is not made Linux-specific
  without a reason, so macOS keeps working as a by-product; a macOS breakage is
  fixed when the fix is cheap and does not complicate Linux code.
- Windows is not supported: no Windows-specific code paths, tests or CI jobs.
- `pyproject.toml`: `[tool.uv] environments = ["sys_platform == 'linux'",
  "sys_platform == 'darwin'"]`, so `uv.lock` resolves for both and `uv sync`
  works on macOS; OS classifiers list `Operating System :: POSIX :: Linux` and
  `Operating System :: MacOS`.
- A repository that relies on Linux specifics narrows `environments` to
  `sys_platform == 'linux'` and says why next to it (e.g. `logo-gen` takes its
  font from a Debian/Ubuntu system path).

## Consequences

### Positive

- One platform to design and test for; small lock files and CI matrix.
- POSIX- and Linux-only APIs may be used freely.

### Negative

- macOS problems surface only when someone runs the code there.
- Windows developers need WSL or a container.

### Open questions

- Whether a published library should get a non-blocking macOS CI job.
