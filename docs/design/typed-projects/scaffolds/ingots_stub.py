"""
What the scaffolds need of ingots: the place of an entity, its slots, the
check of a slot inherited from bases holding different classes (ADR 0018),
the settings and their configs, the project.
"""

import typing as t
import weakref


class Entity:
    """Under its parents, the project the first, its parent the last."""

    _entity_parents: "tuple[weakref.ref[SlotsOwner], ...]"

    def __init__(self) -> None:
        pass

    @property
    def project(self) -> "Project":
        return t.cast("Project", self._entity_parents[0]())

    @property
    def parent(self) -> "SlotsOwner":
        return t.cast("SlotsOwner", self._entity_parents[-1]())


class SlotsOwner:
    """What owns slots: the project, a unit."""

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        names = {
            name
            for base in cls.__mro__[1:]
            for name, value in vars(base).items()
            if isinstance(value, Slot)
        }
        for name in names - set(vars(cls)):
            held = {
                getattr(base, name).cls for base in cls.__bases__ if hasattr(base, name)
            }
            if not any(all(issubclass(one, other) for other in held) for one in held):
                raise TypeError(f"{cls.__qualname__}.{name}: join {held} in a class")

    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        raise NotImplementedError


class Slot[EntityType: Entity]:
    """One entity per parent, created on first access."""

    _name: str

    def __init__(self, cls: type[EntityType]) -> None:
        self._cls = cls

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @property
    def cls(self) -> type[EntityType]:
        return self._cls

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
            entity = self._cls.__new__(self._cls)
            entity._entity_parents = obj._slots_get_parents()
            entity.__init__()  # type: ignore[misc]
            obj.__dict__[key] = entity
        return entity


class Unit(SlotsOwner, Entity):
    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        return (*self._entity_parents, weakref.ref(self))


class Configs(Entity):
    """The configs of a project: each addon mixes its own in, by inheritance."""

    IS_DEBUG: bool = False


class SettingsUnit(Unit):
    configs = Slot(Configs)


class Project(SlotsOwner):
    """The root: the first parent of every entity."""

    settings = Slot(SettingsUnit)

    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        return (weakref.ref(self),)
