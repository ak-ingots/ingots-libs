"""Clients that meet: one invites, its rival accepts, the time between measured."""

import asyncio
import dataclasses

from app_stub import ScenariosConfigs, ScenariosProject, ScenariosSettingsUnit
from app_stub import sign_up_and_in
from ingots_stub import Slot
from perf_stub import LoadClient, LoadGroup, PerfConfigs, PerfUnit


class DuelConfigs(ScenariosConfigs, PerfConfigs):
    DUEL_THINK_MS: int = 0  # a parameter of the scenario, a config


class DuelSettings(ScenariosSettingsUnit):
    configs = Slot(DuelConfigs)


@dataclasses.dataclass
class SeededPair:
    inviter_token: str
    invitee_nickname: str
    invitee_token: str


class Inviter(LoadClient["PerfProject", "DuelGroup"]):
    async def run(self) -> None:
        seeded = self.group.seeded
        async with self.measure("invite"):
            key = await self.project.game.invite(
                seeded.inviter_token, seeded.invitee_nickname
            )
        self.group.start("invited-to-accepted", key)  # finished by the rival
        await asyncio.sleep(0.001)


class Invitee(LoadClient["PerfProject", "DuelGroup"]):
    async def run(self) -> None:
        key = await self.project.game.accept_next(self.group.seeded.invitee_token)
        self.group.finish("invited-to-accepted", key)
        self.group.duels += 1
        await asyncio.sleep(self.project.settings.configs.DUEL_THINK_MS / 1000)


class DuelGroup(LoadGroup[SeededPair]):
    """The two of a duel, and the duels they played, a state of their own."""

    clients = (Inviter, Invitee)

    async def asyncSetUp(self) -> None:
        self.duels = 0


class DuelPerf(PerfUnit[SeededPair]):
    project: "PerfProject"
    group = DuelGroup

    async def _seed(self, groups: int) -> list[SeededPair]:
        pairs = []
        for _ in range(groups):
            _, inviter_token = await sign_up_and_in(self.project)
            pairs.append(SeededPair(inviter_token, *await sign_up_and_in(self.project)))
        return pairs


class PerfProject(ScenariosProject):
    settings = Slot(DuelSettings)
    perf = Slot(DuelPerf)
