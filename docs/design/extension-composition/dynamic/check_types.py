# What mypy (and the IDE) sees versus what runs: `reveal_type` prints both.

import typing as t

from app import AppProject
from pkg2 import Pkg2Project

AppProject.register_extensions()
p = AppProject()
t.reveal_type(p.pkg1_unit.sub_unit.entity)  # mypy: Pkg1Entity, runtime: Pkg1EntityFinal
t.reveal_type(p.settings)  # mypy: Settings, runtime: SettingsFinal
print("SettingsFinal bases:", [c.__name__ for c in type(p.settings).__bases__])  # order varies between runs

print(p.settings.APP_OPTION)  # type: ignore[attr-defined]  # works, mypy can't see it

# extensions are global: a project made of pkg2 alone gets pkg1's and the app's ones
print("Pkg2Project settings:", type(Pkg2Project().settings).__bases__)

# the extension point is inherited: Pkg1Entity.d is AppEntity.d, no error
from app import AppEntity
from pkg1 import Pkg1Entity

print("AppEntity.d is Pkg1Entity.d:", AppEntity.d is Pkg1Entity.d)
