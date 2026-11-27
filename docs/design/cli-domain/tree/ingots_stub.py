"""
What the prototype needs of ingots: the place of an entity, its slots, the
check of a slot inherited from bases holding different classes (ADR 0018);
the command line, a domain of the defaults (``ingots.defaults.cli``); the
project of the defaults, its settings and components, each with its unit of
commands under ``cli``.
"""

import abc
import argparse
import asyncio
import typing as t
import weakref
from dataclasses import dataclass

# -- ingots.puer --------------------------------------------------------------


class Entity:
    """Under its parents, the project the first, its parent the last."""

    _entity_parents: "tuple[weakref.ref[SlotsOwner], ...]"

    def __init__(self) -> None:
        pass

    @property
    def project(self) -> "Project":
        return t.cast("Project", self._entity_parents[0]())

    @property
    def parent(self) -> "SlotsOwner":
        return t.cast("SlotsOwner", self._entity_parents[-1]())


class SlotsOwner:
    """What owns slots: the project, a unit."""

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        for name in set(cls.slots_names()) - set(vars(cls)):
            held = {
                getattr(base, name).cls for base in cls.__bases__ if hasattr(base, name)
            }
            if not any(all(issubclass(one, other) for other in held) for one in held):
                raise TypeError(f"{cls.__qualname__}.{name}: join {held} in a class")

    @classmethod
    def slots_names(cls) -> list[str]:
        """The names of the slots, in the order of their declaration."""
        names: dict[str, None] = {}
        for klass in reversed(cls.__mro__):
            names.update(
                (n, None) for n, v in vars(klass).items() if isinstance(v, Slot)
            )
        return list(names)

    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        raise NotImplementedError


class Slot[EntityType: Entity]:
    """One entity per parent, created on first access."""

    _name: str

    def __init__(self, cls: type[EntityType]) -> None:
        self._cls = cls

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @property
    def cls(self) -> type[EntityType]:
        return self._cls

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: SlotsOwner, owner: type) -> EntityType: ...

    def __get__(self, obj: SlotsOwner | None, owner: type) -> t.Self | EntityType:
        if obj is None:
            return self
        key = f"_slot_{self._name}"
        try:
            entity: EntityType = obj.__dict__[key]
        except KeyError:
            entity = self._cls.__new__(self._cls)
            entity._entity_parents = obj._slots_get_parents()
            entity.__init__()  # type: ignore[misc]
            obj.__dict__[key] = entity
        return entity


class Unit(SlotsOwner, Entity):
    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        return (*self._entity_parents, weakref.ref(self))


class BaseProject(SlotsOwner):
    """The root: the first parent of every entity."""

    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        return (weakref.ref(self),)


# -- ingots.defaults.cli ------------------------------------------------------


class CliNode:
    """A participant of the command line: a unit, a command, the runner."""

    cli_description: t.ClassVar[str] = ""

    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        """Adds this node's options to its parser. Adds none by default."""

    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> object:
        return None

    @property
    def cli_args(self) -> object:
        return self._cli_args

    def _cli_set_args(self, args: object) -> None:
        self._cli_args = args


class BaseCommand(CliNode, Entity):
    """A leaf of the command line, its sub-command the name of its slot."""

    @abc.abstractmethod
    async def _run(self) -> None:
        raise NotImplementedError


class CommandsUnit(CliNode, Unit):
    """
    A sub-command, the name of its slot, grouping the commands and the units
    of its slots, nothing else: anything else in a slot fails the class.
    """

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        for name in cls.slots_names():
            held = getattr(cls, name).cls
            if not issubclass(held, (CommandsUnit, BaseCommand)):
                raise TypeError(
                    f"{cls.__qualname__}.{name}: {held.__qualname__} is not on "
                    "the command line; a domain is reached by its project"
                )


class CommandRunner:
    """
    Parses the command line from the tree of ``project.cli``, every slot a
    sub-command; creates the units on the path of the command, and only them.
    """

    PATH: t.ClassVar[str] = "_cli_command_path"

    def __init__(self, project_cls: "type[Project]", argv: list[str]) -> None:
        self._project_cls = project_cls
        self._argv = argv

    def run(self) -> "Project":
        root = self._project_cls.cli.cls
        parser = argparse.ArgumentParser()
        nodes = self._prepare(parser, root, ())
        namespace = parser.parse_args(self._argv)
        path: tuple[str, ...] = getattr(namespace, self.PATH)
        project = self._project_cls()
        node: CliNode = project.cli
        node._cli_set_args(root._cli_build_args(namespace))
        for depth, name in enumerate(path, 1):
            node = getattr(node, name)
            node._cli_set_args(nodes[path[:depth]]._cli_build_args(namespace))
        assert isinstance(node, BaseCommand), node
        asyncio.run(node._run())
        return project

    def _prepare(
        self,
        parser: argparse.ArgumentParser,
        cls: type[CliNode],
        path: tuple[str, ...],
    ) -> dict[tuple[str, ...], type[CliNode]]:
        cls._cli_prepare_parser(parser)
        if issubclass(cls, BaseCommand):
            parser.set_defaults(**{self.PATH: path})
            return {}
        assert issubclass(cls, CommandsUnit)
        nodes: dict[tuple[str, ...], type[CliNode]] = {}
        sub = parser.add_subparsers(required=True)
        for name in cls.slots_names():
            child: type[CliNode] = getattr(cls, name).cls
            child_parser = sub.add_parser(name.replace("_", "-"))
            nodes[(*path, name)] = child
            nodes |= self._prepare(child_parser, child, (*path, name))
        return nodes


# -- ingots.defaults: the settings and the components, their commands --------


class Configs(Entity):
    IS_DEBUG: bool = False


class SettingsUnit(Unit):
    """The configs; no command, those are in ``cli.settings``."""

    configs = Slot(Configs)

    def print_configs(self) -> None:
        print(f"IS_DEBUG = {self.configs.IS_DEBUG}")


class ListConfigsCommand(BaseCommand):
    cli_description = "Prints the configs of the project."
    project: "Project"

    @t.override
    async def _run(self) -> None:
        self.project.settings.print_configs()


class SettingsCommandsUnit(CommandsUnit):
    cli_description = "The settings of the project."
    list = Slot(ListConfigsCommand)


class ComponentsUnit(Unit):
    def print_components(self) -> None:
        print("Components:")


class ListComponentsCommand(BaseCommand):
    project: "Project"

    @t.override
    async def _run(self) -> None:
        self.project.components.print_components()


class ComponentsCommandsUnit(CommandsUnit):
    list = Slot(ListComponentsCommand)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCliArgs:
    configs: tuple[tuple[str, str], ...] = ()


class CliUnit(CommandsUnit):
    """
    The root of the command line, ``project.cli``: the options of the
    project, ``--config``; the commands of the defaults, ``settings list``,
    ``components list``.
    """

    cli_args: ProjectCliArgs

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--config",
            dest="project_configs",
            action="append",
            default=[],
            type=lambda option: tuple(option.split("=", 1)),
        )

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> ProjectCliArgs:
        return ProjectCliArgs(configs=tuple(namespace.project_configs))

    settings = Slot(SettingsCommandsUnit)
    components = Slot(ComponentsCommandsUnit)


class Project(BaseProject):
    """The project of the defaults: its domains, the command line one of them."""

    settings = Slot(SettingsUnit)
    components = Slot(ComponentsUnit)
    cli = Slot(CliUnit)
