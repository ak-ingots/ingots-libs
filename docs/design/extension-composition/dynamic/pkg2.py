"""Another addon: something else entirely, its own settings."""

import typing as t
from functools import cached_property

from ingots import DefaultProject, Settings, Unit, extensible


class Pkg2Settings(Settings):
    PKG2_OPTION = "pkg2"


@extensible
class Pkg2Unit(Unit):
    project: "Pkg2Project"

    def method(self) -> str:
        settings = t.cast(Pkg2Settings, self.project.settings)
        return f"Pkg2Unit({settings.PKG2_OPTION})"


class Pkg2Project(DefaultProject):
    @classmethod
    def register_extensions(cls) -> None:
        super().register_extensions()
        Settings.d.add(Pkg2Settings)

    @cached_property
    def pkg2_unit(self) -> Pkg2Unit:
        return Pkg2Unit.create(self)
