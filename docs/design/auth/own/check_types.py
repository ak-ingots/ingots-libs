"""
Runs slice 4 as its actors meet it. The end user, through its client: signs
in on a phone and a laptop, sees its sessions, the place of each derived
from its IP, the current one marked, revokes the lost phone, not another's,
then the others; reads its profile when the hash of a reply changes; signs
out, then again with the token closed, nothing to tell. The operator: sets
the tags of a profile as the root by the CLI, reads the record of the
sign-ins over gRPC by its group, which the end user may not. mypy refuses
the lines the other file marks.
"""

import asyncio

from app import AppProject
from auth_stub import (
    PROFILE_HASH_KEY,
    AuthListSessionsParameters,
    AuthRevokeOwnSessionParameters,
    AuthSessionCloseReason,
    AuthSessionNotFoundError,
    AuthSetProfileTagsParameters,
    ServicerContext,
)
from ingots_stub import ANONYMOUS, ROOT, OperationPermissionsError, run


async def main() -> None:
    project = AppProject()
    sessions, profiles = project.auth.sessions, project.auth.profiles

    # the own sessions
    phone = await sessions.open("ann", {"ip": "192.0.2.1", "device": "phone"})
    laptop = await sessions.open("ann", {"ip": "198.51.100.7", "device": "laptop"})
    ann = await sessions.authenticate(laptop)
    own = await run(sessions.op_list_own, None, ann)
    places = [
        (s.attr_values["device"], s.attr_values["country"], s.is_current) for s in own
    ]
    assert places == [("phone", "PL", False), ("laptop", "DE", True)], places
    lost = AuthRevokeOwnSessionParameters(session_id=own[0].id)
    await run(sessions.op_revoke_own, lost, ann)
    assert await sessions.authenticate(phone) is ANONYMOUS
    await sessions.open("bob", {"ip": "192.0.2.1", "device": "phone"})
    bobs = sessions.get_open("bob")[0].id
    try:
        await run(
            sessions.op_revoke_own, AuthRevokeOwnSessionParameters(session_id=bobs), ann
        )
    except AuthSessionNotFoundError as error:
        print("not found:", error)
    else:
        raise AssertionError("another's session revoked")
    await sessions.open("ann", {"device": "tablet"})  # no IP, no place
    assert await run(sessions.op_revoke_others, None, ann) == 1

    # the profile of the caller, its hash in every reply
    context = ServicerContext({"authorization": f"Bearer {laptop}"})
    print(await project.servicer.Buy("tea", context))
    told = dict(context.trailing_metadata)[PROFILE_HASH_KEY]
    profile = await run(profiles.op_get_own, None, ann)
    assert profile.hash == told and profile.permissions["shop"] == 1
    tags = AuthSetProfileTagsParameters(uid="ann", tag_ids=frozenset({1}))
    await run(profiles.op_set_tags, tags, ROOT)  # the operator, by the CLI
    context = ServicerContext({"authorization": f"Bearer {laptop}"})
    await project.servicer.Buy("tea", context)
    assert dict(context.trailing_metadata)[PROFILE_HASH_KEY] != told, "a new hash"
    ann = await sessions.authenticate(laptop)
    profile = await run(profiles.op_get_own, None, ann)
    assert profile.tag_ids == {1}
    assert profile.hash == dict(context.trailing_metadata)[PROFILE_HASH_KEY]

    # the sign-out
    await run(project.auth.sign_out.op_sign_out, None, ann)
    assert await sessions.authenticate(laptop) is ANONYMOUS
    await run(project.auth.sign_out.op_sign_out, None, ANONYMOUS)  # nothing to tell

    # the record of the sign-ins
    project.auth.memberships["eve"] = {"auth.sessions.grp_admins"}
    eve = await sessions.authenticate(await sessions.open("eve", {}))
    query = AuthListSessionsParameters(uid="ann", closed=True)
    record = [
        (r.attr_values["device"], r.close_reason, r.closed_by)
        for r in await run(sessions.op_list, query, eve)
    ]
    assert record == [
        ("phone", AuthSessionCloseReason.REVOKED, "ann"),
        ("laptop", AuthSessionCloseReason.SIGNED_OUT, "ann"),
        ("tablet", AuthSessionCloseReason.REVOKED, "ann"),
    ], record
    try:
        await run(
            sessions.op_list,
            query,
            await sessions.authenticate(await sessions.open("ann", {})),
        )
    except OperationPermissionsError as error:
        print("refused:", error)
    else:
        raise AssertionError("the end user read the record")


asyncio.run(main())
