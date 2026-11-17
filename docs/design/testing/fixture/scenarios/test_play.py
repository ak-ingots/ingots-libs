from testing_stub import ProjectFixture, ProjectTestCase

from . import ScenariosProject


class PlayScenario(ProjectTestCase):
    project = ProjectFixture(ScenariosProject)

    async def test_a_player_reaches_the_game_of_the_run(self) -> None:
        game = await self.project.get_game()
        self.assertEqual(await game.call("sign up"), "sign up at game.local:50061")
        self.assertEqual(self.project.configs.MAILPIT_URL, "http://mailpit.local:8025")
