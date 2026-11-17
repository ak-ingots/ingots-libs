"""The tests of an addon: its project a fixture, configured by the test alone."""

import asyncio

from app import CacheProject
from testing_stub import ProjectFixture, ProjectTestCase

LOOPS: list[asyncio.AbstractEventLoop] = []


class CacheTestCase(ProjectTestCase):
    project = ProjectFixture(CacheProject, configs={"REDIS_PORT": "16380"})

    async def test_the_cache_is_the_server_of_the_tests(self) -> None:
        redis = await self.project.get_redis()
        self.assertEqual(await redis.call("ping"), "ping at localhost:16380")
        LOOPS.append(asyncio.get_running_loop())

    async def test_each_test_has_a_project_of_its_loop(self) -> None:
        redis = await self.project.get_redis()
        await redis.call("ping")
        LOOPS.append(asyncio.get_running_loop())


class ServerMixin:
    """A fixture of a mixin: the server of the tests of several cases."""

    server = ProjectFixture(CacheProject, configs={"REDIS_PORT": "1"})


class TwoProjectsTestCase(ServerMixin, ProjectTestCase):
    """A server and its client, two projects of one test."""

    client = ProjectFixture(CacheProject, configs={"REDIS_PORT": "2"})

    async def test_both_are_there(self) -> None:
        self.assertIsNot(self.server, self.client)
        self.assertEqual(self.client.configs.REDIS_PORT, 2)
