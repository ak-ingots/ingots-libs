"""Another addon: something else entirely, its own settings."""

import typing as t

from ingots import DefaultProject, Settings, Unit


class Pkg2Settings(Settings):
    PKG2_OPTION = "pkg2"


class Pkg2Unit[P: Pkg2Project[Pkg2Settings, t.Any]](Unit[P]):
    def method(self) -> str:
        return f"Pkg2Unit({self.project.settings.PKG2_OPTION})"


class Pkg2Project[S: Pkg2Settings, U: Pkg2Unit[t.Any]](DefaultProject[S]):
    settings_cls = Pkg2Settings
    pkg2_unit_cls: type[Pkg2Unit[t.Any]] = Pkg2Unit

    def __init__(self) -> None:
        super().__init__()
        self._pkg2_unit = self.pkg2_unit_cls(self)

    @property
    def pkg2_unit(self) -> U:
        return t.cast(U, self._pkg2_unit)
