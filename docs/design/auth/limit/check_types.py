"""
Runs slice 7 as its actors meet it: over the sessions its operator allows,
a sign-in of a game evicts the one seen longest ago, in the log in the run
of the sign-in, the cache forgetting it; an expired one closed first, not
counted; a web application refusing instead, or keeping any number. mypy
refuses the lines the other file marks.
"""

import asyncio
import dataclasses
import datetime

from app import AppProject
from auth_stub import (
    AuthNoLimit,
    AuthProject,
    AuthRefuseLimit,
    AuthSessionsLimitError,
    AuthSessionsUnit,
    AuthSessionStatus,
    AuthUnit,
)
from ingots_stub import Slot


def see(project: AuthProject, session_uid: str, days: int) -> None:
    """A session seen so many days before the clock of the sessions."""
    sessions = project.auth.storage.sessions
    at = project.auth.sessions.now - datetime.timedelta(days=days)
    sessions[session_uid] = dataclasses.replace(sessions[session_uid], seen_at=at)


def statuses(project: AuthProject) -> list[str]:
    return [s.status.value for s in project.auth.storage.sessions.values()]


async def main() -> None:
    # sessions.3.3: a game, one session a player, a later sign-in wins
    project = AppProject()
    project.configs.AUTH_SESSIONS_MAX = 1  # APP_AUTH_SESSIONS_MAX=1
    auth = project.auth
    await auth.sign_in("alice")  # the laptop
    await auth.sign_in("alice")  # the phone, the laptop signed out
    assert statuses(project) == ["evicted", "open"]
    assert [(r.action, r.entity_uid, r.run_uid) for r in auth.storage.activities] == [
        ("sign_in", "s1", "r1"),
        ("evict", "s1", "r1"),  # in the run of the sign-in that evicted it
        ("sign_in", "s2", "r1"),
    ]
    assert auth.cache.forgotten == ["h-s1"]  # its token refused at once
    await auth.sign_in("bob")  # a limit of each profile
    assert statuses(project) == ["evicted", "open", "open"]

    # three devices: the one seen longest ago, not the one opened first
    project = AppProject()
    project.configs.AUTH_SESSIONS_MAX = 3
    auth = project.auth
    for _ in range(3):
        await auth.sign_in("alice")
    see(project, "s1", 0)
    see(project, "s2", 1)
    await auth.sign_in("alice")
    assert auth.storage.sessions["s2"].status is AuthSessionStatus.EVICTED
    assert statuses(project).count("open") == 3

    # an expired one takes no room, left to its request and the sweep
    see(project, "s1", 2)
    await auth.sign_in("alice")
    assert auth.storage.sessions["s1"].status is AuthSessionStatus.OPEN
    assert auth.storage.sessions["s3"].status is AuthSessionStatus.OPEN
    assert "expire" not in [r.action for r in auth.storage.activities]

    # the operator lowers the limit: the next sign-in evicts down to it,
    # the expired one aside
    project.configs.AUTH_SESSIONS_MAX = 1
    await auth.sign_in("alice")
    assert statuses(project).count("open") == 2  # s1 expired, the new one

    # a web application refuses instead: the user signs out of another
    class RefusingSessions(AuthSessionsUnit):
        limit = Slot(AuthRefuseLimit)

    class RefusingAuth(AuthUnit):
        sessions = Slot(RefusingSessions)

    class RefusingProject(AuthProject):
        auth = Slot(RefusingAuth)

    refusing = RefusingProject()
    refusing.configs.AUTH_SESSIONS_MAX = 2
    await refusing.auth.sign_in("alice")
    await refusing.auth.sign_in("alice")
    try:
        await refusing.auth.sign_in("alice")
    except AuthSessionsLimitError as error:
        print("refused:", error)
    else:
        raise AssertionError("over the limit")
    assert statuses(refusing) == ["open", "open"]  # nothing of it kept
    assert len(refusing.auth.storage.activities) == 2

    # or keeps any number
    class FreeSessions(AuthSessionsUnit):
        limit = Slot(AuthNoLimit)

    class FreeAuth(AuthUnit):
        sessions = Slot(FreeSessions)

    class FreeProject(AuthProject):
        auth = Slot(FreeAuth)

    free = FreeProject()
    free.configs.AUTH_SESSIONS_MAX = 1
    for _ in range(3):
        await free.auth.sign_in("alice")
    see(free, "s1", 2)  # expired: no sign-in reads it, its request closes it
    await free.auth.sign_in("alice")
    assert statuses(free) == ["open", "open", "open", "open"]


asyncio.run(main())
