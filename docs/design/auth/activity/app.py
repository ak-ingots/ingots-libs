"""
The consumers, the code of applications: one picks the strict log, another
the swallowed one; the latter's storage loses its log.
"""

from auth_stub import (
    AuthActivitiesUnit,
    AuthProject,
    AuthStrictActivityFailure,
    AuthSwallowActivityFailure,
    AuthUnit,
)
from ingots_stub import Slot


class StrictActivitiesUnit(AuthActivitiesUnit):
    failure = Slot(AuthStrictActivityFailure)


class SwallowActivitiesUnit(AuthActivitiesUnit):
    failure = Slot(AuthSwallowActivityFailure)


class StrictAuth(AuthUnit):
    activities = Slot(StrictActivitiesUnit)


class SwallowAuth(AuthUnit):
    activities = Slot(SwallowActivitiesUnit)


class StrictProject(AuthProject):
    auth = Slot(StrictAuth)


class SwallowProject(AuthProject):
    auth = Slot(SwallowAuth)
