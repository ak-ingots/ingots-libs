"""The lines mypy refuses: what a typed project lets no one write."""

from auth_addon import (
    AuthEmailCodeProject,
    AuthNicknameProject,
    AuthProject,
    AuthSettingsUnit,
)
from ingots_stub import Entity, Slot


class Forgotten(AuthNicknameProject, AuthEmailCodeProject):  # error: no join
    pass


class LostConfigs(AuthNicknameProject):
    settings = Slot(AuthSettingsUnit)  # error: the configs of the method lost


class UntypedStorage(Entity):
    project: AuthProject

    def count(self) -> int:
        return len(self.project.mongodb.client.collections)  # error: no MongoDB
