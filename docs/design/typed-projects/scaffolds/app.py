"""
Two applications: a game on the starter, overriding what differs only; a
site of its own composition, the joins its own, the method and the storage
bound by itself.
"""

from auth_addon import (
    AuthGameConfigs,
    AuthGameProject,
    AuthGameSettingsUnit,
    AuthMongoDbConfigs,
    AuthMongoDbProject,
    AuthMongoDbSettingsUnit,
    AuthMethodsUnit,
    AuthMongoDbStorage,
    AuthNicknameConfigs,
    AuthNicknameMethod,
    AuthNicknameProject,
    AuthNicknameSettingsUnit,
    AuthUnit,
)
from ingots_stub import Entity, Slot, Unit

# -- the game: the starter --------------------------------------------------


class GameConfigs(AuthGameConfigs):
    AUTH_SESSIONS_MAX = 1  # a player plays from one device


class GameSettingsUnit(AuthGameSettingsUnit):
    configs = Slot(GameConfigs)


class GameScores(Entity):
    project: "GameProject"

    async def enrol(self, nickname: str) -> str:
        return await self.project.auth.methods.nickname.sign_up(nickname)


class GameUnit(Unit):
    scores = Slot(GameScores)


class GameProject(AuthGameProject):
    settings = Slot(GameSettingsUnit)
    game = Slot(GameUnit)


# -- the site: its own composition ------------------------------------------


class SiteConfigs(AuthNicknameConfigs, AuthMongoDbConfigs):
    pass


class SiteSettingsUnit(AuthNicknameSettingsUnit, AuthMongoDbSettingsUnit):
    configs = Slot(SiteConfigs)


class SiteMethodsUnit(AuthMethodsUnit):
    nickname = Slot(AuthNicknameMethod)


class SiteAuthUnit(AuthUnit):
    storage = Slot(AuthMongoDbStorage)
    methods = Slot(SiteMethodsUnit)


class SiteProject(AuthNicknameProject, AuthMongoDbProject):
    settings = Slot(SiteSettingsUnit)
    auth = Slot(SiteAuthUnit)
