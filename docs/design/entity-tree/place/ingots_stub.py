"""
What the prototype needs of ingots, cut down to the place of an entity: the
owner of an entity, its slot or its factory, creates it, its place set by one
call before its ``__init__``, which takes none: its parents, from the project
to its parent, and its name; the permissions of a unit, their domain the full
name of the unit.
"""

import abc
import enum
import functools
import typing as t
import weakref
from collections.abc import Iterator, Mapping


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
    def __get__(
        self, obj: SlotsOwner, owner: type
    ) -> "t.Callable[[], EntityType]": ...

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
    async def _run(self, parameters: ParametersType) -> ResultType:
        raise NotImplementedError


class OperationPermissionsError(Exception):
    pass


async def run[ParametersType, ResultType](
    factory: "t.Callable[[], BaseOperation[ParametersType, ResultType]]",
    parameters: ParametersType,
    caller: Permissions,
) -> ResultType:
    """The runner: the operation first, then its permissions, then the run."""
    operation = factory()
    required = operation.get_permissions()
    if not caller.has(required):
        raise OperationPermissionsError(operation.full_name, dict(required))
    return await operation._run(parameters)
