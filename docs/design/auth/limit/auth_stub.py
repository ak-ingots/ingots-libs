"""
The limit of the sessions of ingot-auth, as slice 7 builds it, cut down to
what its consumers touch, in memory: a sign-in over ``AUTH_SESSIONS_MAX``
open sessions of a profile asks the strategy of the limit, which evicts or
refuses; each change in the activity log, in the transaction of the sign-in.
"""

import abc
import contextlib
import dataclasses
import datetime
import enum
import typing as t
from collections.abc import AsyncIterator, Mapping, Sequence

from ingots_stub import (
    ANONYMOUS,
    Entity,
    OperationMetadata,
    Project,
    Slot,
    Unit,
)


class AuthSessionStatus(enum.StrEnum):
    OPEN = "open"
    EVICTED = "evicted"
    EXPIRED_IDLE = "expired_idle"


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
    entity_uid: str
    context: Mapping[str, object]
    run_uid: str


class AuthSessionsLimitError(Exception):
    """A sign-in refused: the profile has as many open sessions as allowed."""

    @classmethod
    def for_max(cls, uid: str, count: int) -> t.Self:
        return cls(f"profile {uid!r} has {count} open sessions, the limit", uid)


# the configs: the operator of the application sets them, the env of ingots


class AuthConfigs:
    AUTH_SESSIONS_MAX = 10  # IntConfig(10): open sessions of a profile


# the storage


class AuthStorage(Entity):
    """The sessions by their uid, in order, and the log, in transactions."""

    def __init__(self) -> None:
        super().__init__()
        self.sessions: dict[str, AuthSessionRecord] = {}
        self.activities: list[AuthActivityRecord] = []

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        sessions, activities = dict(self.sessions), list(self.activities)
        try:
            yield
        except BaseException:
            self.sessions, self.activities = sessions, activities
            raise

    async def open(self, session: AuthSessionRecord) -> None:
        self.sessions[session.uid] = session

    async def get_open(self, profile_uid: str) -> tuple[AuthSessionRecord, ...]:
        return tuple(
            session
            for session in self.sessions.values()
            if session.profile_uid == profile_uid
            and session.status is AuthSessionStatus.OPEN
        )

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


class AuthActivitiesUnit(Unit):
    parent: "AuthUnit"

    @t.final
    async def record(
        self,
        entity_uid: str,
        action: str,
        metadata: OperationMetadata,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        self.parent.storage.activities.append(
            AuthActivityRecord(
                who=metadata.caller.uid,
                action=action,
                entity_uid=entity_uid,
                context=context or {},
                run_uid=metadata.run_uid,
            )
        )


# the lifetime, the strategy of 3.1, as built


class AuthSlidingLifetime(Entity):
    IDLE_TTL: t.ClassVar = datetime.timedelta(days=1)  # AUTH_SESSION_IDLE_TTL

    def check(
        self, session: AuthSessionRecord, now: datetime.datetime
    ) -> AuthSessionStatus | None:
        if now - session.seen_at > self.IDLE_TTL:
            return AuthSessionStatus.EXPIRED_IDLE
        return None


# the limit, the strategy of 3.3


class BaseAuthSessionsLimit(Entity):
    """
    Makes room for a session a sign-in opens, in its transaction: the open
    sessions of the profile the lifetime tells expired closed with their
    reason, then, as many as ``AUTH_SESSIONS_MAX`` left, those the strategy
    picks evicted, or the sign-in refused; gives the sessions it closed, so
    that the cache forgets them after the commit.
    """

    parent: "AuthSessionsUnit"

    @t.final
    async def make_room(
        self, uid: str, metadata: OperationMetadata
    ) -> tuple[AuthSessionRecord, ...]:
        auth = self.parent.parent
        now = self.parent.get_now()
        closed = []
        alive = []
        for session in await auth.storage.get_open(uid):
            status = self.parent.lifetime.check(session, now)
            if status is None:
                alive.append(session)
                continue
            await auth.storage.close(session.uid, status)
            await auth.activities.record(
                session.uid, "expire", metadata, context={"reason": status.value}
            )
            closed.append(session)
        # at least one, the session the sign-in opens
        limit = max(self.project.configs.AUTH_SESSIONS_MAX, 1)
        excess = len(alive) - limit + 1
        if excess > 0:
            alive.sort(key=lambda session: session.seen_at)
            for session in self._select_evicted(uid, tuple(alive), excess):
                await auth.storage.close(session.uid, AuthSessionStatus.EVICTED)
                await auth.activities.record(session.uid, "evict", metadata)
                closed.append(session)
        return tuple(closed)

    @abc.abstractmethod
    def _select_evicted(
        self, uid: str, alive: tuple[AuthSessionRecord, ...], excess: int
    ) -> Sequence[AuthSessionRecord]:
        """
        The sessions to evict, of those alive, seen longest ago first, at
        least ``excess`` of them; or raises to refuse the sign-in.
        """
        raise NotImplementedError


class AuthEvictOldestLimit(BaseAuthSessionsLimit):
    """The sessions seen longest ago signed out: a later sign-in wins."""

    @t.override
    def _select_evicted(
        self, uid: str, alive: tuple[AuthSessionRecord, ...], excess: int
    ) -> Sequence[AuthSessionRecord]:
        return alive[:excess]


class AuthRefuseLimit(BaseAuthSessionsLimit):
    """The sign-in refused: the user signs out of another first."""

    @t.override
    def _select_evicted(
        self, uid: str, alive: tuple[AuthSessionRecord, ...], excess: int
    ) -> Sequence[AuthSessionRecord]:
        raise AuthSessionsLimitError.for_max(uid, len(alive))


class AuthNoLimit(BaseAuthSessionsLimit):
    """As many sessions as the users open; ``AUTH_SESSIONS_MAX`` unread."""

    @t.override
    def _select_evicted(
        self, uid: str, alive: tuple[AuthSessionRecord, ...], excess: int
    ) -> Sequence[AuthSessionRecord]:
        return ()


class AuthSessionsUnit(Unit):
    parent: "AuthUnit"

    lifetime = Slot(AuthSlidingLifetime)
    # none by default, the application picks one, as the lifetime
    limit = Slot(BaseAuthSessionsLimit)  # type: ignore[type-abstract]

    now = datetime.datetime(2026, 11, 18, tzinfo=datetime.UTC)  # a clock
    count = 0

    def get_now(self) -> datetime.datetime:
        return self.now

    async def open(self, uid: str) -> str:
        """A session of the profile, by the uid: its token, a hash of it kept."""
        self.count += 1
        session = AuthSessionRecord(
            uid=f"s{self.count}",
            profile_uid=uid,
            token_hash=f"h-s{self.count}",
            opened_at=self.now,
            seen_at=self.now,
        )
        await self.parent.storage.open(session)
        return f"t-{session.uid}"


class AuthUnit(Unit):
    storage = Slot(AuthStorage)
    cache = Slot(AuthCache)
    sessions = Slot(AuthSessionsUnit)
    activities = Slot(AuthActivitiesUnit)

    async def sign_in(self, uid: str) -> str:
        """
        The end of a sign-in of a method, its subject verified as a profile:
        room made, the session opened, in one transaction; the evicted ones
        forgotten by the cache after it.
        """
        metadata = OperationMetadata(caller=ANONYMOUS)
        async with self.storage.transaction():
            closed = await self.sessions.limit.make_room(uid, metadata)
            token = await self.sessions.open(uid)
            await self.activities.record(token[2:], "sign_in", metadata)
        for session in closed:
            await self.cache.forget(session.token_hash)
        return token


class AuthProject(Project):
    configs = AuthConfigs()
    auth = Slot(AuthUnit)
