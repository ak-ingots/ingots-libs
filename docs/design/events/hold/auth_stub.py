"""
The first publisher, ingot-auth as slice 12 builds it on the events, cut
down to what they touch, in memory: the transaction of its storage holding
the events of its block, dropping them on a rollback; the change of a
password, its steps in the transaction, the other sessions closed and the
change recorded, its event published after it; the mail of the change, the
subscriber the core declares.
"""

import contextlib
import contextvars
import dataclasses
import datetime
import hashlib
import typing as t
from collections.abc import AsyncIterator, Mapping

from ingots_stub import (
    BaseOperation,
    Caller,
    EventsUnit,
    Factories,
    Factory,
    OperationMetadata,
    Permissions,
    Project,
    Slot,
    Unit,
)

type AttrValue = str | int | bool


# -- of ingot-mail -------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Mail:
    to: str
    subject: str
    text: str


class MailUnit(Unit):
    """The mailer of the project: here, the mails it has sent."""

    def __init__(self) -> None:
        self.sent: list[Mail] = []

    async def send(self, mail: Mail) -> None:
        self.sent.append(mail)


# -- the storage: its transaction holds the events -----------------------------


@dataclasses.dataclass(slots=True, kw_only=True)
class AuthProfile:
    uid: str
    nickname: str
    emails: list[str]
    secret: str


@dataclasses.dataclass(slots=True, kw_only=True)
class AuthSession:
    uid: str
    profile_uid: str
    attrs: Mapping[str, AttrValue]
    is_closed: bool = False


@dataclasses.dataclass(slots=True, kw_only=True)
class AuthState:
    profiles: dict[str, AuthProfile] = dataclasses.field(default_factory=dict)
    sessions: dict[str, AuthSession] = dataclasses.field(default_factory=dict)
    activities: list[tuple[str, str]] = dataclasses.field(default_factory=list)


_transaction: contextvars.ContextVar[AuthState | None] = contextvars.ContextVar(
    "ingot_auth_transaction", default=None
)


class AuthStorage(Unit):
    """
    In memory: a transaction writes to a copy of the state, kept on the
    commit. :meth:`transaction` is the facade of the core, the backends
    giving the begin, the commit and the rollback alone; the events are
    wired there, once for every backend.
    """

    project: "AuthProject"

    def __init__(self) -> None:
        self._state = AuthState()

    @property
    def state(self) -> AuthState:
        """That of the transaction of the context, else the committed one."""
        return _transaction.get() or self._state

    @t.final
    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """
        A transaction around a block, holding the events published in it:
        committed, they go when the outermost hold ends; rolled back, or
        failing to commit, they are dropped. Inside another, it is that one.
        """
        if _transaction.get() is not None:
            yield
            return
        async with self.project.events.hold() as held:
            token = _transaction.set(_copy(self._state))
            try:
                yield
            except BaseException:
                held.discard()
                raise
            finally:
                written = _transaction.get()
                _transaction.reset(token)
            assert written is not None
            self._state = written  # the commit


def _copy(state: AuthState) -> AuthState:
    return AuthState(
        profiles={
            uid: dataclasses.replace(profile, emails=list(profile.emails))
            for uid, profile in state.profiles.items()
        },
        sessions={
            uid: dataclasses.replace(session) for uid, session in state.sessions.items()
        },
        activities=list(state.activities),
    )


# -- the event and its subscriber of the core ----------------------------------


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthPasswordChanged:
    """The password of a profile was changed, in a session of these attributes."""

    profile_uid: str
    at: datetime.datetime
    session_attrs: Mapping[str, AttrValue]


class AuthMailPasswordChangedOperation(BaseOperation[AuthPasswordChanged, None]):
    """
    A mail to every email of the profile: the default subscriber. A profile
    of no email gets none.
    """

    project: "AuthProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions()

    @t.override
    async def _run(self, parameters: AuthPasswordChanged, metadata: OperationMetadata) -> None:
        profile = self.project.auth.storage.state.profiles[parameters.profile_uid]
        for email in profile.emails:
            await self.project.mail.send(self._build_mail(parameters, email))

    def _build_mail(self, event: AuthPasswordChanged, to: str) -> Mail:
        where = ", ".join(f"{name} {value}" for name, value in event.session_attrs.items())
        return Mail(
            to=to,
            subject="Your password was changed",
            text=f"Changed at {event.at:%Y-%m-%d %H:%M} UTC ({where}). Not you? Recover it.",
        )


# -- the change of a password: steps, then the event ---------------------------


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthCaller(Caller):
    profile_uid: str | None = None
    session_uid: str | None = None


class AuthPasswordRefusedError(Exception):
    """The old password is wrong."""


class AuthPolicyViolationError(Exception):
    """The new password breaks a policy: here, its length."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthChangePasswordParameters:
    old: str = dataclasses.field(repr=False)
    new: str = dataclasses.field(repr=False)


class AuthChangePasswordOperation(BaseOperation[AuthChangePasswordParameters, None]):
    """
    The steps in a transaction, the guarantee of the change: the hash
    written, the other sessions closed, the change recorded. The event after
    the block, the change done: its subscribers react to a fact.
    """

    parent: "AuthPassword"
    project: "AuthProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions()

    @t.override
    async def _run(
        self, parameters: AuthChangePasswordParameters, metadata: OperationMetadata
    ) -> None:
        caller = metadata.caller
        assert isinstance(caller, AuthCaller) and caller.session_uid is not None
        storage = self.project.auth.storage
        async with storage.transaction():
            profile = storage.state.profiles[t.cast(str, caller.profile_uid)]
            if profile.secret != hash_password(parameters.old):
                raise AuthPasswordRefusedError()
            if len(parameters.new) < 15:
                raise AuthPolicyViolationError("length")
            profile.secret = hash_password(parameters.new)
            for session in storage.state.sessions.values():
                if session.profile_uid == profile.uid and session.uid != caller.session_uid:
                    session.is_closed = True
            storage.state.activities.append(("password.changed", profile.uid))
            attrs = storage.state.sessions[caller.session_uid].attrs
        event = AuthPasswordChanged(
            profile_uid=profile.uid,
            at=datetime.datetime(2026, 11, 24, 10, 30, tzinfo=datetime.UTC),
            session_attrs=attrs,
        )
        self.project.events.publish(self.parent.ev_changed, event, metadata)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class AuthPassword(Unit):
    """The password of a profile: its change, and the event of it."""

    op_change = Factory(AuthChangePasswordOperation)
    ev_changed = Factories[BaseOperation[AuthPasswordChanged, None]](
        AuthMailPasswordChangedOperation
    )


class AuthUnit(Unit):
    storage = Slot(AuthStorage)
    password = Slot(AuthPassword)

    def sign_up(self, nickname: str, password: str, emails: list[str]) -> str:
        """A stand-in for the flows of a sign-up: the uid of the profile."""
        state = self.storage.state
        uid = f"p{len(state.profiles) + 1}"
        state.profiles[uid] = AuthProfile(
            uid=uid, nickname=nickname, emails=emails, secret=hash_password(password)
        )
        return uid

    def sign_in(self, profile_uid: str, attrs: Mapping[str, AttrValue]) -> AuthCaller:
        """A stand-in for the flows of a sign-in: the caller of its session."""
        state = self.storage.state
        uid = f"s{len(state.sessions) + 1}"
        state.sessions[uid] = AuthSession(uid=uid, profile_uid=profile_uid, attrs=attrs)
        return AuthCaller(
            uid=profile_uid, permissions=Permissions(), profile_uid=profile_uid, session_uid=uid
        )


class AuthProject(Project):
    events = Slot(EventsUnit)
    mail = Slot(MailUnit)
    auth = Slot(AuthUnit)
