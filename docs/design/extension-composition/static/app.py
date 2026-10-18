"""The application: combines both addons, customizes pkg1's entity three levels deep."""

from pkg1 import Pkg1Entity, Pkg1Project, Pkg1Settings, Pkg1SubUnit, Pkg1Unit
from pkg2 import Pkg2Project, Pkg2Settings, Pkg2Unit


class AppSettings(Pkg1Settings, Pkg2Settings):  # both addons extend settings: an explicit join
    APP_OPTION = "app"


class AppEntity(Pkg1Entity["AppProject"]):
    def method(self) -> str:
        return f"{super().method()} + {self.project.pkg2_unit.method()} + {self.project.settings.APP_OPTION}"


# one class per level, each repeating the parameters of the levels below
class AppSubUnit(Pkg1SubUnit["AppProject", AppEntity]):
    entity_cls = AppEntity


class AppUnit(Pkg1Unit["AppProject", AppSubUnit]):
    sub_unit_cls = AppSubUnit


class AppProject(
    Pkg1Project[AppSettings, AppUnit],
    Pkg2Project[AppSettings, Pkg2Unit["AppProject"]],
):
    settings_cls = AppSettings
    pkg1_unit_cls = AppUnit


if __name__ == "__main__":
    print(AppProject().pkg1_unit.sub_unit.entity.method())
