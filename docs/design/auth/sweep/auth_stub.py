"""
The sessions of ingot-auth an operator ends, as slice 6 builds them, cut down
to what its consumers touch, in memory: every session of a profile revoked,
the expired ones swept, a page at a time, each change in the activity log.
"""

import abc
import contextlib
import dataclasses
import datetime
import enum
import typing as t
from collections.abc import AsyncIterator, Mapping

from ingots_stub import (
    BaseOperation,
    Caller,
    Entity,
    Factory,
    OperationMetadata,
    OperationsOwner,
    PermissionFlags,
    Permissions,
    PermissionsSlot,
    Project,
    Slot,
    Unit,
)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthCaller(Caller):
    session_uid: str


# the caller of what the server does by itself, a job of a schedule
AUTH_SYSTEM = Caller(uid="system", permissions=Permissions())


class AuthSessionStatus(enum.StrEnum):
    OPEN = "open"
    REVOKED = "revoked"
    EXPIRED_IDLE = "expired_idle"
    EXPIRED_ABSOLUTE = "expired_absolute"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthSessionRecord:
    uid: str
    profile_uid: str
    token_hash: str
    opened_at: datetime.datetime
    seen_at: datetime.datetime
    status: AuthSessionStatus = AuthSessionStatus.OPEN


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthActivityRecord:
    who: str
    action: str
    entity_type: str
    entity_uid: str
    context: Mapping[str, object]
    run_uid: str


# the storage


class AuthStorage(Entity):
    """The sessions by their uid, in order, and the log, in transactions."""

    def __init__(self) -> None:
        super().__init__()
        self.sessions: dict[str, AuthSessionRecord] = {}
        self.activities: list[AuthActivityRecord] = []
        self.transactions = 0

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        sessions, activities = dict(self.sessions), list(self.activities)
        self.transactions += 1
        try:
            yield
        except BaseException:
            self.sessions, self.activities = sessions, activities
            raise

    async def get_open(self, profile_uid: str) -> tuple[AuthSessionRecord, ...]:
        return tuple(
            session
            for session in self.sessions.values()
            if session.profile_uid == profile_uid
            and session.status is AuthSessionStatus.OPEN
        )

    async def get_all_open(
        self, after: str | None, limit: int
    ) -> tuple[AuthSessionRecord, ...]:
        """The open sessions by their uid, after the last of a page before."""
        found = sorted(
            (
                session
                for session in self.sessions.values()
                if session.status is AuthSessionStatus.OPEN
                and (after is None or session.uid > after)
            ),
            key=lambda session: session.uid,
        )
        return tuple(found[:limit])

    async def close(self, session_uid: str, status: AuthSessionStatus) -> None:
        session = self.sessions[session_uid]
        self.sessions[session_uid] = dataclasses.replace(session, status=status)


class AuthCache(Entity):
    """What a request reads first: the sessions and their callers by hash."""

    def __init__(self) -> None:
        super().__init__()
        self.forgotten: list[str] = []

    async def forget(self, token_hash: str) -> None:
        self.forgotten.append(token_hash)


# the log


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthActivityContext:
    pass


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthSessionExpired(AuthActivityContext):
    reason: str


class AuthActivitiesUnit(Unit):
    parent: "AuthUnit"

    @t.final
    async def record(
        self,
        unit: Unit,
        entity_uid: str,
        action: str,
        metadata: OperationMetadata,
        *,
        context: AuthActivityContext | None = None,
    ) -> None:
        self.parent.storage.activities.append(
            AuthActivityRecord(
                who=metadata.caller.uid,
                action=action,
                entity_type=unit.full_name,
                entity_uid=entity_uid,
                context=dataclasses.asdict(context) if context else {},
                run_uid=metadata.run_uid,
            )
        )


# the lifetime, the strategy of 3.1


class BaseAuthLifetime(Entity):
    """Tells whether a session expired, and why; ``None`` if it did not."""

    @t.final
    def check(
        self, session: AuthSessionRecord, now: datetime.datetime
    ) -> AuthSessionStatus | None:
        return self._check(session, now)

    @abc.abstractmethod
    def _check(
        self, session: AuthSessionRecord, now: datetime.datetime
    ) -> AuthSessionStatus | None:
        raise NotImplementedError


class AuthSlidingLifetime(BaseAuthLifetime):
    IDLE_TTL: t.ClassVar = datetime.timedelta(days=1)  # AUTH_SESSION_IDLE_TTL

    @t.override
    def _check(
        self, session: AuthSessionRecord, now: datetime.datetime
    ) -> AuthSessionStatus | None:
        if now - session.seen_at > self.IDLE_TTL:
            return AuthSessionStatus.EXPIRED_IDLE
        return None


# the operations of the operator


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthRevokeAllSessionsParameters:
    profile_uid: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthSweepSessionsParameters:
    # a page of the storage, closed in a transaction of its own
    page_size: int = 1000


class AuthRevokeAllSessionsOperation(
    BaseOperation[AuthRevokeAllSessionsParameters, int]
):
    """Closes every open session of a profile, a stolen account: how many."""

    parent: "AuthSessionsUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_REVOKE)

    @t.override
    async def _run(
        self, parameters: AuthRevokeAllSessionsParameters, metadata: OperationMetadata
    ) -> int:
        auth = self.parent.parent
        async with auth.storage.transaction():
            sessions = await auth.storage.get_open(parameters.profile_uid)
            for session in sessions:
                await auth.storage.close(session.uid, AuthSessionStatus.REVOKED)
                await auth.activities.record(
                    self.parent, session.uid, "revoke", metadata
                )
        for session in sessions:  # after the commit
            await auth.cache.forget(session.token_hash)
        return len(sessions)


class AuthSweepSessionsOperation(BaseOperation[AuthSweepSessionsParameters, int]):
    """
    Closes the open sessions the lifetime tells expired, a page at a time,
    each in a transaction: how many. By its caller, an admin or ``system``.
    """

    parent: "AuthSessionsUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_SWEEP)

    @t.override
    async def _run(
        self, parameters: AuthSweepSessionsParameters, metadata: OperationMetadata
    ) -> int:
        auth = self.parent.parent
        now = self.parent.get_now()
        closed = 0
        after: str | None = None
        while page := await auth.storage.get_all_open(after, parameters.page_size):
            after = page[-1].uid
            expired = []
            async with auth.storage.transaction():
                for session in page:
                    status = self.parent.lifetime.check(session, now)
                    if status is None:
                        continue
                    await auth.storage.close(session.uid, status)
                    await auth.activities.record(
                        self.parent,
                        session.uid,
                        "expire",
                        metadata,
                        context=AuthSessionExpired(reason=status.value),
                    )
                    expired.append(session)
            for session in expired:
                await auth.cache.forget(session.token_hash)
            closed += len(expired)
        return closed


class AuthSessionsAdminsGroup(Entity):
    """``auth.sessions.grp_admins``: the sessions of any profile."""

    parent: "AuthSessionsUnit"

    def get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        flags = permissions.flags
        return permissions(flags.CAN_LIST, flags.CAN_REVOKE, flags.CAN_SWEEP)


class AuthSessionsUnit(OperationsOwner, Unit):
    class Flags(PermissionFlags):
        CAN_LIST_OWN = 1 << 0
        CAN_REVOKE_OWN = 1 << 1
        CAN_LIST = 1 << 2
        CAN_REVOKE = 1 << 3
        CAN_SWEEP = 1 << 4

    parent: "AuthUnit"

    permissions = PermissionsSlot(Flags)
    # none by default, the application picks one, as in ingot-auth
    lifetime = Slot(BaseAuthLifetime)  # type: ignore[type-abstract]
    grp_admins = Slot(AuthSessionsAdminsGroup)

    op_revoke_all = Factory(AuthRevokeAllSessionsOperation)
    op_sweep = Factory(AuthSweepSessionsOperation)

    now = datetime.datetime(2026, 11, 16, tzinfo=datetime.UTC)  # a clock

    def get_now(self) -> datetime.datetime:
        return self.now


class AuthUnit(Unit):
    storage = Slot(AuthStorage)
    cache = Slot(AuthCache)
    sessions = Slot(AuthSessionsUnit)
    activities = Slot(AuthActivitiesUnit)


class AuthProject(Project):
    auth = Slot(AuthUnit)


# the transports: the command line of a job, gRPC of an admin UI


async def run_sweep_command(project: AuthProject) -> int:
    """``auth sessions sweep``: a job of a schedule, as ``system``."""
    operation = project.auth.sessions.op_sweep()
    return await operation._run(
        AuthSweepSessionsParameters(), OperationMetadata(caller=AUTH_SYSTEM)
    )
