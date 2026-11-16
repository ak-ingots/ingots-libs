"""The lines mypy refuses: what the operator cannot get wrong."""

from auth_stub import (
    AuthRevokeAllSessionsParameters,
    AuthSessionsUnit,
    AuthSweepSessionsParameters,
)
from ingots_stub import ROOT, run


async def operate(sessions: AuthSessionsUnit) -> None:
    AuthRevokeAllSessionsParameters(profile_uid=7)  # error: a uid a string
    AuthRevokeAllSessionsParameters()  # error: whose sessions
    revoke = AuthRevokeAllSessionsParameters(profile_uid="alice")
    await run(sessions.op_sweep, revoke, ROOT)  # error: the parameters of another
    sweep = AuthSweepSessionsParameters()
    count: str = await run(sessions.op_sweep, sweep, ROOT)  # error: a count
    sessions.permissions.flags.CAN_BLOCK  # error: no such flag yet
