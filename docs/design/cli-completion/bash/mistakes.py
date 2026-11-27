"""What mypy refuses: the lines marked as errors."""

import typing as t

from ingots_stub import BaseCommand, CliCompletion, Project


class TagCommand(BaseCommand):
    @t.override
    @classmethod
    def _cli_complete(cls, project_cls: type[Project], dest: str) -> CliCompletion:
        # the words of the completion, not a list
        return ["vip", "beta"]  # error: a list is no CliCompletion

    @t.override
    async def _run(self) -> None:
        pass
