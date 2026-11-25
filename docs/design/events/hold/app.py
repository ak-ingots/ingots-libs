"""
The consumers, the code of an application: a subscriber of its own beside
the mail of the core, and one that fails; an operation of its own changing
the password and the nickname in one transaction, the change of the
password an operation of the auth it runs, knowing nothing of its event.
"""

import dataclasses
import typing as t

from auth_stub import (
    AuthCaller,
    AuthChangePasswordParameters,
    AuthPassword,
    AuthPasswordChanged,
    AuthProject,
    AuthUnit,
)
from ingots_stub import (
    BaseOperation,
    Factories,
    Factory,
    OperationMetadata,
    Permissions,
    Slot,
    Unit,
    run,
)


class GameAuditOperation(BaseOperation[AuthPasswordChanged, None]):
    """The audit of the game: what changed, for its own log."""

    project: "GameProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions()

    @t.override
    async def _run(self, parameters: AuthPasswordChanged, metadata: OperationMetadata) -> None:
        self.project.game.audit.append(f"password of {parameters.profile_uid}")


class GameBrokenOperation(BaseOperation[AuthPasswordChanged, None]):
    """A subscriber that fails: alone, logged."""

    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions()

    @t.override
    async def _run(self, parameters: AuthPasswordChanged, metadata: OperationMetadata) -> None:
        raise ConnectionError("the analytics are down")


class GamePassword(AuthPassword):
    ev_changed = Factories[BaseOperation[AuthPasswordChanged, None]](
        *AuthPassword.ev_changed.classes, GameAuditOperation, GameBrokenOperation
    )


class GameAuth(AuthUnit):
    password = Slot(GamePassword)


class GameStaffOperation(BaseOperation[AuthPasswordChanged, None]):
    """A subscriber of a permission the end user has not: of the staff."""

    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions({"game.staff": 1})

    @t.override
    async def _run(self, parameters: AuthPasswordChanged, metadata: OperationMetadata) -> None:
        pass


class GuardedPassword(AuthPassword):
    ev_changed = Factories[BaseOperation[AuthPasswordChanged, None]](
        *AuthPassword.ev_changed.classes, GameStaffOperation
    )


class GuardedAuth(AuthUnit):
    password = Slot(GuardedPassword)


class GuardedProject(AuthProject):
    """A subscriber its callers may not run: skipped, the others run."""

    auth = Slot(GuardedAuth)


class GameNicknameTakenError(Exception):
    pass


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GameUpdateParameters:
    password: AuthChangePasswordParameters
    nickname: str
    is_nickname_optional: bool = False


class GameUpdateOperation(BaseOperation[GameUpdateParameters, None]):
    """
    The password and the nickname together, in one transaction: the change
    of the password is the operation of the auth, run inside it. A nickname
    taken undoes both, unless it is optional: then the password stays.
    """

    project: "GameProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions()

    @t.override
    async def _run(self, parameters: GameUpdateParameters, metadata: OperationMetadata) -> None:
        auth = self.project.auth
        async with auth.storage.transaction():
            await run(auth.password.op_change, parameters.password, metadata.caller)
            try:
                self._set_nickname(metadata, parameters.nickname)
            except GameNicknameTakenError:
                if not parameters.is_nickname_optional:
                    raise

    def _set_nickname(self, metadata: OperationMetadata, nickname: str) -> None:
        state = self.project.auth.storage.state
        if any(profile.nickname == nickname for profile in state.profiles.values()):
            raise GameNicknameTakenError(nickname)
        caller = metadata.caller
        assert isinstance(caller, AuthCaller) and caller.profile_uid is not None
        state.profiles[caller.profile_uid].nickname = nickname


class GameUnit(Unit):
    op_update = Factory(GameUpdateOperation)

    def __init__(self) -> None:
        self.audit: list[str] = []


class GameProject(AuthProject):
    auth = Slot(GameAuth)
    game = Slot(GameUnit)
