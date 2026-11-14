"""
Runs the place of an entity: its parents and full name, known in its
``__init__``, the nearest parent of a kind; a kind of slot giving its
entities more before their ``__init__``; the permissions of a unit, bound by
its slot, their domain its full name, a unit placed twice of two domains;
an integration refused before it moves anything. mypy refuses the lines the
other file marks.
"""

import asyncio

from ingots_stub import OperationPermissionsError, Permissions, run
from shop import LabelledProject, LabelledUnit, ShopProject, ShopUnit, StockUnit


async def main() -> None:
    project = ShopProject()
    stock = project.shop.stock

    # the place
    assert (project.shop.full_name, stock.full_name) == ("shop", "shop.stock")
    assert stock.parents == (project, project.shop) and stock.parent is project.shop
    assert stock.opened_at == "shop.stock"  # in its __init__
    count = stock.op_count()
    assert (count.name, count.full_name) == ("op_count", "shop.stock.op_count")
    assert (count.parent, count.project) == (stock, project)
    audit = stock.audit.op_audit()
    assert audit.parents == (project, project.shop, stock, stock.audit)
    assert audit.find_parent(ShopUnit) is project.shop
    try:
        audit.find_parent(LabelledUnit)
    except LookupError as error:
        print("no parent:", error)
    else:
        raise AssertionError("a parent of no such kind is found")

    # a kind of slot
    labelled = LabelledProject()
    assert labelled.tagged.title == "#TAGGED"  # given by its slot before __init__

    # the permissions of a unit, bound by its slot
    assert StockUnit.permissions.flags is StockUnit.Flags  # the class: the enum
    assert stock.permissions.domain == "shop.stock"  # a unit: its domain
    assert stock.permissions is stock.permissions  # bound once a unit
    assert dict(stock.permissions(StockUnit.Flags.CAN_COUNT)) == {"shop.stock": 1}
    assert dict(count.get_permissions()) == {"shop.stock": 1}
    assert dict(project.outlet.op_count().get_permissions()) == {"outlet": 1}
    assert dict(audit.get_permissions()) == {"shop.stock": 1}  # of the stock above
    sell = project.shop.op_sell().get_permissions()
    assert dict(sell) == {"shop": 1, "shop.stock": 2}  # its own and of the move

    counter = Permissions({"shop.stock": StockUnit.Flags.CAN_COUNT})
    print(await run(stock.op_count, None, counter))
    try:
        await run(project.outlet.op_count, None, counter)
    except OperationPermissionsError as error:
        print("refused:", error)
    else:
        raise AssertionError("the domain of the outlet is the stock's")

    seller = Permissions(
        {"shop.stock": StockUnit.Flags.CAN_MOVE, "shop": ShopUnit.Flags.CAN_SELL}
    )
    assert await run(project.shop.op_sell, 3, seller) == 7
    try:
        await run(
            project.shop.op_sell, 3, Permissions({"shop": ShopUnit.Flags.CAN_SELL})
        )
    except OperationPermissionsError as error:
        print("refused before the move:", error)
    else:
        raise AssertionError("the permissions of the move are not asked")
    assert stock.count == 7


asyncio.run(main())
