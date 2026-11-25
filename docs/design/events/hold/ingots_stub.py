"""
What the prototype needs of ingots, copied from that of the entity tree: the
place of an entity, the permissions of a unit by its slot; with the caller
and the metadata of a run, which an operation reads its caller from. New
here, at the end: ``Factories`` as ingots has it, and the events, the unit
``project.events`` the design proposes for ``ingots.defaults``.
"""

import abc
import asyncio
import contextlib
import contextvars
import dataclasses
import enum
import functools
import logging
import typing as t
import weakref
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator, Mapping

logger = logging.getLogger("ingots")


class Entity:
    """
    Under its parents, from the project to its parent, at its name: its owner
    sets them by one call, :meth:`_entity_set_place`, before its ``__init__``,
    the parents as weak references. The rest follows: :attr:`project`, the
    first, :attr:`parent`, the last, :attr:`full_name`, the path from the
    project, :meth:`find_parent`, the nearest of a kind.
    """

    _entity_parents: "tuple[weakref.ref[SlotsOwner], ...]"
    _entity_name: str

    def __init__(self) -> None:
        pass

    @t.final
    def _entity_set_place(
        self, parents: "tuple[weakref.ref[SlotsOwner], ...]", name: str
    ) -> None:
        """Internal: the one call of the owner, before ``__init__``."""
        self._entity_parents = parents
        self._entity_name = name

    @property
    def parents(self) -> "tuple[SlotsOwner, ...]":
        return tuple(_deref(parent) for parent in self._entity_parents)

    @property
    def project(self) -> "Project":
        return t.cast("Project", _deref(self._entity_parents[0]))

    @property
    def parent(self) -> "SlotsOwner":
        return _deref(self._entity_parents[-1])

    @property
    def name(self) -> str:
        return self._entity_name

    @functools.cached_property
    def full_name(self) -> str:
        """The path from the project, built on its first use."""
        prefix = self.parent._slots_get_full_name()
        return f"{prefix}.{self.name}" if prefix else self.name

    @t.final
    def find_parent[ParentType](self, kind: type[ParentType]) -> ParentType:
        """
        The nearest of its parents of a kind.

        :raises LookupError: none is.
        """
        for parent in reversed(self.parents):
            if isinstance(parent, kind):
                return parent
        raise LookupError(f"{self.full_name}: no parent of {kind.__qualname__}")


def _deref[ObjectType](ref: "weakref.ref[ObjectType]") -> ObjectType:
    obj = ref()
    if obj is None:
        raise ReferenceError("the project is gone")
    return obj


class SlotsOwner:
    """What owns slots: the project, a unit."""

    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        """The parents of its children: its own, then itself."""
        raise NotImplementedError

    def _slots_get_full_name(self) -> str:
        raise NotImplementedError


class BaseSlot[EntityType: Entity]:
    """
    The owner of the entities of an attribute: it creates them, by
    :meth:`create_entity`, final, the place set first, one call, then what
    the kind of slot gives, its hook :meth:`_prepare_entity`, then
    ``__init__()``.
    """

    _name: str

    def __init__(self, cls: type[EntityType]) -> None:
        self._cls = cls

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @property
    def cls(self) -> type[EntityType]:
        return self._cls

    @t.final
    def create_entity(self, parent: SlotsOwner) -> EntityType:
        entity = self._cls.__new__(self._cls)
        entity._entity_set_place(parent._slots_get_parents(), self._name)
        self._prepare_entity(entity, parent)
        entity.__init__()  # type: ignore[misc]
        return entity

    def _prepare_entity(self, entity: EntityType, parent: SlotsOwner) -> None:
        """What the kind of slot gives its entities before their ``__init__``."""


class Slot[EntityType: Entity](BaseSlot[EntityType]):
    """One entity per parent, created on first access."""

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: SlotsOwner, owner: type) -> EntityType: ...

    def __get__(self, obj: SlotsOwner | None, owner: type) -> t.Self | EntityType:
        if obj is None:
            return self
        key = f"_slot_{self._name}"
        try:
            entity: EntityType = obj.__dict__[key]
        except KeyError:
            entity = obj.__dict__[key] = self.create_entity(obj)
        return entity


class Factory[EntityType: Entity](BaseSlot[EntityType]):
    """A new entity on every call, each at the full name of the factory."""

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: SlotsOwner, owner: type) -> "t.Callable[[], EntityType]": ...

    def __get__(
        self, obj: SlotsOwner | None, owner: type
    ) -> "t.Self | t.Callable[[], EntityType]":
        if obj is None:
            return self
        return lambda: self.create_entity(obj)


class Unit(SlotsOwner, Entity):
    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        return (*self._entity_parents, weakref.ref(self))

    def _slots_get_full_name(self) -> str:
        return self.full_name


class Project(SlotsOwner):
    """The root: the first parent of every entity, its full name empty."""

    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        return (weakref.ref(self),)

    def _slots_get_full_name(self) -> str:
        return ""


class PermissionFlags(enum.IntFlag, boundary=enum.KEEP):
    """The flags of a domain: no name of their own, the unit binding them gives it."""


class Permissions(Mapping[str, int]):
    """A mask per domain: a flag alone tells no domain, a unit builds them."""

    def __init__(self, *masks: Mapping[str, int]) -> None:
        merged: dict[str, int] = {}
        for item in masks:
            for domain, mask in item.items():
                merged[domain] = merged.get(domain, 0) | int(mask)
        self._masks = {domain: mask for domain, mask in merged.items() if mask}

    def __getitem__(self, domain: str) -> int:
        return self._masks[domain]

    def __iter__(self) -> Iterator[str]:
        return iter(self._masks)

    def __len__(self) -> int:
        return len(self._masks)

    def __or__(self, other: Mapping[str, int]) -> "Permissions":
        return Permissions(self, other)

    def has(self, required: Mapping[str, int]) -> bool:
        return all(
            self._masks.get(domain, 0) & mask == mask
            for domain, mask in required.items()
        )


class BoundPermissions[FlagsType: PermissionFlags]:
    """
    The permissions of a unit: its :attr:`flags`, the enum, and its
    :attr:`domain`, its full name; called with flags, their mask there.
    """

    def __init__(self, flags: type[FlagsType], domain: str) -> None:
        self._flags = flags
        self._domain = domain

    @property
    def flags(self) -> type[FlagsType]:
        return self._flags

    @property
    def domain(self) -> str:
        return self._domain

    def __call__(self, *flags: FlagsType) -> Permissions:
        """The mask of flags of the unit, in its domain."""
        mask = 0
        for flag in flags:
            mask |= int(flag)
        return Permissions({self._domain: mask})


class PermissionsSlot[FlagsType: PermissionFlags]:
    """
    The slot binding an enum of flags to a unit, ``permissions``: on the class
    the slot, its :attr:`flags` the enum; on a unit, its
    :class:`BoundPermissions`, of its domain, the full name of the unit,
    created once a unit.
    """

    def __init__(self, flags: type[FlagsType]) -> None:
        self._flags = flags

    @property
    def flags(self) -> type[FlagsType]:
        return self._flags

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: Entity, owner: type) -> BoundPermissions[FlagsType]: ...

    def __get__(
        self, obj: Entity | None, owner: type
    ) -> t.Self | BoundPermissions[FlagsType]:
        if obj is None:
            return self
        try:
            bound: BoundPermissions[FlagsType] = obj.__dict__["_permissions_bound"]
        except KeyError:
            bound = BoundPermissions(self._flags, obj.full_name)
            obj.__dict__["_permissions_bound"] = bound  # one a unit
        return bound


class OperationsOwner(Entity):
    """
    A mixin of a unit owning operations, which are not its base: its slot
    ``permissions`` binds the flags of their permissions, their domain its
    full name, ``shop.stock``.
    """

    permissions: PermissionsSlot[t.Any]


class BaseOperation[ParametersType, ResultType](Entity):
    """
    Its permissions are of its hook :meth:`_get_permissions`, abstract: it
    builds them by the permissions of a unit, its parent narrowed, so that
    mypy checks the flags, the place and the unit; ``Permissions()`` for
    none. An integration adds the permissions of the operations it runs.
    """

    @t.final
    def get_permissions(self) -> Permissions:
        return self._get_permissions()

    @abc.abstractmethod
    def _get_permissions(self) -> Permissions:
        raise NotImplementedError

    @abc.abstractmethod
    async def _run(
        self, parameters: ParametersType, metadata: "OperationMetadata"
    ) -> ResultType:
        raise NotImplementedError


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Caller:
    """Who runs an operation, a user, a service, a command, by its uid."""

    uid: str
    permissions: Permissions
    is_root: bool = False


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OperationMetadata:
    caller: Caller


ROOT = Caller(uid="root", permissions=Permissions(), is_root=True)
ANONYMOUS = Caller(uid="anonymous", permissions=Permissions())


class OperationPermissionsError(Exception):
    pass


async def run[ParametersType, ResultType](
    factory: "t.Callable[[], BaseOperation[ParametersType, ResultType]]",
    parameters: ParametersType,
    caller: Caller,
) -> ResultType:
    """The runner: the operation first, then its permissions, then the run."""
    operation = factory()
    required = operation.get_permissions()
    if not caller.is_root and not caller.permissions.has(required):
        raise OperationPermissionsError(operation.full_name, dict(required))
    return await operation._run(parameters, OperationMetadata(caller=caller))


# -- Factories, as ingots has them ---------------------------------------------


class Factories[EntityType: Entity]:
    """A new entity of each of its classes on every call, in their order."""

    _name: str

    def __init__(self, *classes: type[EntityType]) -> None:
        self._classes = classes

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @property
    def classes(self) -> tuple[type[EntityType], ...]:
        return self._classes

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: SlotsOwner, owner: type) -> "BoundFactories[EntityType]": ...

    def __get__(
        self, obj: SlotsOwner | None, owner: type
    ) -> "t.Self | BoundFactories[EntityType]":
        if obj is None:
            return self
        return BoundFactories(self, obj)


@t.final
class BoundFactories[EntityType: Entity]:
    """A :class:`Factories` on its owner: a call creates one of each class."""

    def __init__(self, factories: Factories[EntityType], owner: SlotsOwner) -> None:
        self._factories = factories
        self._owner = owner

    @property
    def classes(self) -> tuple[type[EntityType], ...]:
        return self._factories.classes

    def __call__(self) -> list[EntityType]:
        created = []
        for cls in self._factories.classes:
            slot = BaseSlot(cls)
            slot.__set_name__(type(self._owner), self._factories._name)
            created.append(slot.create_entity(self._owner))
        return created


# -- the events, proposed for ingots.defaults ----------------------------------

type Subscribers[EventType] = BoundFactories[BaseOperation[EventType, None]]
"""The subscribers of an event: the slot ``ev_*`` of the unit of its domain."""


@t.final
class EventsScope:
    """
    A hold of the events published in its block: kept till it ends, then
    given to the scope it is in, or sent by the outermost. :meth:`discard`
    drops them: for the one that knows the facts they tell are undone, the
    rollback of a transaction.
    """

    def __init__(self, parent: "EventsScope | None") -> None:
        self._parent = parent
        self._pending: list[Callable[[], Coroutine[t.Any, t.Any, None]]] = []
        self._is_closed = False

    def discard(self) -> None:
        """Drops the events held in this scope, and in those it took in."""
        self._pending.clear()


# the scope of the current context: a hold nests in the one it is in
_scope: contextvars.ContextVar[EventsScope | None] = contextvars.ContextVar(
    "ingots_events_scope", default=None
)


class EventsUnit(Unit):
    """
    ``project.events``: the one way an event is published. Outside a hold,
    its subscribers run at once in the background; inside one, when the
    outermost hold ends. A subscriber is a reaction to a fact: it fails
    alone, logged, and never the flow that published it.
    """

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    @t.final
    def publish[EventType](
        self,
        subscribers: Subscribers[EventType],
        event: EventType,
        metadata: "OperationMetadata",
    ) -> None:
        """
        Publishes ``event`` to ``subscribers``, by the caller of
        ``metadata``: not awaited, the flow goes on.
        """

        def send() -> Coroutine[t.Any, t.Any, None]:
            return self._send(subscribers, event, metadata)

        scope = _scope.get()
        if scope is None:
            self._start(send)
        else:
            scope._pending.append(send)

    @t.final
    @contextlib.asynccontextmanager
    async def hold(self) -> AsyncIterator[EventsScope]:
        """
        Holds the events published in the block till it ends, raising or
        not: a fact published is a fact. The outermost hold sends them.
        """
        parent = _scope.get()
        scope = EventsScope(parent)
        token = _scope.set(scope)
        try:
            yield scope
        finally:
            _scope.reset(token)
            scope._is_closed = True
            if parent is not None and not parent._is_closed:
                parent._pending.extend(scope._pending)
            else:
                # the outermost, or a task outliving the hold it began in
                for send in scope._pending:
                    self._start(send)

    @t.final
    async def join(self) -> None:
        """Waits for the subscribers running and those they publish to."""
        while pending := [task for task in self._tasks if not task.done()]:
            await asyncio.gather(*pending)

    @t.final
    def _start(self, send: Callable[[], Coroutine[t.Any, t.Any, None]]) -> None:
        # in a context of no hold: what a subscriber publishes is its own
        context = contextvars.copy_context()
        context.run(_scope.set, None)
        task = asyncio.create_task(send(), context=context)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @t.final
    async def _send[EventType](
        self,
        subscribers: Subscribers[EventType],
        event: EventType,
        metadata: "OperationMetadata",
    ) -> None:
        await run_each_in_group(subscribers, event, metadata)


async def run_each_in_group[ParametersType](
    factories: BoundFactories[BaseOperation[ParametersType, t.Any]],
    parameters: ParametersType,
    metadata: OperationMetadata,
) -> None:
    """
    The runner, proposed for ingots: each operation of the group on its own,
    for operations that do not decide together, the subscribers of an
    event. The caller is checked for each: one it may not run is skipped,
    logged; the others run together to their end, a failure logged, none
    raised. Its pair, ``run_all_in_group``, the ``run_group`` of ingots
    renamed, runs the group as a whole: the caller checked for all before
    any runs, a refusal refusing all, the failures raised together.
    """
    caller = metadata.caller
    permitted = []
    for operation in factories():
        required = operation.get_permissions()
        if caller.is_root or caller.permissions.has(required):
            permitted.append(operation)
        else:
            logger.warning(
                "%s <%s>: %s may not run it, skipped",
                operation.full_name,
                type(operation).__qualname__,
                caller.uid,
            )
    outcomes = await asyncio.gather(
        *(operation._run(parameters, metadata) for operation in permitted),
        return_exceptions=True,
    )
    for operation, outcome in zip(permitted, outcomes):
        if isinstance(outcome, Exception):
            logger.warning(
                "%s <%s> failed: %r",
                operation.full_name,
                type(operation).__qualname__,
                outcome,
            )
