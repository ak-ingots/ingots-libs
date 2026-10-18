"""An addon: a tree three levels deep, its own settings."""

import typing as t

from ingots import DefaultProject, Entity, Settings, Unit

type AnyPkg1Project = Pkg1Project[Pkg1Settings, t.Any]


class Pkg1Settings(Settings):
    PKG1_OPTION = "pkg1"


class Pkg1Entity[P: AnyPkg1Project](Entity[P]):
    def method(self) -> str:
        return f"Pkg1Entity({self.project.settings.PKG1_OPTION})"


class Pkg1SubUnit[P: AnyPkg1Project, E: Pkg1Entity[t.Any]](Unit[P]):
    entity_cls: type[Pkg1Entity[t.Any]] = Pkg1Entity

    def __init__(self, project: P) -> None:
        super().__init__(project)
        self._entity = self.entity_cls(project)

    @property
    def entity(self) -> E:
        return t.cast(E, self._entity)


class Pkg1Unit[P: AnyPkg1Project, S: Pkg1SubUnit[t.Any, t.Any]](Unit[P]):
    sub_unit_cls: type[Pkg1SubUnit[t.Any, t.Any]] = Pkg1SubUnit

    def __init__(self, project: P) -> None:
        super().__init__(project)
        self._sub_unit = self.sub_unit_cls(project)

    @property
    def sub_unit(self) -> S:
        return t.cast(S, self._sub_unit)


class Pkg1Project[S: Pkg1Settings, U: Pkg1Unit[t.Any, t.Any]](DefaultProject[S]):
    settings_cls = Pkg1Settings
    pkg1_unit_cls: type[Pkg1Unit[t.Any, t.Any]] = Pkg1Unit

    def __init__(self) -> None:
        super().__init__()
        self._pkg1_unit = self.pkg1_unit_cls(self)

    @property
    def pkg1_unit(self) -> U:
        return t.cast(U, self._pkg1_unit)
