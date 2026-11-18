"""The lines mypy refuses: what the author of a scenario cannot get wrong."""

import dataclasses

from app_stub import ScenariosProject
from ingots_stub import Slot
from perf_stub import LoadClient, LoadGroup, PerfUnit


@dataclasses.dataclass
class SeededPlayer:
    token: str


@dataclasses.dataclass
class SeededPair:
    inviter_token: str


class Player(LoadClient[ScenariosProject, "PlayerGroup"]):
    async def run(self) -> None:
        async with self.measure(1):  # error: an action is named by a str
            await self.project.game.get_own_profile(self.group.seeded.nickname)  # error: no nickname
        self.project.perf  # error: the project of the scenario has no unit perf
        self.group.duels  # error: a state of another group


class Inviter(LoadClient[ScenariosProject, "PairGroup"]):
    async def run(self) -> None:
        pass


class PlayerGroup(LoadGroup[SeededPlayer]):
    clients = (Player,)


class PairGroup(LoadGroup[SeededPair]):
    clients = (Inviter,)


class MixedGroup(LoadGroup[SeededPlayer]):
    clients = (Player, Inviter)  # error: a client of another group


class NotAClientGroup(LoadGroup[SeededPlayer]):
    clients = (SeededPlayer,)  # error: not a client of the load


class MixedPerf(PerfUnit[SeededPlayer]):
    group = PairGroup  # error: a group of the rows of another seed

    async def _seed(self, groups: int) -> list[SeededPair]:  # error: rows of another type
        return []


class PerfProject(ScenariosProject):
    perf = Slot(int)  # error: not an entity
