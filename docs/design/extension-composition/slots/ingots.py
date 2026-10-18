"""Slots: a parent declares its children as typed descriptors, a subclass narrows them."""

import typing as t


class Slot[T: Entity]:
    """One entity per owner, created on first access. On the class: the slot itself."""

    def __init__(self, cls: type[T]) -> None:
        self.cls = cls

    def __set_name__(self, owner: type, name: str) -> None:
        self.name, self.key = name, f"_slot_{name}"

    @t.overload
    def __get__(self, obj: None, owner: type) -> "Slot[T]": ...
    @t.overload
    def __get__(self, obj: object, owner: type) -> T: ...
    def __get__(self, obj: object | None, owner: type) -> "Slot[T] | T":
        if obj is None:
            return self
        entity: T | None = obj.__dict__.get(self.key)
        if entity is None:
            project = obj if isinstance(obj, Project) else t.cast(Entity, obj).project
            entity = obj.__dict__[self.key] = self.cls(project)
        return entity

    def __set__(self, obj: object, value: t.Never) -> t.NoReturn:
        raise AttributeError(f"{self.name} is a slot: narrow it in a subclass")

    def __repr__(self) -> str:
        return f"Slot({self.cls.__qualname__})"


def check_slots(cls: type) -> None:
    """A subclass's slot must hold a subclass of what every direct base holds."""
    for base in cls.__bases__:
        for name in dir(base):
            base_slot = getattr(base, name)
            if not isinstance(base_slot, Slot):
                continue
            slot = getattr(cls, name)
            if not (isinstance(slot, Slot) and issubclass(slot.cls, base_slot.cls)):
                raise TypeError(
                    f"{cls.__qualname__}.{name} = {slot!r} does not extend "
                    f"{base.__qualname__}.{name} = {base_slot!r}: define "
                    f"{cls.__qualname__}.{name} with a class extending all bases' ones"
                )


class Node:
    """A project or an entity: its slots are checked when the class is created."""

    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        check_slots(cls)


class Project(Node):
    pass


class Entity(Node):
    """Belongs to one project. A subclass narrows it: `project: "AppProject"`."""

    def __init__(self, project: Project) -> None:
        self.project = project


class Unit(Entity):
    """An entity grouping other entities in slots."""


# ingots/defaults: what every project has and every addon may extend


class Settings(Entity):
    DEBUG = False


class DefaultProject(Project):
    settings = Slot(Settings)
