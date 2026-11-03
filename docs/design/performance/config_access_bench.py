import asyncio
import os
import timeit
import typing as t
from unittest import mock

from ingots.defaults import Project
from ingots.defaults.settings import Settings
from ingots.defaults.settings.configs import Configs, IntConfig
from ingots.puer import Slot, Unit


def make(n_configs: int, n_units: int) -> type[Project]:
    configs = type("BigConfigs", (Configs,), {f"X_{i}_VALUE": IntConfig(i) for i in range(n_configs)})
    settings = type("BigSettings", (Settings,), {"configs": Slot(configs)})
    ns: dict[str, t.Any] = {"settings": Slot(settings)}
    for i in range(n_units):
        ns[f"unit_{i}"] = Slot(type(f"Unit{i}", (Unit,), {}))
    return type("BigProject", (Project,), ns)


class Holder:
    def __init__(self, project: Project) -> None:
        import weakref
        self._ref = weakref.ref(project)

    @property
    def project(self) -> Project:
        p = self._ref()
        assert p is not None
        return p


def bench(n_configs: int, n_units: int) -> None:
    with mock.patch.dict(os.environ, {"INGOT_IS_PRINT_CONFIGS": "off", f"INGOT_X_{n_configs - 1}_VALUE": "7"}, clear=True), mock.patch("logging.config.dictConfig"):
        project = make(n_configs, n_units)()
        asyncio.run(project._configure())
    holder = Holder(project)
    name = f"X_{n_configs - 1}_VALUE"
    configs = project.settings.configs
    assert getattr(configs, name) == 7
    chain = eval(f"lambda: holder.project.settings.configs.{name}", {"holder": holder})
    direct = eval(f"lambda: configs.{name}", {"configs": configs})
    plain = {"v": 7}
    local = lambda: plain["v"]
    n = 1_000_000
    for label, fn in [("holder.project.settings.configs.X", chain), ("configs.X (cached configs)", direct), ("dict lookup (baseline)", local)]:
        best = min(timeit.repeat(fn, number=n, repeat=5)) / n * 1e9
        print(f"  {label:36} {best:6.0f} ns")


for n_configs, n_units in [(6, 1), (500, 20)]:
    print(f"{n_configs} configs, {n_units} units:")
    bench(n_configs, n_units)
