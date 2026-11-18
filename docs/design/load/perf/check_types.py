"""
Runs a stand as the runner and CI meet it: a scenario loaded by the path of
its module, configured by the files of the stand, the scenario's over the
stand's, the command line over both; seeded through the API, the rows read
back by the clients; a point, its groups over the processes, its clients
measured in the window, those of a group sharing a time; the report and
its analysis; a dry point; a module refused. mypy refuses the lines of
``mistakes.py``.
"""

import asyncio
import csv
import tempfile
from pathlib import Path

from perf_stub import ScenarioModuleError, create_scenario

STAND = Path("stand")
FILES = [STAND / "perf.ini"]
FAST = [("PERF_WARMUP", "0.02"), ("PERF_DURATION", "0.1"), ("PERF_LOAD_PROCS", "2")]


async def main() -> None:
    with tempfile.TemporaryDirectory() as work:
        out = [("PERF_WORK", work), ("PERF_REPORTS", f"{work}/reports")]

        # the configs: the stand's file, then the command line
        profile = create_scenario(
            STAND / "scenarios/get-own-profile.py",
            FILES,
            [*FAST, *out, ("PERF_GROUPS", "[1, 3]"), ("PERF_RUN", "r1")],
        )
        configs = profile._configs
        assert configs.PERF_ROUNDS == 3 and configs.PERF_GROUPS == (1, 3), configs
        assert configs.PERF_SCENARIO == "get-own-profile"

        # the seed: through the API, rows of a dataclass, read back typed
        await profile.seed()
        with open(f"{work}/seed.csv", newline="") as file:
            rows = list(csv.DictReader(file))
        assert len(rows) == 3 and list(rows[0]) == ["nickname", "token"], rows
        assert profile._read_seed()[2].token == rows[2]["token"]

        # the points of both roles, a round each, into the report of the run
        for role in ("baseline", "candidate"):
            profile._configs.PERF_ROLE = role
            for groups in configs.PERF_GROUPS:
                point = await profile.point(groups)
                calls = {r["metric"]: r["value"] for r in point}
                assert int(calls["calls"]) > 0 and calls["void"] == "", point
        report = Path(work, "reports/get-own-profile/r1.csv")
        lines = profile.analyze(report)
        assert any(line.startswith("get-own-profile 3 rps:") for line in lines), lines

        # the duel: its own file over the stand's, the command line over both
        duel = create_scenario(
            STAND / "scenarios/duel.py",
            [*FILES, STAND / "scenarios/duel.ini"],
            [*FAST, *out, ("PERF_RUN", "r1"), ("DUEL_THINK_MS", "0")],
        )
        dc = duel._configs
        assert dc.PERF_GROUPS == (1, 2, 4, 8) and dc.PERF_ROUNDS == 3, dc
        assert duel.project.settings.configs.DUEL_THINK_MS == 0  # type: ignore[attr-defined]
        await duel.seed()
        actions = {r["action"] for r in await duel.point(4)}
        # the time from one client of a group to the other is an action too
        assert actions == {"invite", "invited-to-accepted"}, actions
        # the baseline never ran it: the candidate alone, not a regression
        assert all("candidate alone" in line for line in duel.analyze(
            Path(work, "reports/duel/r1.csv")
        ))  # fmt: skip

        # a dry point: a group, a run of each client, its report apart
        dry = create_scenario(STAND / "scenarios/get-own-profile.py", FILES, [*out, ("PERF_RUN", "d1")])
        await dry.smoke()
        assert Path(work, "reports/dry/get-own-profile/d1.csv").exists()

    # a module without its PerfProject: refused, the module named
    try:
        create_scenario(Path("refused/scenarios/no-project.py"))
    except ScenarioModuleError as error:
        assert "no-project.py" in str(error), error
    else:
        raise AssertionError("a module without PerfProject was taken")
    print("the stand runs")


if __name__ == "__main__":
    asyncio.run(main())
