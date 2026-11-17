"""
The scenarios of a game, a project of their own, a client of the game:
``python -m scenarios testing run --config GAME_PORT=50061``, or ``GAME_TEST_*`` in
the environment, as any project of Ingots is configured.
"""

from ingots_stub import Client, Configs
from testing_stub import TestingProject


class ScenariosConfigs(Configs):
    GAME_HOST: str = "localhost"
    GAME_PORT: int = 50051
    MAILPIT_URL: str = "http://localhost:8025"


class ScenariosProject(TestingProject):
    env_configs_prefix = "GAME_TEST"
    _game: Client
    configs: ScenariosConfigs

    def __init__(self) -> None:
        super().__init__()
        self.configs = ScenariosConfigs()

    async def get_game(self) -> Client:
        try:
            return self._game
        except AttributeError:
            c = self.configs
            self._game = self._create_client(c.GAME_HOST, c.GAME_PORT)
            return self._game
