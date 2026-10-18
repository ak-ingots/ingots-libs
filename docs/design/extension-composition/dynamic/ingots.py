"""Dynamic: extensions are registered on a descriptor, the final class is built by type()."""

import typing as t
from functools import cached_property


class Descriptor[T: Entity]:
    """
    Collects the extensions of an entity class and creates its instances from
    a final class built of the "leaves": diamond hierarchies merge without MRO
    errors because intermediate classes are left out.
    """

    def __init__(self, cls: type[T]) -> None:
        self.base = cls
        self.extensions: set[type[T]] = set()  # a set: the bases' order is not defined
        self._final: type[T] | None = None

    def add(self, *extensions: type[T]) -> None:
        for ext in extensions:
            if not issubclass(ext, self.base):
                raise TypeError(f"{ext!r} does not extend {self.base!r}")
            self.extensions.add(ext)
        self._final = None

    def final(self) -> type[T]:
        if self._final is None:
            classes = {self.base, *self.extensions}
            leaves = [c for c in classes if not any(o is not c and issubclass(o, c) for o in classes)]
            self._final = t.cast(type[T], type(f"{self.base.__name__}Final", tuple(leaves), {}))
        return self._final

    def create(self, project: "Project") -> T:
        return self.final()(project)


def extensible[C: type[Entity]](cls: C) -> C:
    """Gives an entity class its descriptor: `cls.d`. Subclasses inherit it silently."""
    cls.d = Descriptor(cls)
    return cls


class Project:
    @classmethod
    def register_extensions(cls) -> None:
        """Cooperative: every addon calls super(), then adds its extensions."""


class Entity:
    d: t.ClassVar[Descriptor[t.Any]]

    def __init__(self, project: Project) -> None:
        self.project = project

    @classmethod
    def create(cls, project: Project) -> t.Self:
        """An instance of the final class: typed as `cls`, whatever was added to it."""
        return t.cast(t.Self, cls.d.create(project))


class Unit(Entity):
    pass


# ingots/defaults


@extensible
class Settings(Entity):
    DEBUG = False


class DefaultProject(Project):
    @cached_property
    def settings(self) -> Settings:  # the final class at runtime, the base for mypy
        return Settings.create(self)
