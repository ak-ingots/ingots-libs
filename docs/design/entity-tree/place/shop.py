"""
An addon: a unit binding its permissions, its flags of its own, nested; its
operations building theirs by their parent, nothing imported; its place
known in its ``__init__``; placed twice; a sub-unit of no permissions, its
operation of those of the stock; a sale of the shop, the integration of a
move of the stock.
"""

import typing as t

from ingots_stub import (
    BaseOperation,
    Factory,
    OperationsOwner,
    PermissionFlags,
    Permissions,
    PermissionsSlot,
    Project,
    Slot,
    SlotsOwner,
    Unit,
)


class AuditOperation(BaseOperation[None, str]):
    """Under a sub-unit of no permissions: of those of the stock above it."""

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.find_parent(StockUnit).permissions
        return permissions(permissions.flags.CAN_COUNT)

    @t.override
    async def _run(self, parameters: None) -> str:
        stock = self.find_parent(StockUnit)
        return f"{stock.full_name}: {stock.count} audited"


class StockAuditUnit(Unit):
    op_audit = Factory(AuditOperation)


class CountOperation(BaseOperation[None, str]):
    parent: "StockUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_COUNT)

    @t.override
    async def _run(self, parameters: None) -> str:
        return f"{self.parent.full_name}: {self.parent.count}"


class MoveOperation(BaseOperation[int, int]):
    parent: "StockUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        return permissions(permissions.flags.CAN_MOVE)

    @t.override
    async def _run(self, parameters: int) -> int:
        self.parent.count -= parameters
        return self.parent.count


class StockUnit(OperationsOwner, Unit):
    class Flags(PermissionFlags):
        CAN_COUNT = 1 << 0
        CAN_MOVE = 1 << 1

    permissions = PermissionsSlot(Flags)

    op_count = Factory(CountOperation)
    op_move = Factory(MoveOperation)

    audit = Slot(StockAuditUnit)

    def __init__(self) -> None:
        super().__init__()
        self.count = 10
        self.opened_at = self.full_name  # the place, known already


class SellOperation(BaseOperation[int, int]):
    """
    An integration: its own flag, and the permissions of the operation of the
    stock it runs, not its flags, so that a caller lacking them is refused
    before anything is done.
    """

    parent: "ShopUnit"

    @t.override
    def _get_permissions(self) -> Permissions:
        permissions = self.parent.permissions
        move = self.parent.stock.op_move()
        return permissions(permissions.flags.CAN_SELL) | move.get_permissions()

    @t.override
    async def _run(self, parameters: int) -> int:
        # as its caller: the metadata passed on, here the stub runs it directly
        return await self.parent.stock.op_move()._run(parameters)


class ShopUnit(OperationsOwner, Unit):
    class Flags(PermissionFlags):
        CAN_SELL = 1 << 0

    permissions = PermissionsSlot(Flags)

    op_sell = Factory(SellOperation)

    stock = Slot(StockUnit)


class ShopProject(Project):
    shop = Slot(ShopUnit)
    outlet = Slot(StockUnit)  # the same unit elsewhere: a domain of its own


class LabelSlot[EntityType: "LabelledUnit"](Slot[EntityType]):
    """A kind of slot giving its entities a label before their ``__init__``."""

    @t.override
    def _prepare_entity(self, entity: EntityType, parent: SlotsOwner) -> None:
        entity.label = f"#{entity.full_name}"


class LabelledUnit(Unit):
    label: str

    def __init__(self) -> None:
        super().__init__()
        self.title = self.label.upper()


class LabelledProject(Project):
    tagged = LabelSlot(LabelledUnit)
