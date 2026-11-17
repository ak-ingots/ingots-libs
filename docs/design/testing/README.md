# Testing: a project as a fixture

- Status: Proposed
- Packages: ingots (`ingots.testing`); its first consumers ingot-auth
  (`tests/`) and its `examples/game/scenarios`
- Date: 2026-11-17
- ADRs: [0005](../../adr/0005-addons-ship-contract-tests.md),
  [0012](../../adr/0012-design-a-feature-before-building-it.md),
  [0016](../../adr/0016-run-the-addons-in-examples.md)

## Problem

A test of an addon builds its project by hand: it patches `os.environ` to
set the configs and to hide those of the developer, patches the logging,
configures the project and shuts it down, each addon in a mixin of its
own (`ServerMixin` of ingot-auth). The scenarios of `examples/game` read
`GAME_TEST_PORT` from the environment themselves and open their channels
by hand, beside the clients of ingot-grpcio. The configs of a test go
around everything the settings of a project give: the prefix, the files,
`--config`, the strict mode, their printing. With the examples of ADR 0016
every feature addon is to write scenarios: the project of a test is to be
written once, in ingots.

## Actors

- The author of an addon: tests its project, the contracts of ADR 0005
  among them.
- The author of an application: runs the scenarios of its examples, a
  client of the application.
- The CI and the dev server: run them, configured as the application is.

## Stories

| # | Actor | Story | Now or later |
|---|---|---|---|
| 1 | author of an addon | I declare the project of a test case as a fixture, `project = ProjectFixture(TstProject, configs={...})`, and read `self.project` in a test, configured by those configs alone, whatever the environment of the developer holds. | now |
| 2 | author of an addon | Each test has a project of its own, created in its event loop and shut down after it, so that a client of a server is never of a closed loop. | now |
| 3 | author of an addon | A test has two projects, a server and its client, two fixtures. | now |
| 4 | author of an application | The scenarios are a project of their own, a client of the application, a `TestingProject`: `python -m scenarios testing run`, configured as any project, `GAME_TEST_*`, `--config`, `--configs-file`, its fixtures of that class configured as the command. | now |
| 5 | CI | A run that fails exits non-zero. | now |
| 6 | author of an addon | A project of a test leaves the logging of the process to the run, unittest or `testing run`: its loggers write where the run sends them, `assertLogs` sees them, and two projects of a test do not configure it in turn. | now |
| 7 | author of an addon | The contracts of ADR 0005 take their project from a fixture of the consumer. | later |
| 8 | author of an application | `testing run` takes the options of unittest: a name, `-k`, `-v`, `--failfast`, as one scenario runs only by the command. | now |

## Rules and examples

- Rule: the configs of a fixture win; then those every fixture sets,
  `IS_PRINT_CONFIGS` and `IS_CONFIGURE_LOGGING` off; what they leave
  open, the run of `testing run` gives, by the environment and the command line;
  outside a run, the defaults of the configs.
  - Example: given `INGOT_REDIS_PORT=6379` in the shell of the developer,
    when a test of `ProjectFixture(TstProject, configs={"REDIS_PORT":
    "16380"})` runs by `python -m unittest`, then the cache is on 16380;
    without the config, on the default 6379 of the configs, not of the
    shell.
  - Example: given `GAME_TEST_GAME_HOST=game.local`, when
    `python -m scenarios testing run --config GAME_PORT=50061` runs, then the
    client of a scenario calls `game.local:50061`.
- Rule: a `TestingProject` is tested by its `testing run` only: its
  fixture outside a run raises `OutsideRunError`, telling the command.
  - Example: when `python -m unittest discover -s scenarios` runs, then
    every scenario errs with `run by: python -m scenarios testing run`, none
    passes nor is skipped.
- Rule: a project configures the logging of the process unless its new
  config `IS_CONFIGURE_LOGGING`, on by default, is off: then the owner of
  the process does, as an application embedded in another server would
  want too.
  - Example: given `GAME_TEST_IS_CONFIGURE_LOGGING=on`, when
    `python -m scenarios testing run` runs, then the project of the command
    configures the logging once, the projects of the scenarios never.
- Rule: a project of a fixture lives one test: created in `asyncSetUp`,
  in the loop of the test, shut down by a cleanup, the later fixture first.
- Rule: a fixture is read during a test only; outside, a `RuntimeError`.
- Rule: a mixin declares a fixture as a test case does. The fixtures are
  created before the `asyncSetUp` of the bases, so a contract of ADR 0005
  reads its project in its own; `ProjectTestCase` comes last of the
  bases, in place of `IsolatedAsyncioTestCase`.
  - Example: `RedisSessionsCacheTestCase(ServerMixin,
    AuthSessionsCacheContract, ProjectTestCase)`, `ServerMixin` declaring
    `server = ProjectFixture(...)` and `create_project()` returning it.
- Rule: `testing run` runs the tests in a thread of their own, as a test case
  runs its own event loop, not in the running one of the command.

## API sketch

The tests of an addon (the prototype: `fixture/addon_tests.py`):

```python
from ingots.testing import ProjectFixture, ProjectTestCase


class RedisCacheTestCase(ProjectTestCase):
    project = ProjectFixture(TstProject, configs={"REDIS_DEFAULT_PORT": "16380"})

    async def test_an_attempt_is_taken_once(self) -> None:
        attempts = self.project.auth.cache.attempts
        ...


class EchoTestCase(ProjectTestCase):
    server = ProjectFixture(ServerProject, configs={"GRPC_DEFAULT_PORT": "50071"})
    client = ProjectFixture(ClientProject, configs={"GRPC_DEFAULT_PORT": "50071"})
```

The scenarios of an application (`fixture/scenarios/`), a
`TestingProject`, as `GrpcProject` a project of an addon: the slot
`testing` of `TestingUnit`, the unit of the commands of the tests, as
`logging` is of `LoggingUnit`, its command `run` the `RunTestsCommand`;
its client the default one of ingot-grpcio:

```python
class ScenariosProject(TestingProject, GrpcProject):
    env_configs_prefix = "GAME_TEST"
    settings = Slot(ScenariosSettingsUnit)  # GRPC_DEFAULT_*, MAILPIT_URL
    grpc = Slot(ScenariosGrpcUnit)          # a client of the bindings of the auth


class SignUpScenario(GameMixin, ProjectTestCase):
    project = ProjectFixture(ScenariosProject)
```

```sh
GAME_TEST_GRPC_DEFAULT_PORT=50061 python -m scenarios testing run -k sign_out
```

`ProjectFixture` is a descriptor typed by its class, as a `Slot` is: mypy
knows `self.project` as the project of the fixture, refuses a config of
another type than `str`, as `--config` takes it, and a class that is not
a project (`fixture/mistakes.py`).

## Pre-mortem

- A test leaks its project, a client open after its loop: the cleanup
  shuts every project down, the later first, whatever the test raised.
- A developer's shell changes a test: outside a run the environment of
  the prefix is hidden while the project is configured.
- The scenarios run by `python -m unittest` call the defaults and fail
  far from the cause, or skipped pass green unchecked: they err outside
  their command, telling it.
- A test of the logging itself needs the project to configure it: its
  fixture sets `IS_CONFIGURE_LOGGING` on, its own configs winning.

## Alternatives

- A plugin of unittest: unittest has none; a runner of our own would be
  a second entrypoint beside the CLI of the project, which configures
  already.
- One project for the whole run: its clients are of the loop of the
  first test; every later test would fail on them.
- The patch of `logging.config.dictConfig` the tests do today: global to
  the process, it also hides the configuring of a project that should
  have run; a config says what the project does instead.
- pytest and its fixtures: not of the ecosystem; this is the explicit
  pseudo-fixture of a test case.

## Open questions

None for now.

## Slices

1. ingots: the config `IS_CONFIGURE_LOGGING`, `ProjectFixture`,
   `ProjectTestCase`, stories 1, 2, 3, 6; their first consumer the tests
   of the storage and the cache of ingot-auth, in place of `ServerMixin`.
   Built: ingots 0.35.0 (ak-ingots/ingots#40); ingot-auth moves to it.
2. ingots: `TestingProject`, `TestingUnit`, `RunTestsCommand`, stories
   4, 5, 8; their first consumer `examples/game/scenarios`, a project
   with the client of ingot-grpcio. Built: ingots 0.35.1
   (ak-ingots/ingots#44), ingot-auth#80.
3. Then the slice 4 of the game: the operator and the second process.
