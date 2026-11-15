"""
Runs slice 6 as its actors meet it: the operator revokes every session of a
profile, each in the log by them, the cache forgetting them; an admin sweeps
the expired ones from an admin UI, in the log by them, a job of a schedule
as `system`, a page at a time; a user may neither. mypy refuses the lines the other file marks.
"""

import asyncio
import datetime

from app import AppProject
from auth_stub import (
    AuthCaller,
    AuthRevokeAllSessionsParameters,
    AuthSessionRecord,
    AuthSessionStatus,
    AuthStorage,
    AuthSweepSessionsParameters,
    run_sweep_command,
)
from ingots_stub import OperationPermissionsError, Permissions, run

NOW = datetime.datetime(2026, 11, 16, tzinfo=datetime.UTC)


def open_sessions(storage: AuthStorage, *seen: tuple[str, str, int]) -> None:
    """Sessions by uid, of a profile, seen so many days ago."""
    for uid, profile_uid, days in seen:
        at = NOW - datetime.timedelta(days=days)
        storage.sessions[uid] = AuthSessionRecord(
            uid=uid,
            profile_uid=profile_uid,
            token_hash=f"h-{uid}",
            opened_at=at,
            seen_at=at,
        )


async def main() -> None:
    project = AppProject()
    auth = project.auth
    admin = AuthCaller(
        uid="op",
        session_uid="s9",
        permissions=auth.sessions.grp_admins.get_permissions(),
    )
    user = AuthCaller(uid="alice", session_uid="s1", permissions=Permissions())

    # sign-out.1.3: every session of alice, a stolen account
    open_sessions(
        auth.storage, ("s1", "alice", 0), ("s2", "alice", 0), ("s3", "bob", 0)
    )
    revoke = AuthRevokeAllSessionsParameters(profile_uid="alice")
    assert await run(auth.sessions.op_revoke_all, revoke, admin) == 2
    assert [s.status for s in auth.storage.sessions.values()] == [
        AuthSessionStatus.REVOKED,
        AuthSessionStatus.REVOKED,
        AuthSessionStatus.OPEN,
    ]
    assert [(r.who, r.action, r.entity_uid) for r in auth.storage.activities] == [
        ("op", "revoke", "s1"),
        ("op", "revoke", "s2"),
    ]
    assert auth.cache.forgotten == ["h-s1", "h-s2"]
    assert await run(auth.sessions.op_revoke_all, revoke, admin) == 0  # none left
    unknown = AuthRevokeAllSessionsParameters(profile_uid="nobody")
    assert await run(auth.sessions.op_revoke_all, unknown, admin) == 0

    # sessions.3.4: an admin sweeps from an admin UI, a page at a time
    open_sessions(
        auth.storage, ("s4", "carol", 2), ("s5", "dave", 3), ("s6", "erin", 0)
    )
    auth.storage.activities.clear()
    auth.storage.transactions = 0
    sweep = AuthSweepSessionsParameters(page_size=2)
    assert await run(auth.sessions.op_sweep, sweep, admin) == 2  # s4, s5
    assert auth.storage.sessions["s4"].status is AuthSessionStatus.EXPIRED_IDLE
    assert auth.storage.sessions["s6"].status is AuthSessionStatus.OPEN
    assert [(r.who, r.entity_uid, r.context) for r in auth.storage.activities] == [
        ("op", "s4", {"reason": "expired_idle"}),
        ("op", "s5", {"reason": "expired_idle"}),
    ]
    assert auth.storage.transactions == 2  # s3 s4 | s5 s6

    # a job of a schedule, on the command line, as system
    open_sessions(auth.storage, ("s7", "frank", 5))
    assert await run_sweep_command(project) == 1
    assert auth.storage.activities[-1].who == "system"

    # a user may neither
    for factory, parameters in (
        (auth.sessions.op_revoke_all, revoke),
        (auth.sessions.op_sweep, sweep),
    ):
        try:
            await run(factory, parameters, user)  # type: ignore[arg-type]
        except OperationPermissionsError as error:
            print("refused:", error)
        else:
            raise AssertionError("a user ended sessions")


asyncio.run(main())
