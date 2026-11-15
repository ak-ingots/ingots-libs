"""
The activity log of ingot-auth as its design builds it, cut down to what its
consumers touch, in memory: a storage of transactions, the log and its
strategy of a failure, an operation recording its change, the auditors.
"""

import abc
import contextlib
import dataclasses
import datetime
import enum
import logging
import typing as t
from collections.abc import AsyncIterator, Mapping

from ingots_stub import (
    BaseOperation,
    Caller,
    Entity,
    Factory,
    OperationMetadata,
    OperationsOwner,
    PermissionFlags,
    Permissions,
    PermissionsSlot,
    Project,
    Slot,
    Unit,
)

logger = logging.getLogger("ingot_auth.activities")


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthCaller(Caller):
    session_id: str


# the caller of what the server does by itself, a session expiring
AUTH_SYSTEM = Caller(uid="system", permissions=Permissions())


# the storage, its transactions


class AuthStorageError(Exception):
    pass


class AuthStorage(Entity):
    """Tags of the profiles and the log, written in a transaction or alone."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: dict[str, tuple[int, ...]] = {}
        self.activities: list[AuthActivityRecord] = []
        self.broken = False  # the log fails to append

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        tags, activities = dict(self.tags), list(self.activities)
        try:
            yield
        except BaseException:
            self.tags, self.activities = tags, activities  # rolled back
            raise

    def append(self, record: "AuthActivityRecord") -> None:
        if self.broken:
            raise AuthStorageError("the log is gone")
        self.activities.append(record)


# the log


class AuthActivityAction(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BIND = "bind"
    UNBIND = "unbind"
    EXPIRE = "expire"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthActivityContext:
    """
    What a change was, optional: a dataclass an activity of a type of entity
    that needs one, typed where an operation writes it, kept as a map.
    """


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthActivityRecord:
    who: str  # the actor, with its session
    session_id: str | None
    action: AuthActivityAction
    entity_type: str
    entity_id: str
    context: Mapping[str, object]  # the attributes as written, any set
    run_uid: str
    when: datetime.datetime


class BaseAuthActivityFailure(Entity):
    """The strategy of a failure to write the log, in the slot ``failure``."""

    @t.final
    def handle(self, error: AuthStorageError, record: AuthActivityRecord) -> None:
        self._handle(error, record)

    @abc.abstractmethod
    def _handle(self, error: AuthStorageError, record: AuthActivityRecord) -> None:
        raise NotImplementedError


class AuthStrictActivityFailure(BaseAuthActivityFailure):
    """Fails the change with it: no change goes without its record."""

    @t.override
    def _handle(self, error: AuthStorageError, record: AuthActivityRecord) -> None:
        raise error


class AuthSwallowActivityFailure(BaseAuthActivityFailure):
    """Logs it, the record with it, and lets the change through."""

    @t.override
    def _handle(self, error: AuthStorageError, record: AuthActivityRecord) -> None:
        logger.error("the activity is not recorded: %s: %r", error, record)


class AuthActivitiesPermissions(PermissionFlags):
    CAN_READ = 1 << 0


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthListActivitiesParameters:
    entity_type: str | None = None
    entity_id: str | None = None
    who: str | None = None
    action: AuthActivityAction | None = None
    since: datetime.datetime | None = None
    until: datetime.datetime | None = None
    limit: int = 100


class AuthListActivitiesOperation(
    BaseOperation[AuthListActivitiesParameters, tuple[AuthActivityRecord, ...]]
):
    parent: "AuthActivitiesUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_READ)

    @t.override
    async def _run(
        self, parameters: AuthListActivitiesParameters, metadata: OperationMetadata
    ) -> tuple[AuthActivityRecord, ...]:
        found = [
            record
            for record in reversed(self.parent.parent.storage.activities)
            if parameters.entity_type in (None, record.entity_type)
            and parameters.entity_id in (None, record.entity_id)
            and parameters.who in (None, record.who)
            and parameters.action in (None, record.action)
        ]
        return tuple(found[: parameters.limit])


class AuthAuditorsGroup(Entity):
    """``auth.activities.grp_auditors``: the reading of the log."""

    parent: "AuthActivitiesUnit"

    def get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_READ)


class AuthActivitiesUnit(OperationsOwner, Unit):
    """The log: what an operation records, the strategy of a failure, the read."""

    parent: "AuthUnit"

    permissions = PermissionsSlot(AuthActivitiesPermissions)
    # mypy refuses an abstract class where a type is expected: the
    # application declares the one it picks
    failure = Slot(BaseAuthActivityFailure)  # type: ignore[type-abstract]
    grp_auditors = Slot(AuthAuditorsGroup)

    op_list = Factory(AuthListActivitiesOperation)

    @t.final
    async def record(
        self,
        unit: Unit,
        entity_id: str,
        action: AuthActivityAction,
        metadata: OperationMetadata,
        *,
        context: AuthActivityContext | None = None,
    ) -> None:
        """
        Records a change of an entity of a unit, in the transaction open, by
        the caller of the metadata, in its run.
        """
        caller = metadata.caller
        record = AuthActivityRecord(
            who=caller.uid,
            session_id=caller.session_id if isinstance(caller, AuthCaller) else None,
            action=action,
            entity_type=unit.full_name,
            entity_id=entity_id,
            context=dataclasses.asdict(context) if context else {},
            run_uid=metadata.run_uid,
            when=datetime.datetime.now(datetime.UTC),
        )
        try:
            self.parent.storage.append(record)
        except AuthStorageError as error:
            self.failure.handle(error, record)


# the profiles, an operation recording its change


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthProfileTagsSet(AuthActivityContext):
    tag_ids: tuple[int, ...]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthAttrCreated(AuthActivityContext):
    name: str
    type: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthSessionExpired(AuthActivityContext):
    reason: str


class AuthProfilesPermissions(PermissionFlags):
    CAN_UPDATE = 1 << 0


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthSetProfileTagsParameters:
    uid: str
    tag_ids: frozenset[int]


class AuthSetProfileTagsOperation(BaseOperation[AuthSetProfileTagsParameters, None]):
    parent: "AuthProfilesUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_UPDATE)

    @t.override
    async def _run(
        self, parameters: AuthSetProfileTagsParameters, metadata: OperationMetadata
    ) -> None:
        auth = self.parent.parent
        tag_ids = tuple(sorted(parameters.tag_ids))
        async with auth.storage.transaction():
            auth.storage.tags[parameters.uid] = tag_ids
            await auth.activities.record(
                self.parent,
                parameters.uid,
                AuthActivityAction.UPDATE,
                metadata,
                context=AuthProfileTagsSet(tag_ids=tag_ids),
            )


class AuthProfilesUnit(OperationsOwner, Unit):
    parent: "AuthUnit"

    permissions = PermissionsSlot(AuthProfilesPermissions)

    op_set_tags = Factory(AuthSetProfileTagsOperation)


class AuthTagsUnit(Unit):
    """A registry: a tag created needs no context, an attribute a little."""

    parent: "AuthUnit"

    async def create(self, tag_id: int, metadata: OperationMetadata) -> None:
        await self.parent.activities.record(
            self, str(tag_id), AuthActivityAction.CREATE, metadata
        )


class AuthAttrsUnit(Unit):
    parent: "AuthUnit"

    async def create(
        self, attr_id: int, name: str, type: str, metadata: OperationMetadata
    ) -> None:
        await self.parent.activities.record(
            self,
            str(attr_id),
            AuthActivityAction.CREATE,
            metadata,
            context=AuthAttrCreated(name=name, type=type),
        )


class AuthSessionsUnit(Unit):
    """A session expiring is closed by the server, no caller of its own."""

    parent: "AuthUnit"

    async def expire(self, session_id: str) -> None:
        # a run of its own, which the log of the server tells
        metadata = OperationMetadata(caller=AUTH_SYSTEM, run_uid="r-expire")
        logger.info("the session %s expired, run %s", session_id, metadata.run_uid)
        await self.parent.activities.record(
            self,
            session_id,
            AuthActivityAction.EXPIRE,
            metadata,
            context=AuthSessionExpired(reason="expired_idle"),
        )


class AuthUnit(Unit):
    storage = Slot(AuthStorage)
    profiles = Slot(AuthProfilesUnit)
    tags = Slot(AuthTagsUnit)
    attrs = Slot(AuthAttrsUnit)
    sessions = Slot(AuthSessionsUnit)
    activities = Slot(AuthActivitiesUnit)


class AuthProject(Project):
    auth = Slot(AuthUnit)
