"""
What the prototype needs of ingots: a project configured by its overrides,
the environment by its prefix then the command line, the later winning,
then the logging of the process unless told not to; a component bound to
the event loop it was created in; a command.
"""

import asyncio
import dataclasses
import os
import typing as t


@dataclasses.dataclass(frozen=True)
class ProjectCliArgs:
    """The options of the project on the command line, as in ingots."""

    configs: tuple[tuple[str, str], ...] = ()


class Configs:
    """A typed attribute a config, its default the value here."""

    IS_PRINT_CONFIGS: bool = True
    # new in ingots: off, the logging of the process is left to its owner
    IS_CONFIGURE_LOGGING: bool = True

    def apply(self, data: dict[str, str]) -> None:
        hints = t.get_type_hints(type(self))
        for name, raw in data.items():
            kind = hints[name]  # KeyError: no config of the name
            value: object = raw.lower() in ("1", "on", "true") if kind is bool else kind(raw)
            setattr(self, name, value)


class Client:
    """A component: its connection is of the loop that created it."""

    def __init__(self, host: str, port: int) -> None:
        self.host, self.port = host, port
        self._loop = asyncio.get_running_loop()
        self.is_closed = False

    async def call(self, what: str) -> str:
        assert asyncio.get_running_loop() is self._loop, "a client of another loop"
        assert not self.is_closed
        return f"{what} at {self.host}:{self.port}"

    async def close(self) -> None:
        self.is_closed = True


# the projects that configured the logging of the process, dictConfig in ingots
LOGGING_CONFIGURED_BY: list[type["Project"]] = []


class Project:
    env_configs_prefix: t.ClassVar[str] = "INGOT"
    configs: Configs

    def __init__(self) -> None:
        self.project = self
        self.cli_args = ProjectCliArgs()
        self._clients: list[Client] = []

    def _cli_set_args(self, args: ProjectCliArgs) -> None:
        self.cli_args = args

    async def _configure(self) -> None:
        prefix = f"{self.env_configs_prefix}_"
        data = {
            name.removeprefix(prefix): value
            for name, value in os.environ.items()
            if name.startswith(prefix)
        }
        data |= dict(self.cli_args.configs)
        self.configs.apply(data)
        if self.configs.IS_CONFIGURE_LOGGING:
            LOGGING_CONFIGURED_BY.append(type(self))

    async def _do_shut_down(self) -> None:
        for client in self._clients:
            await client.close()

    def _create_client(self, host: str, port: int) -> Client:
        client = Client(host, port)
        self._clients.append(client)
        return client


class BaseCommand:
    project: Project

    async def _run(self) -> None:
        raise NotImplementedError


def run_command[P: Project](
    project_cls: type[P], get_command: t.Callable[[P], BaseCommand], args: ProjectCliArgs
) -> None:
    """``python -m app <command> --config NAME=value``, as CommandRunner runs it."""

    async def main() -> None:
        project = project_cls()
        project._cli_set_args(args)
        await project._configure()
        command = get_command(project)
        command.project = project
        try:
            await command._run()
        finally:
            await project._do_shut_down()

    asyncio.run(main())
