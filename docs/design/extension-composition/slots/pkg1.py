"""An addon: a tree three levels deep, its own settings."""

from ingots import DefaultProject, Entity, Settings, Slot, Unit


class Pkg1Settings(Settings):
    PKG1_OPTION = "pkg1"


class Pkg1Entity(Entity):
    project: "Pkg1Project"  # the addon sees its own project, typed

    def method(self) -> str:
        return f"Pkg1Entity({self.project.settings.PKG1_OPTION})"


class Pkg1SubUnit(Unit):
    entity = Slot(Pkg1Entity)


class Pkg1Unit(Unit):
    sub_unit = Slot(Pkg1SubUnit)


class Pkg1Project(DefaultProject):
    settings = Slot(Pkg1Settings)
    pkg1_unit = Slot(Pkg1Unit)
