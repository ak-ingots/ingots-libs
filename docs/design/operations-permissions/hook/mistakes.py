"""
The mistakes mypy refuses, apart: the misspelled flag fails the import
already, so nothing runs this module.
"""

import typing as t

from ingots_stub import BaseOperation, Permissions, Project
from shop import ShopPermissions, ShopProject


class ShopMisspelled(BaseOperation[int, int]):
    PERMISSIONS = Permissions(ShopPermissions.CAN_PAI)  # error: no such flag

    @t.override
    async def _run(self, parameters: int) -> int:
        return parameters


class ShopClassHook(BaseOperation[int, int]):
    """The hook of the class, as first thought: the project narrowed is refused."""

    PERMISSIONS = Permissions()

    @classmethod
    def _get_class_permissions(cls, project: Project) -> Permissions:
        return Permissions()

    @t.override
    async def _run(self, parameters: int) -> int:
        return parameters


class ShopClassHookRefund(ShopClassHook):
    @t.override
    @classmethod
    def _get_class_permissions(cls, project: ShopProject) -> Permissions:  # error: narrows the argument
        return Permissions(ShopPermissions.CAN_REFUND)
