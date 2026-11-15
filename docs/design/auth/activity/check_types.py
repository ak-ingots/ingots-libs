"""
Runs the log as its actors meet it: a change recorded with its context in
its transaction, its type the full name of its unit, its caller and session;
a failure of the log failing the change, strict, or logged and let through,
swallowed; the auditors reading it, newest first, the user refused. mypy
refuses the lines the other file marks.
"""

import asyncio
import logging

from app import StrictProject, SwallowProject
from auth_stub import (
    AuthCaller,
    AuthListActivitiesParameters,
    AuthSetProfileTagsParameters,
    AuthStorageError,
)
from ingots_stub import (
    ROOT,
    OperationMetadata,
    OperationPermissionsError,
    Permissions,
    run,
)


async def main() -> None:
    project = StrictProject()
    auth = project.auth
    operator = AuthCaller(
        uid="op",
        session_id="s9",
        permissions=auth.profiles.permissions(
            auth.profiles.permissions.flags.CAN_UPDATE
        ),
    )
    tags = AuthSetProfileTagsParameters(uid="a1", tag_ids=frozenset({3, 1}))
    await run(auth.profiles.op_set_tags, tags, operator)
    (record,) = auth.storage.activities
    assert (record.who, record.action, record.entity_type, record.entity_id) == (
        "op",
        "update",
        "auth.profiles",
        "a1",
    )
    assert record.context == {"tag_ids": (1, 3)} and record.session_id == "s9"

    # strict: the change goes with its record, or not at all
    auth.storage.broken = True
    again = AuthSetProfileTagsParameters(uid="a1", tag_ids=frozenset({2}))
    try:
        await run(auth.profiles.op_set_tags, again, operator)
    except AuthStorageError as error:
        print("rolled back:", error)
    else:
        raise AssertionError("a change went without its record")
    assert auth.storage.tags["a1"] == (1, 3)

    # swallow: the change goes, the failure is logged
    swallowed = SwallowProject()
    swallowed.auth.storage.broken = True
    logging.basicConfig(level=logging.ERROR, format="%(name)s: %(message)s")
    await run(swallowed.auth.profiles.op_set_tags, again, ROOT)
    assert swallowed.auth.storage.tags["a1"] == (2,)
    assert swallowed.auth.storage.activities == []

    # the auditors read it, the user may not
    auth.storage.broken = False

    # a context as each activity needs: none, a little, by the server itself
    await auth.tags.create(1, OperationMetadata(caller=ROOT))
    await auth.attrs.create(2, "first_name", "str", OperationMetadata(caller=ROOT))
    await auth.sessions.expire("s1")
    created_tag, created_attr, expired = auth.storage.activities[-3:]
    assert (created_tag.entity_type, created_tag.context) == ("auth.tags", {})
    assert created_attr.context == {"name": "first_name", "type": "str"}
    assert (expired.who, expired.run_uid, expired.action) == (
        "system",
        "r-expire",
        "expire",
    )

    await run(auth.profiles.op_set_tags, again, ROOT)
    auditor = AuthCaller(
        uid="au",
        session_id="s8",
        permissions=auth.activities.grp_auditors.get_permissions(),
    )
    query = AuthListActivitiesParameters(entity_type="auth.profiles", entity_id="a1")
    history = await run(auth.activities.op_list, query, auditor)
    assert [(r.who, r.context) for r in history] == [
        ("root", {"tag_ids": (2,)}),
        ("op", {"tag_ids": (1, 3)}),
    ], history
    user = AuthCaller(uid="a1", session_id="s1", permissions=Permissions())
    try:
        await run(auth.activities.op_list, query, user)
    except OperationPermissionsError as error:
        print("refused:", error)
    else:
        raise AssertionError("the user read the log")


asyncio.run(main())
