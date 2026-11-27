"""What mypy refuses: the lines marked as errors."""

import typing as t

from addons import AuthProject, AuthTagsCommandsUnit, GrpcProject
from ingots_stub import BaseCommand


# the projects of two addons with no join of their command lines
class Forgotten(AuthProject, GrpcProject):  # error: cli incompatible
    pass


class RenameTagCommand(BaseCommand):
    parent: AuthTagsCommandsUnit

    @t.override
    async def _run(self) -> None:
        # the parent of a command is its unit of commands, not the domain
        self.parent.list_tags()  # error: no list_tags
