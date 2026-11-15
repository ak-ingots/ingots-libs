"""
The core of ingot-auth as slice 4 builds it, cut down to what its consumers
touch, in memory: the caller with the hash of its profile; the sessions, the
strategy deriving their attributes, the place, and their record, kept closed
with who closed them; the sign-out, open to any caller; the own sessions of
a caller; the values of a profile and the profile of its caller; the
servicer of a signed-in caller telling the hash in the trailing metadata of
its replies. The groups grant as in ingot-auth 0.2.0, found here by a list.
"""

import abc
import dataclasses
import datetime
import enum
import hashlib
import json
import secrets
import typing as t
from collections.abc import Mapping

from ingots_stub import (
    ANONYMOUS,
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
    run,
)

type AttrValue = str | int | bool

PROFILE_HASH_KEY = "ingot-auth-user-profile-hash"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthCaller(Caller):
    """
    A caller signed in: the id of its session, which only the operations of
    the sessions read, and the hash of its profile, computed once, when the
    caller is formed, and told in the replies to its client.
    """

    session_id: str
    profile_hash: str


# the groups, as in ingot-auth 0.2.0


class AuthGroup(Entity):
    """A group, named by its full name, granting by its hook."""

    @t.final
    def get_permissions(self) -> Permissions:
        return self._get_permissions()

    def _get_permissions(self) -> Permissions:
        return Permissions()


class AuthSignedInGroup(AuthGroup):
    """``auth.grp_signed_in``: what every signed-in caller may of its own."""

    parent: "AuthUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        sessions = self.parent.sessions.permissions
        profiles = self.parent.profiles.permissions
        return (
            super()._get_permissions()
            | sessions(sessions.flags.CAN_LIST_OWN, sessions.flags.CAN_REVOKE_OWN)
            | profiles(profiles.flags.CAN_READ_OWN)
        )


class AuthSessionsAdminsGroup(AuthGroup):
    """``auth.sessions.grp_admins``: the record of the sign-ins too."""

    parent: "AuthSessionsUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        sessions = self.parent.permissions
        return super()._get_permissions() | sessions(sessions.flags.CAN_LIST)


class AuthProfilesManagersGroup(AuthGroup):
    """``auth.profiles.grp_managers``: the values of the profiles too."""

    parent: "AuthProfilesUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        profiles = self.parent.permissions
        return super()._get_permissions() | profiles(profiles.flags.CAN_UPDATE)


# the sessions


class AuthSessionCloseReason(enum.StrEnum):
    SIGNED_OUT = "signed_out"
    REVOKED = "revoked"
    EXPIRED_IDLE = "expired_idle"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthSessionRecord:
    """
    A session, open or closed, the record of a sign-in; a closed one tells
    when, why and by whom, ``closed_by`` the uid of the caller that closed
    it, none when it expired. The attributes by their names here, by their
    ids in the storage.
    """

    id: str
    uid: str
    token_hash: str
    attr_values: Mapping[str, AttrValue]
    opened_at: datetime.datetime
    seen_at: datetime.datetime
    closed_at: datetime.datetime | None = None
    close_reason: AuthSessionCloseReason | None = None
    closed_by: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthOwnSession:
    """A session as its user sees it: no token, the current one marked."""

    id: str
    attr_values: Mapping[str, AttrValue]
    opened_at: datetime.datetime
    seen_at: datetime.datetime
    is_current: bool


class AuthSessionNotFoundError(LookupError):
    pass


class BaseAuthSessionAttrsDeriver(Entity):
    """
    The strategy deriving the attributes of a session of the source
    ``derived`` from those the transport and the client gave at its sign-in,
    the place from the IP, in the slot ``deriver`` of the sessions; the
    registry keeps those it has of the source, by their names.
    """

    @t.final
    async def derive(self, values: Mapping[str, AttrValue]) -> Mapping[str, AttrValue]:
        return await self._derive(values)

    @abc.abstractmethod
    async def _derive(self, values: Mapping[str, AttrValue]) -> Mapping[str, AttrValue]:
        raise NotImplementedError


class AuthNoSessionAttrsDeriver(BaseAuthSessionAttrsDeriver):
    """Derives none: an application that tells no place picks it."""

    @t.override
    async def _derive(self, values: Mapping[str, AttrValue]) -> Mapping[str, AttrValue]:
        return {}


class AuthSessionsPermissions(PermissionFlags):
    CAN_LIST_OWN = 1 << 0
    CAN_REVOKE_OWN = 1 << 1
    CAN_LIST = 1 << 2


class AuthListOwnSessionsOperation(BaseOperation[None, tuple[AuthOwnSession, ...]]):
    """The open sessions of the caller, the current one marked; none of root."""

    parent: "AuthSessionsUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_LIST_OWN)

    @t.override
    async def _run(
        self, parameters: None, metadata: OperationMetadata
    ) -> tuple[AuthOwnSession, ...]:
        caller = metadata.caller
        if not isinstance(caller, AuthCaller):
            return ()
        return tuple(
            AuthOwnSession(
                id=record.id,
                attr_values=record.attr_values,
                opened_at=record.opened_at,
                seen_at=record.seen_at,
                is_current=record.id == caller.session_id,
            )
            for record in self.parent.get_open(caller.uid)
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthRevokeOwnSessionParameters:
    session_id: str


class AuthRevokeOwnSessionOperation(
    BaseOperation[AuthRevokeOwnSessionParameters, None]
):
    """Closes an open session of the caller's own; another's is not found."""

    parent: "AuthSessionsUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_REVOKE_OWN)

    @t.override
    async def _run(
        self, parameters: AuthRevokeOwnSessionParameters, metadata: OperationMetadata
    ) -> None:
        caller = metadata.caller
        own = self.parent.get_open(caller.uid) if isinstance(caller, AuthCaller) else ()
        if parameters.session_id not in {record.id for record in own}:
            raise AuthSessionNotFoundError(parameters.session_id)
        self.parent.close(
            parameters.session_id, AuthSessionCloseReason.REVOKED, caller.uid
        )


class AuthRevokeOtherSessionsOperation(BaseOperation[None, int]):
    """Closes the open sessions of the caller but the current one: how many."""

    parent: "AuthSessionsUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_REVOKE_OWN)

    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> int:
        caller = metadata.caller
        if not isinstance(caller, AuthCaller):
            return 0
        others = [
            r for r in self.parent.get_open(caller.uid) if r.id != caller.session_id
        ]
        for record in others:
            self.parent.close(record.id, AuthSessionCloseReason.REVOKED, caller.uid)
        return len(others)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthListSessionsParameters:
    uid: str
    closed: bool = False


class AuthListSessionsOperation(
    BaseOperation[AuthListSessionsParameters, tuple[AuthSessionRecord, ...]]
):
    """The sessions of a profile, the closed ones too if asked: the record."""

    parent: "AuthSessionsUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_LIST)

    @t.override
    async def _run(
        self, parameters: AuthListSessionsParameters, metadata: OperationMetadata
    ) -> tuple[AuthSessionRecord, ...]:
        if parameters.closed:
            return self.parent.get_all(parameters.uid)
        return self.parent.get_open(parameters.uid)


class AuthSessionsUnit(OperationsOwner, Unit):
    """
    The sessions: opened by the sign-in, their attributes derived by the
    strategy in the slot ``deriver``; a token turned into its caller; closed
    by the sign-out or a revoke, kept, the record of the sign-in.
    """

    parent: "AuthUnit"

    permissions = PermissionsSlot(AuthSessionsPermissions)
    # mypy refuses an abstract class where a type is expected: an application
    # declares the one it picks
    deriver = Slot(BaseAuthSessionAttrsDeriver)  # type: ignore[type-abstract]
    grp_admins = Slot(AuthSessionsAdminsGroup)

    op_list_own = Factory(AuthListOwnSessionsOperation)
    op_revoke_own = Factory(AuthRevokeOwnSessionOperation)
    op_revoke_others = Factory(AuthRevokeOtherSessionsOperation)
    op_list = Factory(AuthListSessionsOperation)

    def __init__(self) -> None:
        super().__init__()
        self._records: dict[str, AuthSessionRecord] = {}
        self._callers: dict[str, AuthCaller] = {}  # the cache, by the token hash

    async def open(self, uid: str, values: Mapping[str, AttrValue]) -> str:
        """The end of a sign-in, cut down: the token of a new session."""
        token = secrets.token_urlsafe()
        now = datetime.datetime.now(datetime.UTC)
        derived = await self.deriver.derive(values)
        record = AuthSessionRecord(
            id=secrets.token_hex(4),
            uid=uid,
            token_hash=_hash(token),
            attr_values={**values, **derived},
            opened_at=now,
            seen_at=now,
        )
        self._records[record.id] = record
        return token

    async def authenticate(self, token: str) -> Caller:
        """The caller of a token, the anonymous one of a session closed."""
        token_hash = _hash(token)
        try:
            return self._callers[token_hash]
        except KeyError:
            pass
        for record in self.get_open(None):
            if record.token_hash == token_hash:
                caller = self.parent.form_caller(record)
                self._callers[token_hash] = caller
                return caller
        return ANONYMOUS

    def get_open(self, uid: str | None) -> tuple[AuthSessionRecord, ...]:
        return tuple(r for r in self.get_all(uid) if r.closed_at is None)

    def get_all(self, uid: str | None) -> tuple[AuthSessionRecord, ...]:
        return tuple(r for r in self._records.values() if uid is None or r.uid == uid)

    def close(
        self, session_id: str, reason: AuthSessionCloseReason, closed_by: str | None
    ) -> None:
        """Closes a session, kept; forgets its caller after, as the storage commits."""
        record = self._records[session_id]
        self._records[session_id] = dataclasses.replace(
            record,
            closed_at=datetime.datetime.now(datetime.UTC),
            close_reason=reason,
            closed_by=closed_by,
        )
        self._callers.pop(record.token_hash, None)

    def forget_callers(self, uid: str) -> None:
        for token_hash, caller in tuple(self._callers.items()):
            if caller.uid == uid:
                del self._callers[token_hash]


# the sign-out


class AuthSignOutOperation(BaseOperation[None, None]):
    """
    Closes the session of the caller: any caller may, the anonymous one, of
    a token closed, expired or unknown, signing out of nothing.
    """

    @t.override
    def _get_permissions(self) -> Permissions:
        return Permissions()

    @t.override
    async def _run(self, parameters: None, metadata: OperationMetadata) -> None:
        caller = metadata.caller
        if isinstance(caller, AuthCaller):
            sessions = self.find_parent(AuthUnit).sessions
            sessions.close(
                caller.session_id, AuthSessionCloseReason.SIGNED_OUT, caller.uid
            )


class AuthSignOutUnit(OperationsOwner, Unit):
    """The sign-out, as the sign-in is a unit of its own: no permissions."""

    op_sign_out = Factory(AuthSignOutOperation)


# the profiles


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthProfileValues:
    """The tags and the values of the attributes of a profile, by their ids."""

    tag_ids: frozenset[int] = frozenset()
    attr_values: Mapping[int, AttrValue] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthOwnProfile:
    """The profile of the caller as its client sees it, and its hash."""

    tag_ids: frozenset[int]
    attr_values: Mapping[int, AttrValue]
    permissions: Mapping[str, int]
    hash: str


class AuthProfilesPermissions(PermissionFlags):
    CAN_READ_OWN = 1 << 0
    CAN_UPDATE = 1 << 1


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthSetProfileTagsParameters:
    uid: str
    tag_ids: frozenset[int]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AuthSetProfileAttrValuesParameters:
    uid: str
    attr_values: Mapping[int, AttrValue]


class AuthSetProfileTagsOperation(BaseOperation[AuthSetProfileTagsParameters, None]):
    """Sets the tags of a profile, all of them; its callers are forgotten."""

    parent: "AuthProfilesUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_UPDATE)

    @t.override
    async def _run(
        self, parameters: AuthSetProfileTagsParameters, metadata: OperationMetadata
    ) -> None:
        values = self.parent.get_values(parameters.uid)
        self.parent.set_values(
            parameters.uid, dataclasses.replace(values, tag_ids=parameters.tag_ids)
        )


class AuthSetProfileAttrValuesOperation(
    BaseOperation[AuthSetProfileAttrValuesParameters, None]
):
    """Sets the values of the attributes of a profile, all of them."""

    parent: "AuthProfilesUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_UPDATE)

    @t.override
    async def _run(
        self,
        parameters: AuthSetProfileAttrValuesParameters,
        metadata: OperationMetadata,
    ) -> None:
        values = self.parent.get_values(parameters.uid)
        self.parent.set_values(
            parameters.uid,
            dataclasses.replace(values, attr_values=parameters.attr_values),
        )


class AuthGetOwnProfileOperation(BaseOperation[None, AuthOwnProfile]):
    """The profile of the caller, its permissions and its hash."""

    parent: "AuthProfilesUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_READ_OWN)

    @t.override
    async def _run(
        self, parameters: None, metadata: OperationMetadata
    ) -> AuthOwnProfile:
        caller = metadata.caller
        if not isinstance(caller, AuthCaller):
            raise LookupError("no profile of a caller not signed in")
        values = self.parent.get_values(caller.uid)
        return AuthOwnProfile(
            tag_ids=values.tag_ids,
            attr_values=values.attr_values,
            permissions=dict(caller.permissions),
            hash=caller.profile_hash,
        )


class AuthProfilesUnit(OperationsOwner, Unit):
    parent: "AuthUnit"

    permissions = PermissionsSlot(AuthProfilesPermissions)
    grp_managers = Slot(AuthProfilesManagersGroup)

    op_set_tags = Factory(AuthSetProfileTagsOperation)
    op_set_attr_values = Factory(AuthSetProfileAttrValuesOperation)
    op_get_own = Factory(AuthGetOwnProfileOperation)

    def __init__(self) -> None:
        super().__init__()
        self._values: dict[str, AuthProfileValues] = {}

    def get_values(self, uid: str) -> AuthProfileValues:
        return self._values.get(uid, AuthProfileValues())

    def set_values(self, uid: str, values: AuthProfileValues) -> None:
        """Keeps them, then forgets the callers of the profile: a new hash."""
        self._values[uid] = values
        self.parent.sessions.forget_callers(uid)


# the auth


class AuthUnit(Unit):
    sessions = Slot(AuthSessionsUnit)
    sign_out = Slot(AuthSignOutUnit)
    profiles = Slot(AuthProfilesUnit)
    grp_signed_in = Slot(AuthSignedInGroup)

    def __init__(self) -> None:
        super().__init__()
        self.memberships: dict[str, set[str]] = {}  # uid: the names of its groups

    def form_caller(self, record: AuthSessionRecord) -> AuthCaller:
        """The caller of an open session: what its groups grant, the hash."""
        groups = (self.sessions.grp_admins, self.profiles.grp_managers)
        permissions = self.grp_signed_in.get_permissions()
        for group in groups:
            if group.full_name in self.memberships.get(record.uid, ()):
                permissions |= group.get_permissions()
        values = self.profiles.get_values(record.uid)
        return AuthCaller(
            uid=record.uid,
            permissions=permissions,
            session_id=record.id,
            profile_hash=_hash(
                json.dumps(
                    [
                        sorted(values.tag_ids),
                        sorted(values.attr_values.items()),
                        sorted(permissions.items()),
                    ]
                )
            ),
        )


class AuthProject(Project):
    auth = Slot(AuthUnit)


# the transport, cut down from ingot-grpcio and the contrib of the auth


class ServicerContext:
    """What a servicer sees of a call of grpc.aio: its metadata, its trailer."""

    def __init__(self, metadata: Mapping[str, str]) -> None:
        self._metadata = tuple(metadata.items())
        self.trailing_metadata: tuple[tuple[str, str], ...] = ()

    def invocation_metadata(self) -> tuple[tuple[str, str], ...]:
        return self._metadata

    def set_trailing_metadata(self, metadata: tuple[tuple[str, str], ...]) -> None:
        self.trailing_metadata = metadata


class GrpcServicer(Entity):
    """Of ingot-grpcio: runs an operation for the caller of a call."""

    @t.final
    async def run_operation[ParametersType, ResultType](
        self,
        factory: t.Callable[[], BaseOperation[ParametersType, ResultType]],
        parameters: ParametersType,
        context: ServicerContext,
    ) -> ResultType:
        return await run(factory, parameters, await self._get_caller(context))

    async def _get_caller(self, context: ServicerContext) -> Caller:
        return ANONYMOUS


class BaseAuthGrpcServicer(GrpcServicer):
    """
    A servicer of a signed-in caller, its caller of the token of a call: it
    tells the hash of the profile of the caller in the trailing metadata of
    the reply, so that every servicer of an application extending it does,
    no interceptor; one open to anyone has no profile to tell.
    """

    project: AuthProject

    @t.override
    async def _get_caller(self, context: ServicerContext) -> Caller:
        metadata = dict(context.invocation_metadata())
        token = metadata.get("authorization", "").removeprefix("Bearer ")
        caller = await self.project.auth.sessions.authenticate(token)
        if isinstance(caller, AuthCaller):
            context.set_trailing_metadata(((PROFILE_HASH_KEY, caller.profile_hash),))
        return caller


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
