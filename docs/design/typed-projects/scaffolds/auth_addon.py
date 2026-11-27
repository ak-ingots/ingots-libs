"""
ingot-auth, in short, a section per module: the core and its project; two
methods, each with the project it needs, its configs mixed in; the storage
on MongoDB, with the project of both addons; the starter of a game, a
project joining them all, the methods and the storage bound.
"""

import abc
import typing as t

from ingots_stub import Configs, Entity, Project, SettingsUnit, Slot, Unit
from mongodb_addon import MongoDbConfigs, MongoDbProject, MongoDbSettingsUnit

# -- ingot_auth: the core -----------------------------------------------------


class AuthConfigs(Configs):
    AUTH_SESSIONS_MAX: int = 10


class AuthSettingsUnit(SettingsUnit):
    configs = Slot(AuthConfigs)


class BaseAuthStorage(Entity):
    @abc.abstractmethod
    async def add_profile(self, nickname: str) -> str:
        raise NotImplementedError


class AuthMemoryStorage(BaseAuthStorage):
    def __init__(self) -> None:
        self.profiles: list[str] = []

    @t.override
    async def add_profile(self, nickname: str) -> str:
        self.profiles.append(nickname)
        return f"memory:{len(self.profiles)}"


class AuthMethodsUnit(Unit):
    """No method is bound until an application, or its starter, binds it."""


class AuthUnit(Unit):
    storage: Slot[BaseAuthStorage] = Slot(AuthMemoryStorage)
    methods = Slot(AuthMethodsUnit)


class AuthProject(Project):
    settings = Slot(AuthSettingsUnit)
    auth = Slot(AuthUnit)


# -- ingot_auth.methods.nickname ----------------------------------------------


class AuthNicknameConfigs(AuthConfigs):
    AUTH_SIGN_UP_NICKNAME_ENABLED: bool = True


class AuthNicknameSettingsUnit(AuthSettingsUnit):
    configs = Slot(AuthNicknameConfigs)


class AuthNicknameProject(AuthProject):
    """What the method needs of a project: its configs mixed in."""

    settings = Slot(AuthNicknameSettingsUnit)


class AuthNicknameMethod(Entity):
    project: "AuthNicknameProject"

    async def sign_up(self, nickname: str) -> str:
        if not self.project.settings.configs.AUTH_SIGN_UP_NICKNAME_ENABLED:
            raise PermissionError("the sign-up by a nickname is closed")
        return await self.project.auth.storage.add_profile(nickname)


# -- ingot_auth.methods.email_code --------------------------------------------


class AuthEmailCodeConfigs(AuthConfigs):
    AUTH_EMAIL_CODE_TTL: int = 600


class AuthEmailCodeSettingsUnit(AuthSettingsUnit):
    configs = Slot(AuthEmailCodeConfigs)


class AuthEmailCodeProject(AuthProject):
    settings = Slot(AuthEmailCodeSettingsUnit)


class AuthEmailCodeMethod(Entity):
    project: "AuthEmailCodeProject"

    def get_code_ttl(self) -> int:
        return self.project.settings.configs.AUTH_EMAIL_CODE_TTL


# -- ingot_auth.contrib.storages.mongodb --------------------------------------


class AuthMongoDbConfigs(AuthConfigs, MongoDbConfigs):
    pass


class AuthMongoDbSettingsUnit(AuthSettingsUnit, MongoDbSettingsUnit):
    configs = Slot(AuthMongoDbConfigs)


class AuthMongoDbProject(AuthProject, MongoDbProject):
    """What the storage needs of a project: both addons, their settings joined."""

    settings = Slot(AuthMongoDbSettingsUnit)


class AuthMongoDbStorage(BaseAuthStorage):
    project: "AuthMongoDbProject"

    @t.override
    async def add_profile(self, nickname: str) -> str:
        profiles = self.project.mongodb.client.collections.setdefault("profiles", [])
        profiles.append({"nickname": nickname})
        return f"mongodb:{len(profiles)}"


# -- ingot_auth.contrib.starters.game -----------------------------------------


class AuthGameConfigs(AuthNicknameConfigs, AuthEmailCodeConfigs, AuthMongoDbConfigs):
    pass


class AuthGameSettingsUnit(
    AuthNicknameSettingsUnit, AuthEmailCodeSettingsUnit, AuthMongoDbSettingsUnit
):
    configs = Slot(AuthGameConfigs)


class AuthGameMethodsUnit(AuthMethodsUnit):
    nickname = Slot(AuthNicknameMethod)
    email_code = Slot(AuthEmailCodeMethod)


class AuthGameUnit(AuthUnit):
    storage = Slot(AuthMongoDbStorage)
    methods = Slot(AuthGameMethodsUnit)


class AuthGameProject(AuthNicknameProject, AuthEmailCodeProject, AuthMongoDbProject):
    """The joins written once, here: an application inherits them."""

    settings = Slot(AuthGameSettingsUnit)
    auth = Slot(AuthGameUnit)
