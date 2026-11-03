"""
The contract tests of the facade: every backend passes them, the memory
one here, MongoDB in the extra of the addon (ADR 0005).
"""

import asyncio
import datetime
from collections.abc import Callable

from model import AuthProfile, MethodBinding, Session, SessionOrigin
from storage import BaseAuthStorage, IdentifierTaken

NOW = datetime.datetime(2026, 10, 27, tzinfo=datetime.UTC)
HOUR = datetime.timedelta(hours=1)


def profile(auth_id: str) -> AuthProfile[None]:
    return AuthProfile(auth_id=auth_id, data=None, created_at=NOW)


def method(identifier: str) -> MethodBinding:
    return MethodBinding(
        kind="password", identifier=identifier, secret="hash", created_at=NOW
    )


def session(session_id: str, auth_id: str, token_hash: str) -> Session:
    return Session(
        session_id=session_id,
        auth_id=auth_id,
        method_kind="password",
        token_hash=token_hash,
        origin=SessionOrigin(),
        created_at=NOW,
        last_seen_at=NOW,
        expires_at=NOW + HOUR,
    )


async def an_identifier_is_bound_once(storage: BaseAuthStorage[None]) -> None:
    await storage.create_profile(profile("a1"), method("ann"))
    try:
        await storage.create_profile(profile("a2"), method("ann"))
    except IdentifierTaken as error:
        assert str(error) == "password 'ann' is taken", error
    else:
        raise AssertionError("bound twice")
    found = await storage.find_by_method("password", "ann")
    assert found is not None and found[0].auth_id == "a1"
    assert await storage.find_by_method("password", "bob") is None


async def concurrent_sign_ups_bind_once(storage: BaseAuthStorage[None]) -> None:
    results = await asyncio.gather(
        *(storage.create_profile(profile(f"c{n}"), method("cat")) for n in range(5)),
        return_exceptions=True,
    )
    taken = [result for result in results if isinstance(result, IdentifierTaken)]
    assert len(taken) == 4, results


async def a_session_lives_until_ended_or_expired(
    storage: BaseAuthStorage[None],
) -> None:
    await storage.create_profile(profile("s1"), method("sue"))
    for n in (1, 2):
        await storage.create_session(session(f"x{n}", "s1", f"h{n}"))
    found = await storage.find_live_session("h1", NOW)
    assert found is not None and found[1].auth_id == "s1"
    assert await storage.find_live_session("h1", NOW + HOUR) is None, "expired"
    assert await storage.end_sessions("s1", NOW, only="x1") == 1
    assert await storage.find_live_session("h1", NOW) is None, "ended"
    assert await storage.find_live_session("h2", NOW) is not None, "kept"
    assert await storage.end_sessions("s1", NOW) == 1


CONTRACT: tuple[Callable[[BaseAuthStorage[None]], object], ...] = (
    an_identifier_is_bound_once,
    concurrent_sign_ups_bind_once,
    a_session_lives_until_ended_or_expired,
)
