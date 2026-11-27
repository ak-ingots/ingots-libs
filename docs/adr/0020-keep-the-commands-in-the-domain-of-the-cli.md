# 0020. Keep the commands in the domain of the command line, as its tree goes

- Status: Proposed
- Domains: design
- Date: 2026-11-27
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: — (refines [0007](0007-code-layout-and-naming.md)
  for the commands)

> In the context of **the commands of an addon, once the command line is a
> domain of its own, `project.cli`, apart from the units they run**, facing
> **commands left in the packages of their domains, a `commands.py` in each,
> the tree of `auth ...` scattered over the tree of the units and put
> together in one module**, we decided for **a package `cli/` of the addon
> holding every command, its folders as the tree of the command line goes,
> a group in the `__init__.py` of its package or in the module of its
> name**, and against **the commands beside their domains, and the units of
> the domains holding them, as before**, to achieve **one place for the
> command line, read as it is typed**, accepting **two trees, the units and
> the commands, kept in step by the types**.

## Context

The command line of ingots 0.38 is a domain,
[the command line, a domain](../design/cli-domain/README.md): a
`CliUnit` at `project.cli`, groups of sub-commands `CommandsUnit`, an
addon extending the root, `AuthCliUnit(CliUnit)`. A domain unit holds no
command any more; a command reaches its domain by `self.project`.

The first layout of ingot-auth kept each group beside its domain,
`profiles/tags/commands.py`, and a `cli.py` putting them together: the
tree of `auth ...` was found in twelve packages, as the configs would be
if each package held its own, where `settings.py` holds them all.

## Decision

- The commands of an addon are in its package `cli/`, its `*CliUnit` in
  `cli/__init__.py`.
- Its folders repeat the tree of the command line: the group of
  `auth profiles attrs` in `cli/profiles/attrs/__init__.py`, that of
  `auth profiles tags`, which has no group under it, in
  `cli/profiles/tags.py`, the root group of the addon in `cli/__init__.py`.
- A base of the commands of several groups is in a module beside them,
  `cli/registry.py`, out of the tree: an `__init__.py` cannot hold the base
  its own modules import.
- The commands import their operations and data from the domains; the
  domains import nothing of `cli/`.
- In ingots, the root `CliUnit` is the domain and its own commands,
  `completion`, are in `defaults/cli/commands.py`; the commands of the
  other domains of the defaults are its extensions,
  `defaults/cli/extensions/settings.py`. An application's commands are in
  `extensions/cli.py`.

## Consequences

- The command line of an addon is read in one folder, as it is typed.
- A command moved in the tree moves its module; a domain moved breaks its
  commands in mypy.
- Every addon with commands follows: ingot-auth since 0.12.0, ingot-grpcio
  since its release after 0.17.0, `ingot_grpcio.cli.grpc`.
