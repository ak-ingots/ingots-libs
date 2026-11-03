"""The model of auth: profiles, the methods bound to them, sessions."""

import datetime
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthProfile[DataType]:
    """An account: the id the system knows the caller by, and the data of
    the application, its schema of the profile."""

    auth_id: str
    data: DataType
    is_blocked: bool = False
    created_at: datetime.datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class MethodBinding:
    """A way to sign in bound to a profile: a password under a login, an
    external account, a phone. ``(kind, identifier)`` is unique."""

    kind: str
    identifier: str
    secret: str | None
    created_at: datetime.datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionOrigin:
    """Where a session comes from, as its transport sees it."""

    address: str | None = None
    client: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Session:
    """A signed-in client: who, through which method, from where, when. The
    token is kept as its hash only."""

    session_id: str
    auth_id: str
    method_kind: str
    token_hash: str
    origin: SessionOrigin
    created_at: datetime.datetime
    last_seen_at: datetime.datetime
    expires_at: datetime.datetime
    ended_at: datetime.datetime | None = None
