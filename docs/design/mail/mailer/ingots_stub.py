"""
What the prototype needs of ingots: the slots and their entities, the units,
the project, the configs as plain typed attributes.
"""

import typing as t


class Entity:
    """Knows its project; the slot sets it before ``__init__``."""

    project: "Project"

    def __init__(self) -> None:
        pass


class SlotsOwner:
    """What owns slots: the project, a unit."""

    project: "Project"


class Slot[EntityType: Entity]:
    """One entity per owner, created on first access."""

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
            entity.project = obj.project
            entity.__init__()  # type: ignore[misc]
            obj.__dict__[key] = entity
        return entity


class Unit(SlotsOwner, Entity):
    pass


class Configs(Entity):
    """The configs: a typed attribute a config, its default the value here."""


class SettingsUnit(Unit):
    configs = Slot(Configs)


class Project(SlotsOwner):
    settings = Slot(SettingsUnit)

    def __init__(self) -> None:
        self.project = self
