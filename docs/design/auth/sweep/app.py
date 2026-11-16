"""
The consumer, the code of an application: a sliding lifetime of its
sessions, which the sweep asks.
"""

from auth_stub import AuthProject, AuthSessionsUnit, AuthSlidingLifetime, AuthUnit
from ingots_stub import Slot


class SessionsUnit(AuthSessionsUnit):
    lifetime = Slot(AuthSlidingLifetime)


class Auth(AuthUnit):
    sessions = Slot(SessionsUnit)


class AppProject(AuthProject):
    auth = Slot(Auth)
