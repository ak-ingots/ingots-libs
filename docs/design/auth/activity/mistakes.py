"""The lines mypy refuses: what the log lets no one record."""

import dataclasses

from auth_stub import (
    AuthActivityAction,
    AuthProfilesUnit,
    AuthProfileTagsSet,
    AuthUnit,
)
from ingots_stub import ROOT, OperationMetadata


@dataclasses.dataclass(frozen=True)
class Changed:
    what: str


async def record(auth: AuthUnit, profiles: AuthProfilesUnit) -> None:
    metadata = OperationMetadata(caller=ROOT)
    update = AuthActivityAction.UPDATE
    changed = Changed(what="x")
    await auth.activities.record(profiles, "a1", "set", metadata)  # error: an action
    await auth.activities.record(profiles, 7, update, metadata)  # error: an id a string
    record = auth.activities.record
    await record(profiles, "a1", update, metadata, context=changed)  # error: a context
    AuthProfileTagsSet(tag_ids=("beta",))  # error: the ids of the tags
