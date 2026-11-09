"""
Runs the hook of the permissions: the constant by default, the hook of an
operation by its project, an operation declaring neither refused when its
class is created; mypy refuses the lines the other files mark.
"""

import asyncio

from ingots_stub import BaseOperation, OperationPermissionsError, Permissions, run
from shop import ShopPay, ShopPermissions, ShopProject, ShopRefund


async def main() -> None:
    project = ShopProject()
    clerk = Permissions(ShopPermissions.CAN_PAY | ShopPermissions.CAN_REFUND)
    assert ShopPay.PERMISSIONS is ShopPay(project).get_permissions()  # one instance
    assert dict(ShopRefund(project).get_permissions()) == {"shop": 2}
    print("refund", await run_refund(project, clerk))

    project.REFUND_LIMIT = 0
    try:
        await run_refund(project, clerk)
    except OperationPermissionsError as error:
        print("refused:", error)
    else:
        raise AssertionError("the hook is not asked")

    try:

        class Forgotten(BaseOperation[int, int]):
            async def _run(self, parameters: int) -> int:
                return parameters

    except TypeError as error:
        print("refused:", error)
    else:
        raise AssertionError("an operation without permissions is accepted")


async def run_refund(project: ShopProject, caller: Permissions) -> int:
    return await run(project, ShopRefund, 5, caller)


asyncio.run(main())
