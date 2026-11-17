"""The lines mypy refuses: what a consumer cannot get wrong."""

from app import CacheProject
from testing_stub import ProjectFixture, ProjectTestCase


class CacheTestCase(ProjectTestCase):
    project = ProjectFixture(CacheProject, configs={"REDIS_PORT": 16380})  # error: str
    other = ProjectFixture(int)  # error: not a project

    async def test_it(self) -> None:
        await self.project.get_mongo()  # error: a cache project has no MongoDB
        self.project.configs.REDIS_PORT = "1"  # error: an int
