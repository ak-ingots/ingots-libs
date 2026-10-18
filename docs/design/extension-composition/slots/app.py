"""The application: combines both addons, customizes pkg1's entity three levels deep."""

from ingots import Slot
from pkg1 import Pkg1Entity, Pkg1Project, Pkg1Settings, Pkg1SubUnit, Pkg1Unit
from pkg2 import Pkg2Project, Pkg2Settings


class AppSettings(Pkg1Settings, Pkg2Settings):  # both addons extend settings: an explicit join
    APP_OPTION = "app"


class AppEntity(Pkg1Entity):
    project: "AppProject"  # narrowed: the neighbour addon is visible and typed

    def method(self) -> str:
        return f"{super().method()} + {self.project.pkg2_unit.method()} + {self.project.settings.APP_OPTION}"


# one short class per level down to the customized entity
class AppSubUnit(Pkg1SubUnit):
    entity = Slot(AppEntity)


class AppUnit(Pkg1Unit):
    sub_unit = Slot(AppSubUnit)


class AppProject(Pkg1Project, Pkg2Project):
    settings = Slot(AppSettings)
    pkg1_unit = Slot(AppUnit)


if __name__ == "__main__":
    print(AppProject().pkg1_unit.sub_unit.entity.method())
