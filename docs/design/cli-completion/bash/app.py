"""
Two projects of one host. A shop: its configs, a server among its
components, its command with an option of choices; it writes nothing for
the completion, the choices complete by themselves, the names of the
configs and the paths of the components by the hooks of the defaults. A
game, its own command, completed apart.
"""

import argparse
import typing as t
from dataclasses import dataclass

from ingots_stub import (
    BaseCommand,
    CliUnit,
    CommandsUnit,
    Component,
    Configs,
    Project,
    SettingsUnit,
    Slot,
    Unit,
)


class ShopConfigs(Configs):
    SHOP_PORT: t.ClassVar[int] = 8080


class ShopSettingsUnit(SettingsUnit):
    configs = Slot(ShopConfigs)


class ShopServer(Component):
    pass


class ShopUnit(Unit):
    server = Slot(ShopServer)


@dataclass(frozen=True, slots=True, kw_only=True)
class RestockCliArgs:
    mode: str


class RestockCommand(BaseCommand):
    cli_args: RestockCliArgs

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--mode", dest="restock_mode", choices=("fast", "slow"))

    @t.override
    async def _run(self) -> None:
        pass


class ShopCommandsUnit(CommandsUnit):
    restock = Slot(RestockCommand)


class ShopCliUnit(CliUnit):
    shop = Slot(ShopCommandsUnit)


class ShopProject(Project):
    settings = Slot(ShopSettingsUnit)
    shop = Slot(ShopUnit)
    cli = Slot(ShopCliUnit)


# -- another project on the same host: a game ---------------------------------


class PlayCommand(BaseCommand):
    @t.override
    async def _run(self) -> None:
        pass


class GameCommandsUnit(CommandsUnit):
    play = Slot(PlayCommand)


class GameCliUnit(CliUnit):
    game = Slot(GameCommandsUnit)


class GameProject(Project):
    cli = Slot(GameCliUnit)
