"""
The consumer, the code of an application: a game, a later sign-in signing
out the earlier ones; how many sessions it keeps its operator sets.
"""

from auth_stub import AuthEvictOldestLimit, AuthProject, AuthSessionsUnit, AuthUnit
from ingots_stub import Slot


class SessionsUnit(AuthSessionsUnit):
    limit = Slot(AuthEvictOldestLimit)


class Auth(AuthUnit):
    sessions = Slot(SessionsUnit)


class AppProject(AuthProject):
    auth = Slot(Auth)
