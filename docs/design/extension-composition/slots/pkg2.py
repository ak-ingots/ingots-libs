"""Another addon: something else entirely, its own settings."""

from ingots import DefaultProject, Settings, Slot, Unit


class Pkg2Settings(Settings):
    PKG2_OPTION = "pkg2"


class Pkg2Unit(Unit):
    project: "Pkg2Project"

    def method(self) -> str:
        return f"Pkg2Unit({self.project.settings.PKG2_OPTION})"


class Pkg2Project(DefaultProject):
    settings = Slot(Pkg2Settings)
    pkg2_unit = Slot(Pkg2Unit)
