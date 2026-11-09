"""An addon: an operation of constant permissions, one of permissions by the project."""

import typing as t

from ingots_stub import BaseOperation, PermissionFlags, Permissions, Project


class ShopPermissions(PermissionFlags, domain="shop"):
    CAN_PAY = 1 << 0
    CAN_REFUND = 1 << 1
    CAN_REFUND_ANY = 1 << 2


class ShopProject(Project):
    REFUND_LIMIT: int = 100  # a config, as the settings would give it


class ShopPay(BaseOperation[int, int]):
    PERMISSIONS = Permissions(ShopPermissions.CAN_PAY)

    @t.override
    async def _run(self, parameters: int) -> int:
        return parameters


class ShopRefund(BaseOperation[int, int]):
    """A refund over the limit of the project needs more: of the project, not the class."""

    project: ShopProject

    @t.override
    def _get_permissions(self) -> Permissions:
        if self.project.REFUND_LIMIT == 0:
            return Permissions(ShopPermissions.CAN_REFUND | ShopPermissions.CAN_REFUND_ANY)
        return Permissions(ShopPermissions.CAN_REFUND)

    @t.override
    async def _run(self, parameters: int) -> int:
        return -parameters
