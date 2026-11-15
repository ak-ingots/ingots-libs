"""The lines mypy refuses: what slice 4 lets no one write."""

import typing as t
from collections.abc import Mapping

from app import ShopUnit
from auth_stub import (
    AttrValue,
    AuthRevokeOwnSessionParameters,
    AuthSessionsUnit,
    BaseAuthSessionAttrsDeriver,
)
from ingots_stub import Caller, Slot


class ListDeriver(BaseAuthSessionAttrsDeriver):
    @t.override
    async def _derive(  # error: a value of an attribute is no list
        self, values: Mapping[str, AttrValue]
    ) -> Mapping[str, list[str]]:
        return {}


class ShopSessions(AuthSessionsUnit):
    deriver = Slot(ShopUnit)  # error: a deriver goes in the slot


def sign_out(caller: Caller) -> None:
    print(caller.session_id)  # error: a caller may be anonymous, narrowed first


AuthRevokeOwnSessionParameters(id="s1")  # error: by the public id of a session
