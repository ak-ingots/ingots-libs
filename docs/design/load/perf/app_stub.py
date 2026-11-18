"""
The application loaded and the project of its scenarios, as the game and
``examples/game/scenarios`` are: a server in memory, its client, the
configs of the client.
"""

import asyncio
import itertools
import uuid

from ingots_stub import Configs, Entity, Project, SettingsUnit, Slot


class Unauthenticated(Exception):
    """The status of a call with a token the server does not know."""


class GameServer:
    """The game: players signed up and in, invitations between them."""

    def __init__(self) -> None:
        self.passwords: dict[str, str] = {}
        self.tokens: dict[str, str] = {}
        self.invitations: dict[str, asyncio.Queue[str]] = {}
        self.keys = itertools.count()

    async def sign_up(self, nickname: str, password: str) -> None:
        await asyncio.sleep(0)
        self.passwords[nickname] = password
        self.invitations[nickname] = asyncio.Queue()

    async def sign_in(self, nickname: str, password: str) -> str:
        await asyncio.sleep(0)
        assert self.passwords[nickname] == password
        token = uuid.uuid4().hex
        self.tokens[token] = nickname
        return token

    async def get_own_profile(self, token: str) -> str:
        await asyncio.sleep(0)
        try:
            return self.tokens[token]
        except KeyError:
            raise Unauthenticated from None

    async def invite(self, token: str, nickname: str) -> str:
        await asyncio.sleep(0)
        key = f"{self.tokens[token]}-{next(self.keys)}"
        await self.invitations[nickname].put(key)
        return key

    async def accept_next(self, token: str) -> str:
        return await self.invitations[self.tokens[token]].get()


# the one server of the prototype; a target over the network in ingots
SERVER = GameServer()


class GameClient(Entity):
    """The client of ingot-grpcio bound to the services of the game."""

    async def sign_up(self, nickname: str, password: str) -> None:
        await SERVER.sign_up(nickname, password)

    async def sign_in(self, nickname: str, password: str) -> str:
        return await SERVER.sign_in(nickname, password)

    async def get_own_profile(self, token: str) -> str:
        return await SERVER.get_own_profile(token)

    async def invite(self, token: str, nickname: str) -> str:
        return await SERVER.invite(token, nickname)

    async def accept_next(self, token: str) -> str:
        return await SERVER.accept_next(token)


class ScenariosConfigs(Configs):
    GRPC_DEFAULT_PORT: int = 50061


class ScenariosSettingsUnit(SettingsUnit):
    configs = Slot(ScenariosConfigs)


class ScenariosProject(Project):
    env_configs_prefix = "GAME_TEST"
    settings = Slot(ScenariosSettingsUnit)
    game = Slot(GameClient)


async def sign_up_and_in(project: ScenariosProject) -> tuple[str, str]:
    nickname = f"perf-{uuid.uuid4().hex[:8]}"
    await project.game.sign_up(nickname, "s3cret")
    return nickname, await project.game.sign_in(nickname, "s3cret")
