"""
Two addons with commands: ingot-auth, the tags of the profiles; ingot-grpcio,
the export of the services. Each keeps its domain clear of commands and
gives them a tree under ``cli``, as the defaults do.
"""

import typing as t

from ingots_stub import BaseCommand, CommandsUnit, CliUnit, Project, Slot, Unit

# -- ingot_auth ---------------------------------------------------------------


class AuthTagsUnit(Unit):
    """The registry of the tags: its operations, no command."""

    def list_tags(self) -> tuple[str, ...]:
        return ("vip", "beta")


class AuthUnit(Unit):
    tags = Slot(AuthTagsUnit)


class AuthListTagsCommand(BaseCommand):
    cli_description = "Prints the tags."
    project: "AuthProject"

    @t.override
    async def _run(self) -> None:
        print(" ".join(self.project.auth.tags.list_tags()))


class AuthTagsCommandsUnit(CommandsUnit):
    cli_description = "The tags of the profiles."
    list = Slot(AuthListTagsCommand)


class AuthCommandsUnit(CommandsUnit):
    tags = Slot(AuthTagsCommandsUnit)


class AuthCliUnit(CliUnit):
    auth = Slot(AuthCommandsUnit)


class AuthProject(Project):
    auth = Slot(AuthUnit)
    cli = Slot(AuthCliUnit)


# -- ingot_grpcio -------------------------------------------------------------


class GrpcUnit(Unit):
    def export(self) -> str:
        return "services.json"


class ExportGrpcCommand(BaseCommand):
    project: "GrpcProject"

    @t.override
    async def _run(self) -> None:
        print(self.project.grpc.export())


class GrpcCommandsUnit(CommandsUnit):
    export = Slot(ExportGrpcCommand)


class GrpcCliUnit(CliUnit):
    grpc = Slot(GrpcCommandsUnit)


class GrpcProject(Project):
    grpc = Slot(GrpcUnit)
    cli = Slot(GrpcCliUnit)
