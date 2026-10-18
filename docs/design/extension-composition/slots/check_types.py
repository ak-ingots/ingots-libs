# What mypy (and the IDE) sees, and what is rejected. Runs as well: the
# rejected class definitions raise TypeError at import time.

import typing as t

from app import AppProject
from ingots import Entity, Slot
from pkg1 import Pkg1Project
from pkg2 import Pkg2Project

p = AppProject()
t.reveal_type(p.pkg1_unit.sub_unit.entity)  # AppEntity
t.reveal_type(p.pkg1_unit.sub_unit.entity.project)  # AppProject
t.reveal_type(p.settings)  # AppSettings

if t.TYPE_CHECKING:
    p.settings.NO_SUCH_OPTION  # error: no attribute
    p.pkg1_unit = p.pkg1_unit  # error: a slot is narrowed in a subclass, not assigned

try:

    class Unjoined(Pkg1Project, Pkg2Project):  # error: settings differ in the bases
        pass

except TypeError as exc:
    print(f"Unjoined: {exc}")

try:

    class Other(Entity):
        pass

    class Unrelated(Pkg1Project):
        settings = Slot(Other)  # error: Other does not extend Pkg1Settings

except TypeError as exc:
    print(f"Unrelated: {exc}")
