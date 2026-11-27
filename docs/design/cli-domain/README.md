# The command line, a domain of its own

- Status: Built, released as ingots 0.38.0, ingot-grpcio 0.17.0 and
  ingot-auth 0.12.0 (2026-11-27)
- Packages: ingots, ingot-grpcio, ingot-auth
- Date: 2026-11-26
- ADRs: [0004](../../adr/0004-static-composition-with-typed-slots.md),
  [0007](../../adr/0007-code-layout-and-naming.md),
  [0018](../../adr/0018-check-a-slot-by-its-kind.md);
  [0020](../../adr/0020-keep-the-commands-in-the-domain-of-the-cli.md), its layout
  once accepted, the place of the commands of every addon changing

## Problem

The command line is mixed into the domains: `ingots.puer.cli` gives
`CliUnit` and `CliProject`, and the settings, the logging, the components,
`perf`, `testing`, the gRPC unit and a dozen units of ingot-auth are
`CliUnit`s, their commands in slots next to their operations and entities.
Two namespaces share one unit, so the commands take a prefix,
`cmd_list = Slot(...)`, and the sub-command a `cli_name`; the domain units
carry `cli_description`; the parser walks every unit and leaves out those
that are not on the command line. The command line is an interface, as gRPC
and HTTP are, and those are trees of their own that call the domains.

## Actors

- The author of an addon: gives the commands of its domain.
- The author of an application: takes the commands of its addons, adds its
  own.
- An operator: runs them, by the command lines of today.

## Stories

| # | Actor | Story | Now or later |
|---|---|---|---|
| <a id="cli-1"></a>1 | author of an addon | **The commands of my addon are a tree of their own, `AuthCommandsUnit` with `tags = Slot(AuthTagsCommandsUnit)`, under `project.cli`; my domain units hold no command, and a command reaches the domain by its project, `self.project.auth.tags`.**<br>• The name of a slot is the sub-command: no `cmd_` prefix, no `cli_name`. | now |
| <a id="cli-2"></a>2 | author of an application | **I join the command lines of my addons as I join their settings: `AppCliUnit(AuthCliUnit, GrpcCliUnit)`, adding a slot of my own.** A join forgotten fails in mypy and at the creation of the class. | now |
| <a id="cli-3"></a>3 | operator | **The command lines stay as they are: `--config NAME=value`, `settings list`, `components run-forever`, `auth tags list`, `grpc export`, `perf seed`, `testing run`.** | now |
| <a id="cli-4"></a>4 | author of an addon | **A domain unit put in a unit of commands fails the class**, not leaves it silently off the command line. | now |

## Rules and examples

- Rule: `ingots.defaults.cli` is the domain of the command line: `CliNode`,
  `CliUnit`, `CommandsUnit`, `BaseCommand`, the parser, `CommandRunner`.
  `ingots.puer.cli` and `CliProject` go; `ingots.defaults.Project` is no
  `CliNode`, its slot `cli` is.
- Rule: the domain is named as the others are: its root `CliUnit`,
  `project.cli`, as `SettingsUnit` is `project.settings`; an addon extends
  it, `AuthCliUnit(CliUnit)`, as it extends the settings; a group of
  sub-commands is a `CommandsUnit`, `AuthCommandsUnit`,
  `AuthTagsCommandsUnit`, `SettingsCommandsUnit`.
- Rule: the root owns the options of the project, `--config`,
  `--configs-file`, and the groups of the defaults, `settings`, `logging`,
  `components`; what reads the options reads `project.cli.cli_args`: the
  loader of the command line, `perf point` passing them on, `testing run`.
- Rule: a slot of a `CommandsUnit` holds a `CommandsUnit` or a command, else
  the class fails. A command's `parent` is its unit of commands.
  - Example: `perf`: its commands had `cmd_seed` beside the entity `seed`,
    and read the scenario through `self.parent`; now `cli.perf.seed` reads
    `self.project.perf`, typed by `PerfStandProject`, the base of the
    project of a scenario, which puts `perf` on its command line.
- Rule: the commands of a domain are an extension of the command line, laid
  out as such: in ingots, `defaults/cli/extensions/settings.py`,
  `logging.py`, `components.py`, the group of each beside its commands, not
  at the root of `cli/`, where a module named after a domain reads as that
  domain; in an application, `extensions/cli.py` beside
  `extensions/settings.py`; in an addon, its package `cli/`, the folders as
  the tree goes, `cli/profiles/tags.py` the group `auth profiles tags`, the
  addon's `*CliUnit` in `cli/__init__.py` (ADR 0020).
- Rule: the members of `CliNode` keep the prefix `cli_` of a mixin (0007):
  the runner is a node too.
- Rule: `BaseOperationCommand` stays in `ingots.defaults.operations`, the
  bridge from a command to an operation.

## API sketch

The prototype is in [tree/](tree/): `ingots_stub.py` puer, the domain of
the command line and the defaults; `addons.py` ingot-auth and ingot-grpcio;
`app.py` an application of both and of its own commands; `check_types.py`
runs the command lines; `mistakes.py` what mypy refuses.

```python
# ingot_auth
class AuthListTagsCommand(BaseCommand):
    project: "AuthProject"

    async def _run(self) -> None:
        print(" ".join(self.project.auth.tags.list_tags()))


class AuthTagsCommandsUnit(CommandsUnit):
    list = Slot(AuthListTagsCommand)


class AuthCommandsUnit(CommandsUnit):
    tags = Slot(AuthTagsCommandsUnit)


class AuthCliUnit(CliUnit):
    auth = Slot(AuthCommandsUnit)


class AuthProject(Project):
    auth = Slot(AuthUnit)  # its domain, no command in it
    cli = Slot(AuthCliUnit)


# the application
class AppCliUnit(AuthCliUnit, GrpcCliUnit):
    shop = Slot(ShopCommandsUnit)


class AppProject(AuthProject, GrpcProject):
    shop = Slot(ShopUnit)
    cli = Slot(AppCliUnit)
```

What is checked where:

- mypy: the command lines of two addons not joined; a command reaching the
  domain through its parent.
- At the creation of a class: the join forgotten (0018); a slot of a unit of
  commands holding neither a unit of commands nor a command.
- At run time: nothing new; only the units on the path of the command are
  created, as today.

## Pre-mortem

- One more join per addon: an application of three addons with commands
  joins `cli` as it joins `settings`, a line. A starter
  ([typed projects](../typed-projects/README.md)) writes it once.
- Two trees to keep in step, the domain and its commands: a command reaches
  its domain by the project, so a domain moved breaks the command in mypy,
  not at run time.
- A command needing its domain unit as context, `perf` with its scenario:
  it reads `self.project.perf`, typed by the project of the part.

## Alternatives

- **Every horizontal concern a domain**, the operations and the components
  under `operations` and `components` too: rejected, it splits a domain over
  as many trees and multiplies the joins; an operation needs its domain unit
  as its parent, a component is a role of an entity, not a place.
- **The mixin, as now**: the prefixes, the `cli_name`, a parser that skips.

## Open questions

- `cli_name` gone: a sub-command that is no identifier, `import`, waits for
  its case.

## Slices

1. ingots, a breaking release: `ingots.defaults.cli`, `Project.cli`, the
   commands of the settings, the logging, the components, `perf` and
   `testing` in their trees; `ingots.puer.cli` gone. Its first consumers,
   the tests and the scenarios of `perf`.
2. ingot-grpcio: `GrpcCommandsUnit`, `grpc export`.
3. ingot-auth: the tree `auth` of its commands, its domain units plain; the
   examples on it.
