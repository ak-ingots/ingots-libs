"""
The logic of auth over the facade: sign-up, sign-in, sign-out and the
authentication of a request. In the addon each is an operation; here a
method, to keep the prototype short.
"""

import datetime
import hashlib
import hmac
import os
import secrets
import typing as t
from collections.abc import Callable
from dataclasses import dataclass

from model import AuthProfile, MethodBinding, Session, SessionOrigin
from storage import BaseAuthStorage

PASSWORD = "password"


class SignInFailed(Exception):
    """No such login, a wrong password or a blocked profile: one error, not
    telling which."""


class NotAuthenticated(Exception):
    """No live session for the token."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthConfigs:
    """The configs of auth, ``AUTH_*`` in the addon."""

    session_ttl: datetime.timedelta = datetime.timedelta(days=30)
    is_sign_in_on_sign_up: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class SignedUp[DataType]:
    profile: AuthProfile[DataType]
    token: str | None


class Auth[DataType]:
    def __init__(
        self,
        storage: BaseAuthStorage[DataType],
        configs: AuthConfigs = AuthConfigs(),
        *,
        clock: Callable[[], datetime.datetime] = lambda: datetime.datetime.now(
            datetime.UTC
        ),
    ) -> None:
        self._storage = storage
        self._configs = configs
        self._clock = clock

    async def sign_up(
        self, data: DataType, login: str, password: str, origin: SessionOrigin
    ) -> SignedUp[DataType]:
        now = self._clock()
        profile = AuthProfile(auth_id=os.urandom(16).hex(), data=data, created_at=now)
        method = MethodBinding(
            kind=PASSWORD,
            identifier=login,
            secret=hash_password(password),
            created_at=now,
        )
        await self._storage.create_profile(profile, method)  # IdentifierTaken
        token = None
        if self._configs.is_sign_in_on_sign_up:
            token = await self._open_session(profile, method, origin, now)
        return SignedUp(profile=profile, token=token)

    async def sign_in(self, login: str, password: str, origin: SessionOrigin) -> str:
        found = await self._storage.find_by_method(PASSWORD, login)
        if found is None:
            hash_password(password)  # the same time as a wrong password
            raise SignInFailed()
        profile, method = found
        if (
            method.secret is None
            or not verify_password(password, method.secret)
            or profile.is_blocked
        ):
            raise SignInFailed()
        return await self._open_session(profile, method, origin, self._clock())

    async def sign_out(self, token: str) -> None:
        session, _ = await self._find_session(token)
        await self._storage.end_sessions(
            session.auth_id, self._clock(), only=session.session_id
        )

    async def authenticate(self, token: str) -> AuthProfile[DataType]:
        """The profile of a request: what becomes its Caller."""
        session, profile = await self._find_session(token)
        if profile.is_blocked:
            raise NotAuthenticated()
        await self._storage.touch_session(session.session_id, self._clock())
        return profile

    async def _find_session(
        self, token: str
    ) -> tuple[Session, AuthProfile[DataType]]:
        found = await self._storage.find_live_session(hash_token(token), self._clock())
        if found is None:
            raise NotAuthenticated()
        return found

    async def _open_session(
        self,
        profile: AuthProfile[DataType],
        method: MethodBinding,
        origin: SessionOrigin,
        now: datetime.datetime,
    ) -> str:
        token = secrets.token_urlsafe(32)
        await self._storage.create_session(
            Session(
                session_id=os.urandom(16).hex(),
                auth_id=profile.auth_id,
                method_kind=method.kind,
                token_hash=hash_token(token),
                origin=origin,
                created_at=now,
                last_seen_at=now,
                expires_at=now + self._configs.session_ttl,
            )
        )
        return token


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


_SCRYPT: t.Final = {"n": 2**14, "r": 8, "p": 1}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    params = "$".join(str(_SCRYPT[key]) for key in ("n", "r", "p"))
    return f"scrypt${params}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    algorithm, n, r, p, salt, digest = stored.split("$")
    if algorithm != "scrypt":
        return False
    expected = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p)
    )
    return hmac.compare_digest(expected.hex(), digest)
