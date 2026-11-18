"""A call with a token: a player signed in ahead, calling its profile."""

import dataclasses

from app_stub import ScenariosConfigs, ScenariosProject, ScenariosSettingsUnit
from app_stub import sign_up_and_in
from ingots_stub import Slot
from perf_stub import LoadClient, LoadGroup, PerfConfigs, PerfUnit


class GamePerfConfigs(ScenariosConfigs, PerfConfigs):
    pass


class GamePerfSettings(ScenariosSettingsUnit):
    configs = Slot(GamePerfConfigs)


@dataclasses.dataclass
class SeededPlayer:
    nickname: str
    token: str


class Player(LoadClient["PerfProject", "PlayerGroup"]):
    async def asyncSetUp(self) -> None:
        self.token = self.group.seeded.token

    async def run(self) -> None:
        async with self.measure("get-own-profile"):
            await self.project.game.get_own_profile(self.token)


class PlayerGroup(LoadGroup[SeededPlayer]):
    clients = (Player,)


class OwnProfilePerf(PerfUnit[SeededPlayer]):
    project: "PerfProject"
    group = PlayerGroup

    async def _seed(self, groups: int) -> list[SeededPlayer]:
        return [SeededPlayer(*await sign_up_and_in(self.project)) for _ in range(groups)]


class PerfProject(ScenariosProject):
    settings = Slot(GamePerfSettings)
    perf = Slot(OwnProfilePerf)
