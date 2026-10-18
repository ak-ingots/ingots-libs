"""The application: combines both addons, customizes pkg1's entity three levels deep."""

import typing as t

from ingots import Settings
from pkg1 import Pkg1Entity, Pkg1Project
from pkg2 import Pkg2Project


class AppSettings(Settings):  # joined with both addons' settings automatically
    APP_OPTION = "app"


class AppEntity(Pkg1Entity):
    project: "AppProject"

    def method(self) -> str:
        settings = t.cast(AppSettings, self.project.settings)
        return f"{super().method()} + {self.project.pkg2_unit.method()} + {settings.APP_OPTION}"


class AppProject(Pkg1Project, Pkg2Project):
    @classmethod
    def register_extensions(cls) -> None:
        super().register_extensions()
        Settings.d.add(AppSettings)
        Pkg1Entity.d.add(AppEntity)  # one line, however deep the entity is


if __name__ == "__main__":
    AppProject.register_extensions()
    print(AppProject().pkg1_unit.sub_unit.entity.method())
