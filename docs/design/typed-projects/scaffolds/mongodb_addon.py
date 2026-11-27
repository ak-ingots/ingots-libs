"""ingot-pymongo, in short: its configs and settings, a client, its project."""

from ingots_stub import Configs, Entity, Project, SettingsUnit, Slot, Unit


class MongoDbConfigs(Configs):
    MONGODB_URL: str = "mongodb://localhost"


class MongoDbSettingsUnit(SettingsUnit):
    configs = Slot(MongoDbConfigs)


class MongoDbClient(Entity):
    """A database in memory, its collections of documents."""

    project: "MongoDbProject"

    def __init__(self) -> None:
        self.collections: dict[str, list[dict[str, object]]] = {}

    @property
    def url(self) -> str:
        return self.project.settings.configs.MONGODB_URL


class MongoDbUnit(Unit):
    client = Slot(MongoDbClient)


class MongoDbProject(Project):
    settings = Slot(MongoDbSettingsUnit)
    mongodb = Slot(MongoDbUnit)
