"""What mypy refuses: each line of a mark of an error."""

import typing as t

from ingots_stub import (
    BaseOperation,
    Factory,
    OperationsOwner,
    Permissions,
    Project,
    Unit,
)
from shop import ShopUnit, StockUnit

# a flag alone tells no domain: a unit builds the mask
Permissions(StockUnit.Flags.CAN_COUNT)  # error: no domain


class OldUnit(Unit):
    def __init__(self, project: Project) -> None:
        super().__init__(project)  # error: the place is set, no argument


class SellingOperation(BaseOperation[None, None]):
    parent: StockUnit

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        permissions(ShopUnit.Flags.CAN_SELL)  # error: of another unit
        return permissions(permissions.flags.CAN_SELL)  # error: no such flag here

    @t.override
    async def _run(self, parameters: None) -> None:
        self.parent.op_sell()  # error: no such operation of its parent
        self.find_parent(StockUnit).count = "ten"  # error: of the type of the kind


class ForgottenOperation(BaseOperation[None, None]):
    """Its permissions forgotten: abstract, refused where a factory takes it."""

    @t.override
    async def _run(self, parameters: None) -> None:
        pass


class CarelessUnit(OperationsOwner, Unit):
    permissions = StockUnit.Flags  # error: an enum, not a slot binding it

    op_forgotten = Factory(ForgottenOperation)  # error: abstract, no permissions
