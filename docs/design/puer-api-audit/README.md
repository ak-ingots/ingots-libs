# PUER API audit

A working note, not a decision. Every member of every PUER entity: who it is
for, how sensitive it is, who calls it and from where, how it is protected
now, and how it could be. Taken from the uncommitted `puer-components` branch
of `ingots` on 2026-10-21, after the components came into PUER.

## Decided since

Applied on the `puer-components` branch, waiting for the ADRs:

- **The owner package is the friend**, not the module: a protected member
  is touched by its class, its subclasses and the nearest package of its
  class, never by anything outside it. Closely interacting classes live in
  one package, one class family per file (`slots/pool.py`, `slots/map.py`,
  `slots/factory.py` next to `Slot`), so modules stay small and a change is
  a diff in its own file. Classes in different packages interact loosely,
  through arguments and public API; the nearest package is not stretched to
  its parent, or it soon becomes the whole project.
- **A hook gets what it needs as arguments** (`_create_entity(project)`,
  `_iter_entities(owner)`, `_extends(base)`), so a slot kind written in an
  addon only overrides hooks. A component takes its `ComponentLifecycle` in
  its constructor: `ComponentSlot` (`ingots.puer.slots`) hands it over
  instead of setting the component's internals (`ingots.puer`), and an
  addon's slot kind for components does the same.
- **Hooks take an underscore**, all of them: no prefix covers every kind
  of hook (moments, work, factories, predicates).
- **Every override takes `@typing.override`**, checked by mypy's
  `explicit-override`: a hook overridden by chance, or misspelt, is an
  error. It does not check that `super()` is called.
- **Final where the structure breaks**: `runner.run()` (parsing moved to
  `_prepare_run()`), `await component`, the `slots_` methods,
  `Slot.__get__` and `__set__`, read-only properties.
- **The project has no public lifecycle methods**: the runner awaits the
  `_configure()` hook and the final, internal `_do_shut_down()`, which
  runs the `_shut_down()` hook, then the components. The hooks need no
  `super()` for the framework.
- **The slot protocol is plural**: `_iter_entities(owner)`.
- **The slot index is lazy** by `cls.__dict__`, so a forgotten `super()` in
  `__init_subclass__` loses neither the check nor the index.
- **Internal names leave `__all__`**: `ComponentLifecycle`,
  `configure_component()`, `shut_down_components()`,
  `check_shutdown_order()`, `check_slots()`.

## Audiences and the rule

- **Caller**: business code, the CLI, commands. Reads slots, awaits
  components, reads `project.state`. Protected by `@t.final`: it may call,
  not override.
- **Extender**: the addon's author, and the application's author customizing
  the addon by inheritance (ADR 0004). Overrides hooks only: `_configure`,
  `create_entity`, `run_workflow`. Contract tests (ADR 0005) catch broken
  hooks.
- **Framework**: PUER itself: the lifecycle, the slot index, the state
  machine. Not exported, not documented, free to change. Lives in an
  underscored module or as functions in the class's own module.
- **The rule for protected members**, as first proposed: only the class,
  its subclasses and the module defining it touch them; the module is the
  "friend". Since replaced by the owner package, see above.

Marks: ✓ follows the rule; ✗ breaks the module rule; ! a risk or an open
question.

## Entity

`puer/entity.py`: the workhorse, the leaf of the tree.

| Member | Audience | Sensitivity | Called by, from | Now | Proposal | |
|---|---|---|---|---|---|---|
| `__init__(project)` | framework, extender | medium | `Slot.create_entity`, `slots/entity.py` | the signature is a contract with the slot | as is | ✓ |
| `project` | caller | low | any entity code | property, narrowed by `project: "AppProject"` | as is; `final` would lose the narrowing | ✓ |
| `_project_ref` | framework | — | the class | weakref | as is | ✓ |

## BaseComponent

`puer/component.py`: two states of one object.

| Member | Audience | Sensitivity | Called by, from | Now | Proposal | |
|---|---|---|---|---|---|---|
| `__await__` | caller | high | any `await component` | overridable | `@t.final`: the only door to the configuration | ! |
| `SHUTDOWN_ORDER` | extender | medium | the slot, when declared | checked in `__init_subclass__` | as is | ✓ |
| `_configure()` | extender | high | `_configure()` of the same module | hook, called once, in the implementation state | as is; documented as an extension point | ✓ |
| `_shut_down()` | extender | high | `_shut_down()` of the same module | hook, called once | as is | ✓ |
| `_component_lifecycle` | framework | high | written by `ComponentSlot.create_entity` in `slots/component.py`; read in `component.py` | instance attribute | slot and component in one module, or a public final attach point | ✗ |
| `configure_component()` | framework | high | `__await__` | public, in `__all__` | internal: callers have `await` | ! |
| `is_configured()` | caller | low | tests, diagnostics | module function | as is, or a final `is_configured` property | ✓ |
| `shut_down_components()` | framework | high | `Project.shut_down`, `project.py` | public, in `__all__` | a function, as decided; internal, not API | ! |
| `check_shutdown_order()`, `ComponentLifecycle` | framework | — | `component.py`, `slots/component.py` | in `__all__` | internal | ! |

## Slot, ComponentSlot

`puer/slots/entity.py`, `puer/slots/component.py`: the supervisor of one
entity.

| Member | Audience | Sensitivity | Called by, from | Now | Proposal | |
|---|---|---|---|---|---|---|
| `cls`, `implementation`, `shutdown_order` | caller | low | CLI, `components list`, applications | read-only properties | `@t.final` | ✓ |
| `__get__` | framework | high | Python; it calls `obj._slots_get_project()` from `slots/entity.py`, while `SlotsOwner` is in `slots/owner.py` | creates lazily, caches in `__dict__` | `final`; `Slot` and `SlotsOwner` in one module | ✗ |
| `__set__`, `__set_name__` | framework | high | Python | `ComponentSlot` overrides `__set_name__` | `__set__` final; `__set_name__` a hook calling `super()` | ✓ |
| `create_entity()` | extender | high | `__get__` of the same class | public name | a hook of slot kinds; underscored? | ✓ |
| `extends()` | extender | high | `check_slots`, `slots/owner.py` | public | a hook of slot kinds | ✓ |
| `get_entity(owner)` | framework | high | `slots_walk_entities` | one entity per slot | `iter_entities(owner)`: Pool, Map and Factory hold many, and all of them shut down | ! |
| `_check_class()` | extender | medium | `__init__` of the same class | a plain `Slot` rejects a component | as is | ✓ |

## SlotsOwner, Unit

`puer/slots/owner.py`, `puer/unit.py`: the first natural container.

| Member | Audience | Sensitivity | Called by, from | Now | Proposal | |
|---|---|---|---|---|---|---|
| `slots_iter()`, `slots_walk()` | caller | high | the CLI parser, `components list`, settings, applications | overridable | `@t.final` | ! |
| `slots_find_entity()` | caller | medium | `components run-forever`, the file loader | overridable | `@t.final` | ! |
| `slots_walk_entities()` | caller, framework | high | `shut_down_components`, tests | overridable | `@t.final`: a replaced walk silently leaves components running | ! |
| `__init_subclass__` | framework | high | Python | checks and indexes the slots | a user's `__init_subclass__` without `super()` drops the check and the index of its subclasses; build the index lazily by `cls.__dict__` | ! |
| `_slots_index` | framework | high | the module | a dict per class | as is | ✓ |
| `_slots_get_project()` | framework | high | implemented by `Project` and `Unit` (subclasses: fine); called by `Slot.__get__` from another module | abstract | see `__get__`: one module for the slot and its owner | ✗ |
| `check_slots()` | framework | high | `__init_subclass__` | a function, as decided | a function; internal, not API | ✓ |

## Project, ProjectState

`puer/project.py`, `puer/project_state.py`: the root, the only thing a runner
creates.

| Member | Audience | Sensitivity | Called by, from | Now | Proposal | |
|---|---|---|---|---|---|---|
| `state` | caller | low | `configure_component`, applications | read-only property | `@t.final` | ✓ |
| `configure()` | caller, extender | medium | the runner; `defaults.Project` overrides it with `super()` | public, overridable | as is: a forgotten `super()` is not fatal here | ✓ |
| `shut_down()` | caller | high | the runner, `runner.py` | overridable; a subclass must call `super()` | `@t.final`: states, components, then a `_shut_down()` hook for the rest; closes the forgotten `super()` of ADR 0004 for the shutdown | ! |
| `_project_state` | framework | high | the class | class attribute as the default | as is | ✓ |

## BaseRunner, CommandRunner

`puer/runner.py`, `puer/cli/runner.py`: drives the project through its flow.

| Member | Audience | Sensitivity | Called by, from | Now | Proposal | |
|---|---|---|---|---|---|---|
| `run()` | caller | high | the application's `main` | `CommandRunner` overrides it (argument parsing) | `final` once parsing moves to a hook; create → configure → run → shut down fixed | ! |
| `run_workflow()`, `stop_workflow()` | extender | high | `_run_project` of the same class | public names, abstract | hooks; underscored or not is the common decision on hooks | ✓ |
| `create_project()` | extender | medium | the class; `CommandRunner` overrides it | public | a hook | ✓ |
| `project`, `GRACEFUL_TIMEOUT_DEFAULT` | caller | low | subclasses, the CLI | property, constant | as is | ✓ |
| `_run_project()`, `_run_stage()`, signal handling | framework | high | the class | protected | as is | ✓ |

## CliNode, BaseCommand, CliParser

`puer/cli/`: the command line built from the slots.

| Member | Audience | Sensitivity | Called by, from | Now | Proposal | |
|---|---|---|---|---|---|---|
| `cli_description`, `cli_prepare_parser()`, `cli_build_args()` | extender | medium | the parser | `cli_` prefix | as is: the mixin prefix of ADR 0007 | ✓ |
| `cli_args` | caller | low | commands, units | property | `@t.final` | ✓ |
| `_cli_set_args()` | framework | high | `CommandRunner._set_cli_args` in `cli/runner.py`, on another object; the class is in `cli/node.py` | protected | an internal function in `node.py`, or node and runner in one module | ✗ |
| `BaseCommand.run()`, `stop()` | extender | high | `CommandRunner.run_workflow` | public, abstract | hooks | ✓ |
| `CliParser.parse()`, `tree`; `_build_children()` … | caller, extender | medium | the runner; a parser subclass through `cli_parser_cls` | protected hooks, documented | as is | ✓ |

## Future slots: Pool, Map, Factory

Not there yet; what they ask of today's protocol.

| Object | Audience | Sensitivity | Natural API | Asks of PUER | Open question | |
|---|---|---|---|---|---|---|
| `Pool(RedisApi, max=5)` | caller | high | `async with project.clients as client` | a slot giving several entities: `iter_entities(owner)` | is every instance a component with its own lifecycle? | ! |
| `Map(Connection)` | caller | medium | `project.dbs["main"]` | dynamic keys: `slots_walk` on the class does not know them | the path in `slots_find_entity`: `dbs.main` or `dbs[main]`? | ! |
| `Factory(...)` | caller | high | already discussed | what it creates is tracked to be shut down | who owns it: the factory (strong references) or the caller (weak)? | ! |

## Findings

1. **✗ Protected members touched from another module, four places.**
   `_slots_get_project` and `_component_lifecycle` came with the
   one-class-per-file layout; `_cli_set_args` was there before. Closely
   coupled classes (a slot and its owner, a component slot and its
   component) share a module or talk through a public final point.
2. **! `@t.final` where the structure breaks.** `__await__`, the `slots_`
   methods, `Project.shut_down` with a hook, `Slot.__get__` and `__set__`,
   read-only properties; `BaseRunner.run` once parsing leaves
   `CommandRunner.run`.
3. **! The public API is wider than callers need.** `configure_component`,
   `shut_down_components`, `check_shutdown_order`, `ComponentLifecycle`,
   `check_slots` serve the framework: they stay functions, but leave
   `__all__` for an internal module.
4. **! The slot protocol in the plural.** `get_entity(owner)` becomes
   `iter_entities(owner)` while there are two slot kinds; the walk and the
   shutdown then do not care whether a Slot, a Pool or a Factory is in front
   of them.
5. **! A forgotten `super()` in `__init_subclass__`.** In a user's class it
   silently drops the slot check and the index of its subclasses. Build the
   index lazily by `cls.__dict__`, with the check there too, on the first
   walk.
6. **! Hooks with or without an underscore.** Mixed today: `_configure`,
   `_shut_down` against `create_entity`, `extends`, `run_workflow`,
   `BaseCommand.run`. One rule for every hook.
