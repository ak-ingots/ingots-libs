"""
The proposal, ``ingots.perf``: what is loaded and how, against a target
already up. A scenario is a module, its ``PerfProject`` a project with the
unit ``perf``: the group of its clients, its seed, its report, its
analysis. The commands ``seed``, ``point``, ``smoke``, ``analyze``; in
ingots ``point`` starts a process of the load, ``load``, a bucket of the
groups each, here a task each.
"""

import abc
import asyncio
import contextlib
import csv
import dataclasses
import importlib.util
import shlex
import statistics
import tempfile
import time
import typing as t
from collections.abc import AsyncIterator
from pathlib import Path

from ingots_stub import Configs, Entity, Project, Slot, Unit


class ScenarioModuleError(Exception):
    """A module of a scenario gives no ``PerfProject`` a run can take."""


class SmokeFailedError(Exception):
    """A dry point found a client that measured nothing or erred."""


class PerfConfigs(Configs):
    """The configs of a run, ``PERF_*``, joined to those of the client."""

    PERF_SCENARIO: str = ""  # the name of the module, set by the loader
    PERF_BASELINE: str = "latest"
    PERF_CANDIDATE: str = "tree"
    PERF_ROUNDS: int = 3
    PERF_WARMUP: float = 10
    PERF_DURATION: float = 30
    PERF_LOAD_PROCS: int = 4
    PERF_GROUPS: tuple[int, ...] = (1, 2, 4, 8, 16)
    PERF_MIN_CALLS: int = 20
    PERF_WORK: str = "."
    PERF_SEED_FILE: str = ""  # seed.csv of PERF_WORK by default
    PERF_REPORTS: str = "reports"
    # of a point, told by the runner
    PERF_RUN: str = ""
    PERF_ROLE: str = "candidate"
    PERF_ROUND: int = 1


@dataclasses.dataclass
class Call:
    action: str
    latency: float
    error: str = ""


class Recorder:
    """The calls of a point ending in its measured window."""

    def __init__(self, start: float, end: float) -> None:
        self.start, self.end = start, end
        self.calls: list[Call] = []

    def record(self, action: str, begun: float, done: float, error: str = "") -> None:
        if begun >= self.start and done <= self.end:
            self.calls.append(Call(action, done - begun, error))


class LoadGroup[R]:
    """
    The clients that meet in a point, one of each class of ``clients``, a
    class twice for two, and what they share: the row of the seed the group
    takes, a time one starts and another finishes, the state a subclass
    declares. An instance a group of a point, in one process of the load.
    """

    clients: tuple[type["LoadClient[t.Any, t.Self]"], ...] = ()

    def __init__(self, seeded: R, recorder: Recorder) -> None:
        self.seeded = seeded
        self._recorder = recorder
        self._started: dict[tuple[str, str], float] = {}

    async def asyncSetUp(self) -> None:
        """The group set up before its clients, unmeasured."""

    def start(self, action: str, key: str) -> None:
        self._started[action, key] = time.monotonic()

    def finish(self, action: str, key: str) -> None:
        begun = self._started.pop((action, key))
        self._recorder.record(action, begun, time.monotonic())


class LoadClient[P: Project, G: LoadGroup[t.Any]](abc.ABC):
    """
    A user of the application, an instance a client of a point: its
    set-up unmeasured, then its ``run()`` again and again; ``P`` its
    project, the ``PerfProject`` of the scenario, ``G`` its group.
    """

    def __init__(self, project: P, group: G) -> None:
        self.project = project
        self.group = group

    async def asyncSetUp(self) -> None:
        pass

    @abc.abstractmethod
    async def run(self) -> None:
        raise NotImplementedError

    @contextlib.asynccontextmanager
    async def measure(self, action: str) -> AsyncIterator[None]:
        begun = time.monotonic()
        try:
            yield
        except Exception as error:
            self.group._recorder.record(action, begun, time.monotonic(), type(error).__name__)
        else:
            self.group._recorder.record(action, begun, time.monotonic())


Row = dict[str, str]


class CsvReport(Entity):
    """The CSV of a run, the data alone, and its INI, the run."""

    FIELDS: t.ClassVar[tuple[str, ...]] = (
        "role", "round", "action", "groups", "metric", "value",
    )  # fmt: skip

    def append(self, path: Path, rows: list[Row]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not path.exists()
        with path.open("a", newline="") as file:
            writer = csv.DictWriter(file, self.FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerows(rows)

    def read(self, path: Path) -> list[Row]:
        with path.open(newline="") as file:
            return list(csv.DictReader(file))


class MedianAnalysis(Entity):
    """The candidate against the baseline, by the median of the rounds."""

    METRICS: t.ClassVar[tuple[str, ...]] = ("rps", "p50_ms")

    def analyze(self, rows: list[Row]) -> list[str]:
        values: dict[tuple[str, int, str, str], list[float]] = {}
        for row in rows:
            if row["metric"] in self.METRICS:
                key = (row["action"], int(row["groups"]), row["metric"], row["role"])
                values.setdefault(key, []).append(float(row["value"]))
        lines = []
        for action, groups, metric in sorted({k[:3] for k in values}):
            baseline = values.get((action, groups, metric, "baseline"))
            candidate = values.get((action, groups, metric, "candidate"), [0.0])
            if not baseline:
                lines.append(f"{action} {groups} {metric}: the candidate alone")
                continue
            old, new = statistics.median(baseline), statistics.median(candidate)
            change = (new / old - 1) * 100 if old else 0.0
            lines.append(f"{action} {groups} {metric}: {old:.1f} -> {new:.1f} ({change:+.1f}%)")
        return lines


class PerfUnit[R](Unit):
    """
    The unit ``perf`` of a scenario: its group of clients, its seed, rows
    of ``R``, a dataclass; its report and analysis in slots; its commands.
    """

    group: type[LoadGroup[R]]
    report = Slot(CsvReport)
    analysis = Slot(MedianAnalysis)

    async def _seed(self, groups: int) -> list[R]:
        """The rows a scenario needs ahead, made through the API; none by default."""
        return []

    # the commands

    async def seed(self) -> None:
        rows = await self._seed(max(self._configs.PERF_GROUPS))
        if not rows:
            return
        fields = [field.name for field in dataclasses.fields(t.cast(t.Any, rows[0]))]
        with self._seed_file.open("w", newline="") as file:
            writer = csv.DictWriter(file, fields)
            writer.writeheader()
            writer.writerows(dataclasses.asdict(t.cast(t.Any, row)) for row in rows)

    async def point(self, groups: int) -> list[Row]:
        configs = self._configs
        start = time.monotonic() + configs.PERF_WARMUP
        recorder = Recorder(start, start + configs.PERF_DURATION)
        seeded = self._read_seed()
        buckets = [range(i, groups, configs.PERF_LOAD_PROCS) for i in range(configs.PERF_LOAD_PROCS)]
        # a bucket a process of the load in ingots: a group never over two
        await asyncio.gather(
            *(self._run_group(i, seeded, recorder) for bucket in buckets for i in bucket)
        )  # fmt: skip
        rows = self._measure(recorder, groups)
        path = Path(configs.PERF_REPORTS, configs.PERF_SCENARIO, f"{configs.PERF_RUN}.csv")
        self.report.append(path, rows)
        return rows

    async def smoke(self) -> None:
        """A point dry: a group, no warmup, a run of each client, in a directory apart."""
        configs = self._configs
        with tempfile.TemporaryDirectory() as work:
            configs.PERF_WORK, configs.PERF_SEED_FILE = work, ""
            configs.PERF_GROUPS = (1,)
            await self.seed()
            recorder = Recorder(0, float("inf"))
            clients = await self._create_clients(0, self._read_seed(), recorder)
            for client in clients:
                await client.run()
        failed = [call for call in recorder.calls if call.error]
        if failed or not recorder.calls:
            raise SmokeFailedError(f"{configs.PERF_SCENARIO}: {failed or 'no call'}")
        path = Path(configs.PERF_REPORTS, "dry", configs.PERF_SCENARIO, f"{configs.PERF_RUN}.csv")
        self.report.append(path, self._measure(recorder, 1, min_calls=1))

    def plan(self) -> str:
        """The configs of a run resolved, for the shell of the runner: ``eval``."""
        configs = self._configs
        lines = []
        for name in t.get_type_hints(PerfConfigs):
            value = getattr(configs, name)
            text = " ".join(map(str, value)) if isinstance(value, tuple) else str(value)
            lines.append(f"{name}={shlex.quote(text)}")
        return "\n".join(lines)

    def analyze(self, path: Path) -> list[str]:
        return self.analysis.analyze(self.report.read(path))

    # the flow

    @property
    def _configs(self) -> PerfConfigs:
        return t.cast(PerfConfigs, self.project.settings.configs)

    @property
    def _seed_file(self) -> Path:
        configs = self._configs
        return Path(configs.PERF_SEED_FILE or Path(configs.PERF_WORK, "seed.csv"))

    def _read_seed(self) -> list[R]:
        if not self._seed_file.exists():
            return []
        cls = self._get_row_type()
        hints = t.get_type_hints(cls)
        with self._seed_file.open(newline="") as file:
            return [
                cls(**{name: hints[name](value) for name, value in row.items()})
                for row in csv.DictReader(file)
            ]

    def _get_row_type(self) -> type[R]:
        for base in type(self).__mro__:
            for orig in getattr(base, "__orig_bases__", ()):
                if t.get_origin(orig) is PerfUnit:
                    return t.cast(type[R], t.get_args(orig)[0])
        raise TypeError(f"{type(self).__qualname__}: no row type")

    async def _create_clients(
        self, index: int, seeded: list[R], recorder: Recorder
    ) -> list[LoadClient[t.Any, t.Any]]:
        row = seeded[index % len(seeded)] if seeded else t.cast(R, None)
        group = self.group(row, recorder)
        await group.asyncSetUp()
        clients = [cls(self.project, group) for cls in group.clients]
        for client in clients:
            await client.asyncSetUp()
        return clients

    async def _run_group(self, index: int, seeded: list[R], recorder: Recorder) -> None:
        clients = await self._create_clients(index, seeded, recorder)

        # the window over, a client is cancelled, waiting on its rival or not
        deadline = asyncio.get_running_loop().time() + recorder.end - time.monotonic()

        async def run(client: LoadClient[t.Any, t.Any]) -> None:
            with contextlib.suppress(TimeoutError):
                async with asyncio.timeout_at(deadline):
                    while True:
                        await client.run()

        async with asyncio.TaskGroup() as tasks:
            for client in clients:
                tasks.create_task(run(client))

    def _measure(self, recorder: Recorder, groups: int, min_calls: int | None = None) -> list[Row]:
        configs = self._configs
        duration = configs.PERF_DURATION
        common = {"role": configs.PERF_ROLE, "round": str(configs.PERF_ROUND), "groups": str(groups)}
        rows = []
        for action in sorted({call.action for call in recorder.calls}):
            calls = [c for c in recorder.calls if c.action == action]
            latencies = sorted(c.latency * 1000 for c in calls if not c.error)
            metrics: dict[str, object] = {"calls": len(latencies), "rps": len(latencies) / duration}
            for call in calls:
                if call.error:
                    key = f"errors_{call.error}"
                    metrics[key] = t.cast(int, metrics.get(key, 0)) + 1
            if len(latencies) > 1:
                cuts = statistics.quantiles(latencies, n=100, method="inclusive")
                metrics |= {"p50_ms": cuts[49], "p95_ms": cuts[94], "p99_ms": cuts[98]}
            least = configs.PERF_MIN_CALLS if min_calls is None else min_calls
            metrics["void"] = f"calls {len(latencies)}" if len(latencies) < least else ""
            rows += [common | {"action": action, "metric": m, "value": str(v)} for m, v in metrics.items()]
        return rows


def load_scenario(path: Path) -> type[Project]:
    """
    The ``PerfProject`` of the module of a scenario, loaded by its path, not
    as a package; refused unless a project with the unit ``perf`` and the
    configs of a run.
    """
    spec = importlib.util.spec_from_file_location(f"perf_scenario_{path.stem.replace('-', '_')}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project = getattr(module, "PerfProject", None)
    perf = getattr(project, "perf", None)
    if not (
        isinstance(project, type)
        and issubclass(project, Project)
        and isinstance(perf, Slot)
        and issubclass(perf.cls, PerfUnit)
    ):
        raise ScenarioModuleError(f"{path}: no PerfProject, a project with the unit perf")
    return project


def create_scenario(
    path: Path, files: t.Sequence[Path] = (), configs: t.Sequence[tuple[str, str]] = ()
) -> PerfUnit[t.Any]:
    """The unit ``perf`` of a scenario, its project configured as a command does."""
    project = load_scenario(path)()
    project.configure(files, [("PERF_SCENARIO", path.stem), *configs])
    if not isinstance(project.settings.configs, PerfConfigs):
        raise ScenarioModuleError(f"{path}: the configs of the project are no PerfConfigs")
    return t.cast(PerfUnit[t.Any], t.cast(t.Any, project).perf)
