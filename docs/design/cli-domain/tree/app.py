"""
An application taking both addons: the trees of their commands joined in
one class, as the settings of two addons are.
"""

import typing as t

from addons import AuthCliUnit, AuthProject, GrpcCliUnit, GrpcProject
from ingots_stub import BaseCommand, CommandsUnit, Slot, Unit


class ShopUnit(Unit):
    def count_orders(self) -> int:
        return 3


class CountOrdersCommand(BaseCommand):
    project: "AppProject"

    @t.override
    async def _run(self) -> None:
        print(self.project.shop.count_orders())


class ShopCommandsUnit(CommandsUnit):
    count_orders = Slot(CountOrdersCommand)


class AppCliUnit(AuthCliUnit, GrpcCliUnit):
    shop = Slot(ShopCommandsUnit)


class AppProject(AuthProject, GrpcProject):
    shop = Slot(ShopUnit)
    cli = Slot(AppCliUnit)
