# The load of the ecosystem

- Status: Proposed
- Packages: ingots (`ingots.perf`, what is loaded and how), ingots-libs
  (`perf/`, the runner of the dev server and the stand of Compose),
  ingot-auth (the game its first stand), ingot-grpcio (`examples/echo/`,
  its first own stand)
- Date: 2026-11-18
- ADRs: [0004](../../adr/0004-static-composition-with-typed-slots.md),
  [0012](../../adr/0012-design-a-feature-before-building-it.md),
  [0016](../../adr/0016-run-the-addons-in-examples.md); the design of
  [testing](../testing/README.md) beside it

## Problem

The load of the game ([slice 6](../auth/examples/game.md)) works and has
found two things already: a call with a token is bound by the GIL of a
process, about 1.15 CPU of each, and the sign-in loses throughput under
overload. It is written for the game alone, in bash and a module of its
own: its client calls stubs by hand beside the clients of ingot-grpcio
and the configs of the scenarios, its cores are written twice, and
nothing of it serves another addon. What of 3.7 ms of CPU a call is the
auth, what ingot-grpcio, what grpcio, no number tells. Every addon is to
be loaded alike, its numbers subtracting those of the addons under it;
and a scenario is to shape its own report and analysis, as an
application shapes an addon: by a project, its slots and its configs.

## Actors

- The author of an addon: writes the stands of its examples, runs one
  at the cut of a release, the candidate against the release before it,
  reads the analysis into the pull request of the release.
- The author of a feature addon: reads its own cost as its number less
  that of its transport.
- The dev server: the only host of a run; its owner keeps it quiet.
- CI: runs every scenario dry against the example it brought up.

## The split

`ingots.perf` is what is loaded and how: a scenario, its clients, a
point of the load against a target already up, its report and its
analysis. It assumes nothing of how the target was brought up, on which
host, in which cores: it is tested by unit tests, with no Docker.

A stand is how the target is brought up and down: its build, its
services, their cores, what of them a point measures, and how its
scenarios run, their Python and their directory. It is an executable of
the stand, `stand`, its contract three commands, its inside anything:
Compose, processes, a dump restored.

The runner is how a run is carried out on a host: its checks, the roles
and their trees, the rounds, the cores of the load. It knows no Docker:
it calls `stand` and the commands of the scenarios through it. It is
outside the framework, `perf/` of the meta repository, bash to begin
with; another host gets a runner of its own, and the runner changes with
no release of ingots.

```python
def run(stand, scenario):            # the runner, roughly
    check_host()
    plan = stand.perf(scenario, "plan")
    for round in plan.rounds:
        for role in ("baseline", "candidate"):
            try:
                services = stand.up(worktree(role))   # down a half up too
                stand.perf(scenario, "seed")
                for groups in plan.groups:
                    pinned(stand.perf(scenario, "point", groups, services))
            finally:
                stand.down(worktree(role))
    stand.perf(scenario, "analyze")
```

## Stories

| # | Actor | Story | Now or later |
|---|---|---|---|
| 1 | author of an addon | A stand is a directory, `perf/<stand>/`, an addon having as many as it wants, the same example in another topology or under other scenarios: its executable `stand`, its `perf.ini`, its `scenarios/`, its `reports/`, and what its `stand` brings the target up by, `docker-compose.perf.yml`. | now |
| 1a | author of an addon | `stand` is the contract of a stand with the runner: `stand up TREE` builds the target of a tree of the repository and brings it up, printing what its points tell, `PERF_CGROUPS` and `PERF_SERVERS`, `NAME=value` quoted for the shell; `stand down TREE` brings it down with its data; `stand perf ARGS` runs `python -m ingots.perf ARGS` as its scenarios import, from the directory of the example. A stand of Compose delegates to `perf/compose-stand` of the meta repository, its example and its files named; another writes its own. | now |
| 2 | author of an addon | A scenario is a module of the stand, `scenarios/<name>.py`, a project of its own, `PerfProject`, a subclass of the project of the client it loads, the scenarios project of the example or the project of the stand over it, `project.py` beside `scenarios/`, the base its scenarios share, with the unit `perf` of `ingots.perf`: its configs, its logging, its client, its report and its analysis overridden there as any project overrides an addon. | now |
| 3 | author of an addon | The unit `perf`, a subclass of `PerfUnit[Row]`, names the group of the scenario, `group = DuelGroup`, a `LoadGroup[Row]`, and what it seeds, its slot `seed`, a `CsvSeed[Row]` whose `_make()` makes the rows: the data the scenario needs ahead, made through the API of the application by its client, not written into its storages, so that it is what the application writes, the same for both roles whatever their storages keep. | now |
| 4 | author of an addon | `seed` writes the rows `_make()` returns, dataclasses of the type of the unit, `Player(nickname, token)`, into `seed.csv`, their fields its header; `point` reads them back by the annotations of the fields, and group `i` of a point takes row `i` in turn, its clients reading it as `self.group.seeded`. A scenario that seeds nothing, the echo, has no file. | now |
| 5 | author of an addon | A client of the load, a `LoadClient`, is a user of the application, an instance a client: its set-up unmeasured, then its `run()` again and again, what it measures named by it, `async with self.measure("get-own-profile")`; its project the `PerfProject`, its client that of ingot-grpcio. | now |
| 6 | author of an addon | A group, a `LoadGroup[Row]`, is the clients that meet, one of each class of its `clients`, `(Inviter, Invitee)`, a class twice for two, and what they share, typed: the row of the seed, the state its subclass declares, set up by its `asyncSetUp()` before the clients, and a time one starts and another finishes, `self.group.start("invite", key)`, `finish("invite", key)`, measured as an action; a client is typed by its group, `LoadClient[PerfProject, DuelGroup]`; a group runs in one process of the load. | now |
| 7 | author of an addon | The configuration has two levels, those of every project: the files, `perf.ini` of the stand, then `scenarios/<name>.ini` of the scenario if any, found by `ingots.perf` beside the module, give the defaults, the command line overrides them, `--config PERF_DURATION=60`; the configs are `PERF_*` of `PerfConfigs` and those the scenario declares, its parameters. | now |
| 8 | author of an addon | The commands of the unit, its slots `cmd_*`, against a target up: `seed`, its rows into `seed.csv`; `point`, the processes of the load started, warmed up, measured, merged, the rows appended to the report of the run; `load`, a process of a point; `analyze`, a report compared by its roles; `smoke`, a point dry; `plan`, the configs of a run resolved, `PERF_*` a line each, `NAME=value` quoted for the shell, a list its items apart by spaces, so that the runner takes them by `eval` and parses no file. | now |
| 9 | author of an addon | A point keeps, by each action, the calls, the calls a second, p50, p95, p99, the errors by their codes; by the point, the CPU of every service, given by its cgroup, and of the backend a call, the CPU of the load, and why it is void. | now |
| 10 | author of an addon | A run is a report of its own, in `reports/<scenario>/` of the stand, `<date>-<time>-<host>.csv` and `.ini`: the CSV the data alone, the role, the round, the action, the groups, the metric, its value; the INI the run, the host and its state, the Python and the servers, each role with its ref and commit, and the configs resolved, by which the run is repeated. | now |
| 11 | author of an addon | `analyze` compares the candidate with the baseline by the median of the rounds, and marks a change beyond the spread of the rounds; a scenario overrides it, and the report, by the slots of its unit. | now |
| 12 | CI | `smoke`, against the example CI brought up: no warmup, a group, a run of each client; in its process alone, its report in `reports/dry/`, ignored by git; it fails when an action made no call or met an error the scenario does not expect. The CI of every addon with a stand runs it, `make perf-smoke`. | now |
| 13 | author of an addon | The runner, `make -C perf run STAND=ingot-auth/perf/game` of the meta repository, carries a run out on the dev server: it checks and tunes the host, brings each role up and down by `stand`, rounds after rounds, calls `seed` and `point` of each scenario through it, then `analyze`. | now |
| 14 | author of an addon | The baseline and the candidate are each a git ref, a tag, a branch, a commit, or `latest`, the newest `vX.Y.Z`, the default of the baseline, so that at the cut of a release the candidate meets the release before it with no edit; the candidate the tree by default. The runner brings a ref up from its worktree, and tells `point` the ref as given and the commit it resolved to, `-dirty` for a tree with changes. | now |
| 15 | author of an addon | The cores are written once: those of the services by the stand, in `docker-compose.perf.yml`, their `cpuset`, those of the load and of the system in `PERF_LOAD_CPUS`, `PERF_SYSTEM_CPUS`; the runner starts `point` on the cores of the load, its processes inheriting them, and gives it the cgroups of the services `stand up` told. | now |
| 16 | dev server | The runner refuses a host that is not quiet: the boost, the IDE, Claude Code off the cores of the system, the memory, the swap; `perf/tune-host` tunes the host, `perf/check-host` tells how it stands. | now |
| 17 | author of ingot-grpcio | Its example, `examples/demo/`, and its stand load an echo through the servicer of ingot-grpcio, a failure mapped by its policy, and the same echo on grpcio alone, the floor, of the stand, not of the example: its server, `bare/`, an image of its own at the versions of the example of the role, its client in the stand, on cores of its own; an addon of a feature has none. | now |
| 18 | author of a feature addon | The numbers of two stands compare on one host: the same cores, Python, client and clients. | now |
| 19 | author of an addon | A point profiled: `py-spy` records a service in the measured window, its flame graph beside the report. | later |
| 20 | author of an addon | The transport checked by a client without the GIL, `ghz`, against the client of the stand. | later |
| 21 | author of ingot-pymongo, ingot-redis | Their examples, a query, a get and a set, loaded alike. | later |
| 22 | author of an addon | A scenario seeds a volume the API makes too slowly, a million profiles to load a query by, through the storage of the addon, `_make()` of its seed so. | later |

## Rules and examples

- Rule: a config is taken from the command line, else the environment,
  else the files in their order, `perf.ini`, then the scenario's, else
  its default in the code of the scenario.
  - Example: given `PERF_DURATION = 30` in `perf.ini` and `= 60` in
    `scenarios/sign-in.ini`, when `--config PERF_DURATION=90` is given,
    then the sign-in is measured 90 seconds a point, the rest 30.
- Rule: the module of a scenario gives `PerfProject`, a project with a
  slot `perf` of a `PerfUnit`; otherwise `ingots.perf` refuses, naming
  the module.
- Rule: the data of a seed is of one role and round: the runner brings
  each role down with its volumes, so a token seeded in the baseline is
  nothing to the candidate; `seed.csv` is made again each time, in the
  work of the stand, `PERF_WORK`, `work/` ignored by git, holding tokens;
  `PERF_SEED_FILE` names another.
- Rule: a relative path of the configs, `PERF_WORK`, `PERF_SEED_FILE`,
  `PERF_REPORTS`, is of the stand, whichever directory runs it.
  - Example: 256 players seeded through the API of the game take two
    minutes and more, a password hashed twice each; it is paid once a
    role and round, not once a point.
- Rule: a seed makes the data, not the steady state: the caches, the
  pools of connections reach it in the warmup of each point, under the
  load, `PERF_WARMUP`.
- Rule: the state the clients of a group share, the invitations of a
  duel, lives in the process of a point, never in `seed.csv`.
- Rule: `PERF_GROUPS` is the sweep, a point is of one of its values,
  `point --groups 4`; the seed is of the largest. The groups of a point
  are its size: `--groups 4` of
  the group of `clients = (Inviter, Invitee)` is 8 clients. `point` spreads the groups
  over its processes, never a group over two.
- Rule: the stand of a run, `stand`, `perf.ini`, `scenarios/` and the
  compose file of the stand, is that of the candidate for both roles, so
  that their cores and their client are one; each role brings only its
  example, from its own tree, `stand up TREE`.
  - Example: a scenario of the candidate calls an RPC the baseline has
    not; the baseline errs at it, and the analysis marks the point of
    the candidate alone, not a regression.
- Rule: the runner knows of a stand only `stand`; a stand needing
  another order, two targets, a dump, changes its `stand`, not the
  runner.
- Rule: numbers subtract only from the same host, cores, Python and
  client, and only as costs: the latency at one client, the CPU of the
  backend a call at the saturation; the latencies past it are queues.
- Rule: the window of a point over, its clients are cancelled, those
  waiting on a rival too; a call ending after the window is not
  measured.
- Rule: `PERF_GROUPS` is a list of any length, a `ListConfig` of ingots,
  its items of one type: `[1, 256]` as `[1, 2, 4, 8, 16]`.
- Rule: a point is void when its load took over 0.9 of its cores, the
  host swapped in, or it measured fewer than 20 calls; `point`
  reads the CPU of its processes and the swap of the host itself.
- Rule: the time of a run is in the name of its report, written by the
  run: git keeps no time of a file, and that of a commit is when it was
  committed, changed by a rebase too.
- Rule: the reports of the releases are committed with them; a trial's
  and a dry run's are out of git.

## API sketch

An addon, its stands under its examples (story 1):

```
ingot-auth/examples/
    game/                        # the application: compose, scenarios
    perf/
        game/                    # the game as it runs
            stand                # up, down, perf: the contract
            project.py           # the project of the stand, its scenarios' base
            perf.ini
            docker-compose.perf.yml
            scenarios/
                get-own-profile.py
                sign-in.py
                sign-in.ini
                duel.py
            reports/
                get-own-profile/
                    20261118-174448-bee.csv
                    20261118-174448-bee.ini
                dry/             # ignored by git
```

`perf.ini`, configs of every scenario of the stand, read by the
`--configs-file` of every project (story 7, 14, 15):

```ini
PERF_BASELINE = latest           ; a ref: v0.8.0, main, 9b8892d
PERF_CANDIDATE = tree
PERF_ROUNDS = 3
PERF_WARMUP = 10
PERF_DURATION = 30
PERF_LOAD_PROCS = 4
PERF_LOAD_CPUS = 8-11
PERF_SYSTEM_CPUS = 0-1
PERF_GROUPS = [1, 2, 4, 8, 16]
```

`project.py`, the project of the stand over the scenarios project of
the game, what its scenarios share (story 2–4):

```python
from ingots.perf import CsvSeed, PerfConfigs
from ingots.puer import Slot
from scenarios.project import ScenariosConfigs, ScenariosProject
from scenarios.project import ScenariosSettingsUnit


class GamePerfConfigs(ScenariosConfigs, PerfConfigs): ...


class GamePerfSettingsUnit(ScenariosSettingsUnit):
    configs = Slot(GamePerfConfigs)


class GamePerfProject(ScenariosProject):
    settings = Slot(GamePerfSettingsUnit)


@dataclasses.dataclass
class SeededPlayer:                              # a row of seed.csv
    nickname: str
    token: str


class PlayersSeed(CsvSeed[SeededPlayer]):
    project: "GamePerfProject"

    async def _make(self, groups: int) -> list[SeededPlayer]:
        return [await sign_up_and_in(self.project) for _ in range(groups)]
```

`scenarios/get-own-profile.py`, a scenario on it (story 2–5):

```python
from ingots.perf import LoadClient, LoadGroup, PerfUnit
from ingots.puer import Slot
from project import GamePerfProject, PlayersSeed, SeededPlayer


class Player(LoadClient["PerfProject", "PlayerGroup"]):
    async def asyncSetUp(self) -> None:          # unmeasured
        self.metadata = bearer(self.group.seeded.token)

    async def run(self) -> None:                 # again and again
        async with self.measure("get-own-profile"):
            await self.project.grpc.clients.game.profiles.GetOwnProfile(
                GetOwnProfileRequest(), metadata=self.metadata
            )


class PlayerGroup(LoadGroup[SeededPlayer]):
    clients = (Player,)


class OwnProfilePerf(PerfUnit[SeededPlayer]):
    group = PlayerGroup
    seed = Slot(PlayersSeed)


class PerfProject(GamePerfProject):
    perf = Slot(OwnProfilePerf)
```

`scenarios/duel.py`, clients that meet, a parameter a config (story 6,
7):

```python
class DuelConfigs(GamePerfConfigs):
    DUEL_THINK_MS = IntConfig(0)


@dataclasses.dataclass
class SeededPair:                            # a row: the two of a group
    inviter_token: str
    invitee_nickname: str
    invitee_token: str


class Inviter(LoadClient["PerfProject", "DuelGroup"]):
    async def run(self) -> None:
        key = await invite(self.project, self.group.seeded.invitee_nickname)
        self.group.start("invite", key)      # finished by the rival


class Invitee(LoadClient["PerfProject", "DuelGroup"]):
    async def run(self) -> None:
        key = await accept_next(self.project)
        self.group.finish("invite", key)
        self.group.duels += 1                # a state of the group, typed
        await asyncio.sleep(self.project.settings.configs.DUEL_THINK_MS / 1000)


class DuelGroup(LoadGroup[SeededPair]):
    clients = (Inviter, Invitee)

    async def asyncSetUp(self) -> None:      # before its clients
        self.duels = 0


class DuelPerf(PerfUnit[SeededPair]):
    group = DuelGroup
```

A report and an analysis of its own, by the slots of the unit (story
11):

```python
class SignInPerf(PerfUnit[SeededPlayer]):
    group = SignedInGroup
    analysis = Slot(HashBoundAnalysis)       # a subclass of MedianAnalysis
```

The slots of `PerfUnit`, each a strategy with a working default:

| Slot | Default | What it does |
|---|---|---|
| `seed` | `CsvSeed` | makes the rows of the seed, none by default, writes and reads `seed.csv` |
| `report` | `CsvReport` | appends the rows of a point to the CSV, writes the INI of a run |
| `analysis` | `MedianAnalysis` | compares the roles of a report |

The commands, `python -m ingots.perf <module> [options] perf
<command>`: `ingots.perf` loads the module by its path, not as a
package, so that it does not shadow the package `scenarios` of the
example, the stand joining the end of the path of imports, `project.py`
importing; finds its configs files beside it, and runs its `PerfProject`:

```sh
S=$PWD/perf/game; cd examples/game          # as the stand runs it
python -m ingots.perf $S/scenarios/get-own-profile.py perf seed   # work/seed.csv
python -m ingots.perf $S/scenarios/get-own-profile.py \
    --config PERF_RUN=20261118-174448-bee --config PERF_ROLE=baseline \
    --config PERF_ROUND=1 ... perf point --groups 8
python -m ingots.perf $S/scenarios/get-own-profile.py perf analyze \
    20261118-174448-bee                       # reports/get-own-profile/
python -m ingots.perf $S/scenarios/get-own-profile.py perf smoke
```

The runner, from the meta repository, where it lives; an addon keeps
`perf-build`, what its stand builds a role by, and `perf-smoke`, which
needs no meta repository:

```sh
make -C perf run STAND=ingot-auth/perf/game
make -C perf run STAND=ingot-auth/perf/game SCENARIOS=duel \
    ARGS="--config PERF_BASELINE=v0.7.1 --config DUEL_THINK_MS=0"
make perf-smoke                  # in the addon, in CI, after its compose up
```

`make -C perf run` calls `perf/run <stand> $(SCENARIOS) -- $(ARGS)`: the configs of the run taken from `plan`, `eval "$(stand
perf <module> plan)"`, the files read and their order kept by the
project alone; the host checked, then for each round and role the
worktree of its ref, `eval "$(stand up <tree>)"`, `seed`, `point` for each
value of `PERF_GROUPS` on `PERF_LOAD_CPUS`, `stand down <tree>`; at the
end `analyze`. `ARGS` go to every command.

`stand` of the game, the stand of Compose of the meta repository given
its example and its file:

```sh
#!/usr/bin/env bash
here=$(cd "$(dirname "$0")" && pwd)
meta=${INGOTS_META:-$(git -C "$here" rev-parse --show-toplevel)/..}
exec "$meta/perf/compose-stand" --stand "$here" --example examples/game \
    --file docker-compose.perf.yml "$@"
```

The prototype, [`perf/`](perf/), runs a stand of two scenarios against a
game in memory: the configs of the files and the command line, the seed
and its rows read back, the points of both roles, the time between two
clients of a group, the analysis, a dry point, a module refused;
`mistakes.py` holds what mypy refuses: an action not named by a `str`,
a field the row has not, a state of another group, a client of another
group among the clients of a group, what is no client among them, a
group of the rows of another seed, a seed of another type. It keeps
the first shape of the design, the seed `_seed()` of the unit; the code
made it `CsvSeed` in the slot `seed`, as this text tells.

## Alternatives

- The runner in `ingots.perf`, Docker, git and systemd driven from
  Python: assumptions of a host in a library, not testable without them;
  the framework says what and how to load, the runner how to run it.
- One runner bringing every stand up by Compose, reading the example of
  the stand from its `perf.ini`: a stand of another shape, two targets, a
  dump, a process off Docker, would grow flags in the runner for each;
  the runner calls `stand`, and a stand is what it needs.
- Hooks of a stand around the steps of one runner: the same runner with
  its order fixed, the flags moved into files.
- `stand` a project of ingots, its steps slots: kept for when a stand
  outgrows a script; the contract does not change.
- A stand of its own, configured by its own file: a second way to
  configure, to override, to log; a project is what every addon already
  is.
- TOML: `tomllib` reads but does not write, the INI of a report would
  need `tomli-w`; INI is read by ingots already, `configparser` writes
  it, and the configs parse strings anyway. JSON is not a format of
  configs written by hand.
- k6, locust: their scenarios in JS or apart from the clients and the
  configs of the scenarios project; locust made for HTTP.
- ghz as the client: a scenario of the game needs its state, a player
  signed in; kept as a check of the transport.
- A class a scenario, the call of one client timed: clients that meet
  would not fit; a client and a group of them do.
- The group a tuple of the classes of its clients, `group = (Inviter,
  Invitee)`, sharing an untyped state: a class of the group types what
  its clients share and checks that each is of it.
- Many scenarios in one module, named in a file: two names for one
  thing; a module a scenario names it once.
- Actions by decorated methods, as locust's tasks: names made of
  methods; `measure()` names what it measures where it does.
- A seed written into the storages directly: the data the way the seed
  writes it, not the application, and a seed of each storage and of
  each version of its schema; kept for the volumes the API makes too
  slowly, later.
- A seed shared by the roles and the rounds: their volumes go down with
  them.
- Parameters of a scenario as a dataclass checked against a table: the
  configs of a project are that already, typed, overridden alike.
- The baseline fixed in `perf.ini`: an edit after every release;
  `latest` follows the tags.
- One report of a stand for all its scenarios: a scenario shaping its
  own could not; a report a scenario and run can.
- The time of a run from its file or its commit: git keeps neither.

## Open questions

None for now.

## Slices

1. ingots: `ListConfig`, a pull request of its own; `ingots.perf`,
   `PerfUnit`, `LoadGroup`, `LoadClient`, `PerfConfigs`, the commands
   `seed`, `point`, `load`, `smoke`, `plan`, `CsvReport`, stories 2–10,
   12; its first consumer `perf/game` of ingot-auth, its
   scenarios dry in CI after its compose up.
2. ingots: `analyze`, `MedianAnalysis`, story 11; ingots-libs: `perf/`,
   the runner in bash, stories 1, 13–16; the game moved onto both, its
   stand of bash in ingot-auth removed, its first `results.csv` split
   into the report of its first run; a run of 0.8.0 against itself
   matching it.
3. ingot-grpcio: `examples/echo/`, `perf/echo/`, stories 17,
   18; its first run beside the game.
4. Later: py-spy, ghz, the storages and the cache.
