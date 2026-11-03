"""
The facade of the storage: what the logic of auth needs, a step of a
scenario per call. A backend keeps the invariants (unique identifiers,
atomic calls) and decides how; the logic passes the time and the rules.
"""

import abc
import dataclasses
import datetime
import typing as t

from model import AuthProfile, MethodBinding, Session


class IdentifierTaken(Exception):
    """Another profile has bound the identifier of the method."""

    @classmethod
    def for_method(cls, method: MethodBinding) -> t.Self:
        return cls(
            f"{method.kind} {method.identifier!r} is taken",
            method.kind,
            method.identifier,
        )

    @t.override
    def __str__(self) -> str:
        return str(self.args[0])


class BaseAuthStorage[DataType](abc.ABC):
    """The storage of profiles and sessions; a component in the addon."""

    # profiles

    @abc.abstractmethod
    async def create_profile(
        self, profile: AuthProfile[DataType], method: MethodBinding
    ) -> None:
        """Creates the profile with its first method, or raises
        IdentifierTaken: one call, no check before it."""

    @abc.abstractmethod
    async def find_by_method(
        self, kind: str, identifier: str
    ) -> tuple[AuthProfile[DataType], MethodBinding] | None:
        """The profile and the binding of a method, in one query."""

    # sessions

    @abc.abstractmethod
    async def create_session(self, session: Session) -> None: ...

    @abc.abstractmethod
    async def find_live_session(
        self, token_hash: str, now: datetime.datetime
    ) -> tuple[Session, AuthProfile[DataType]] | None:
        """The session not ended nor expired at ``now``, with its profile."""

    @abc.abstractmethod
    async def touch_session(self, session_id: str, now: datetime.datetime) -> None:
        """The session is seen at ``now``: a backend may write it seldom."""

    @abc.abstractmethod
    async def end_sessions(
        self, auth_id: str, now: datetime.datetime, *, only: str | None = None
    ) -> int:
        """Ends the live sessions of the profile, ``only`` one of them; gives
        how many it ended."""


class MemoryAuthStorage[DataType](BaseAuthStorage[DataType]):
    """The storage of the tests. An asyncio call with no await inside is
    atomic: the check and the insert of create_profile are one step."""

    def __init__(self) -> None:
        self._profiles: dict[str, AuthProfile[DataType]] = {}
        self._methods: dict[tuple[str, str], tuple[str, MethodBinding]] = {}
        self._sessions: dict[str, Session] = {}

    @t.override
    async def create_profile(
        self, profile: AuthProfile[DataType], method: MethodBinding
    ) -> None:
        key = (method.kind, method.identifier)
        if key in self._methods:
            raise IdentifierTaken.for_method(method)
        self._profiles[profile.auth_id] = profile
        self._methods[key] = (profile.auth_id, method)

    @t.override
    async def find_by_method(
        self, kind: str, identifier: str
    ) -> tuple[AuthProfile[DataType], MethodBinding] | None:
        try:
            auth_id, method = self._methods[kind, identifier]
        except KeyError:
            return None
        return self._profiles[auth_id], method

    @t.override
    async def create_session(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    @t.override
    async def find_live_session(
        self, token_hash: str, now: datetime.datetime
    ) -> tuple[Session, AuthProfile[DataType]] | None:
        for session in self._sessions.values():
            if session.token_hash == token_hash and _is_live(session, now):
                return session, self._profiles[session.auth_id]
        return None

    @t.override
    async def touch_session(self, session_id: str, now: datetime.datetime) -> None:
        session = self._sessions[session_id]
        self._sessions[session_id] = dataclasses.replace(session, last_seen_at=now)

    @t.override
    async def end_sessions(
        self, auth_id: str, now: datetime.datetime, *, only: str | None = None
    ) -> int:
        ended = [
            session
            for session in self._sessions.values()
            if session.auth_id == auth_id
            and _is_live(session, now)
            and only in (None, session.session_id)
        ]
        for session in ended:
            self._sessions[session.session_id] = dataclasses.replace(
                session, ended_at=now
            )
        return len(ended)


def _is_live(session: Session, now: datetime.datetime) -> bool:
    return session.ended_at is None and now < session.expires_at
