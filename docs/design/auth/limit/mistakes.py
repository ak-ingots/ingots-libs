"""The lines mypy refuses: what the application cannot get wrong."""

from auth_stub import AuthSessionsUnit, AuthSlidingLifetime, BaseAuthSessionsLimit
from ingots_stub import Slot


class Sessions(AuthSessionsUnit):
    limit = Slot(AuthSlidingLifetime)  # error: a lifetime is no limit


class AbstractSessions(AuthSessionsUnit):
    limit = Slot(BaseAuthSessionsLimit)  # error: no strategy picked
