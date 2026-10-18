"""An addon: a tree three levels deep, its own settings."""

import typing as t
from functools import cached_property

from ingots import DefaultProject, Entity, Settings, Unit, extensible


class Pkg1Settings(Settings):
    PKG1_OPTION = "pkg1"


@extensible
class Pkg1Entity(Entity):
    project: "Pkg1Project"

    def method(self) -> str:
        settings = t.cast(Pkg1Settings, self.project.settings)  # typed only in its own branch
        return f"Pkg1Entity({settings.PKG1_OPTION})"


@extensible
class Pkg1SubUnit(Unit):
    @cached_property
    def entity(self) -> Pkg1Entity:
        return Pkg1Entity.create(self.project)


@extensible
class Pkg1Unit(Unit):
    @cached_property
    def sub_unit(self) -> Pkg1SubUnit:
        return Pkg1SubUnit.create(self.project)


class Pkg1Project(DefaultProject):
    @classmethod
    def register_extensions(cls) -> None:
        super().register_extensions()
        Settings.d.add(Pkg1Settings)

    @cached_property
    def pkg1_unit(self) -> Pkg1Unit:
        return Pkg1Unit.create(self)
