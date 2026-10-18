# What mypy (and the IDE) sees, and what is rejected.

import typing as t

from app import AppProject

p = AppProject()
t.reveal_type(p.pkg1_unit.sub_unit.entity)  # AppEntity
t.reveal_type(p.pkg1_unit.sub_unit.entity.project)  # AppProject
t.reveal_type(p.settings)  # AppSettings

if t.TYPE_CHECKING:
    from app import AppSettings
    from pkg1 import Pkg1Project, Pkg1Settings
    from pkg2 import Pkg2Project, Pkg2Settings

    p.settings.NO_SUCH_OPTION  # error: no attribute

    class Unjoined(Pkg1Project[Pkg1Settings, t.Any], Pkg2Project[Pkg2Settings, t.Any]):  # error: settings differ
        pass

    class Mismatched(Pkg1Project[Pkg1Settings, t.Any]):
        settings_cls = int  # error: not a settings class

    # not caught: the parameter says one class, the attribute creates another
    class Lying(Pkg1Project[AppSettings, t.Any]):
        settings_cls = Pkg1Settings
