"""An addon of the prototype: a project with a cache, its client a component."""

from ingots_stub import Client, Configs, Project


class CacheConfigs(Configs):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379


class CacheProject(Project):
    _redis: Client
    configs: CacheConfigs

    def __init__(self) -> None:
        super().__init__()
        self.configs = CacheConfigs()

    async def get_redis(self) -> Client:
        try:
            return self._redis
        except AttributeError:
            c = self.configs
            self._redis = self._create_client(c.REDIS_HOST, c.REDIS_PORT)
            return self._redis
