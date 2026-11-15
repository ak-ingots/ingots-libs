"""
The consumers of slice 4, the code of an application: a strategy deriving
the place of a session from its IP, bound in the slot of the sessions; a
shop served to signed-in callers, its servicer telling the hash of the
profile in every reply, granted to every signed-in user.
"""

import typing as t
from collections.abc import Mapping

from auth_stub import (
    AttrValue,
    AuthProject,
    AuthSessionsUnit,
    AuthSignedInGroup,
    AuthUnit,
    BaseAuthGrpcServicer,
    BaseAuthSessionAttrsDeriver,
    ServicerContext,
)
from ingots_stub import (
    BaseOperation,
    Factory,
    OperationMetadata,
    OperationsOwner,
    PermissionFlags,
    Permissions,
    PermissionsSlot,
    Slot,
    Unit,
)


class GeoIpDeriver(BaseAuthSessionAttrsDeriver):
    """The country of the IP, as a base of GeoIP would tell it."""

    COUNTRIES: t.ClassVar[Mapping[str, str]] = {"192.0.2.1": "PL", "198.51.100.7": "DE"}

    @t.override
    async def _derive(self, values: Mapping[str, AttrValue]) -> Mapping[str, AttrValue]:
        ip = values.get("ip")
        country = self.COUNTRIES.get(ip) if isinstance(ip, str) else None
        return {"country": country} if country else {}


class AppSessions(AuthSessionsUnit):
    deriver = Slot(GeoIpDeriver)


class ShopPermissions(PermissionFlags):
    CAN_BUY = 1 << 0


class BuyOperation(BaseOperation[str, str]):
    parent: "ShopUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_BUY)

    @t.override
    async def _run(self, parameters: str, metadata: OperationMetadata) -> str:
        return f"{metadata.caller.uid} bought {parameters}"


class ShopUnit(OperationsOwner, Unit):
    permissions = PermissionsSlot(ShopPermissions)

    op_buy = Factory(BuyOperation)


class AppSignedInGroup(AuthSignedInGroup):
    project: "AppProject"

    @t.override
    def _get_permissions(self) -> Permissions:
        shop = self.project.shop.permissions
        return super()._get_permissions() | shop(shop.flags.CAN_BUY)


class AppAuth(AuthUnit):
    sessions = Slot(AppSessions)
    grp_signed_in = Slot(AppSignedInGroup)


class ShopServicer(BaseAuthGrpcServicer):
    project: "AppProject"

    async def Buy(self, item: str, context: ServicerContext) -> str:
        return await self.run_operation(self.project.shop.op_buy, item, context)


class AppProject(AuthProject):
    auth = Slot(AppAuth)
    shop = Slot(ShopUnit)
    servicer = Slot(ShopServicer)
