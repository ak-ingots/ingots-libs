"""
What the prototype needs of ingots: the slots; the command line of the
defaults, its tree, its runner and, new, the completion of a shell built
from the classes (``ingots.defaults.cli``); the settings and the components
whose names it completes.
"""

import abc
import argparse
import asyncio
import enum
import os
import re
import shlex
import sys
import typing as t
import weakref
from collections.abc import Iterator
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
    def _slots_get_parents(self) -> "tuple[weakref.ref[SlotsOwner], ...]":
        return (weakref.ref(self),)


def walk_slots(owner: type[SlotsOwner], kind: type[Entity]) -> Iterator[str]:
    """The paths of the slots holding ``kind``, from the classes alone."""
    for name in owner.slots_names():
        held = getattr(owner, name).cls
        if issubclass(held, kind):
            yield name
        if issubclass(held, SlotsOwner):
            yield from (f"{name}.{path}" for path in walk_slots(held, kind))


# -- ingots.defaults.cli ------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class CliCompletion:
    """
    What completes the value of an option: ``words``, or the paths of the
    files; ``is_spaced`` off when the value goes on after the word, the
    ``=`` of ``--config NAME=``.
    """

    words: tuple[str, ...] = ()
    files: bool = False
    is_spaced: bool = True


class CliNode:
    """A participant of the command line: the root, a group, a command."""

    cli_description: t.ClassVar[str] = ""

    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        """Adds this node's options to its parser. Adds none by default."""

    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> object:
        return None

    @classmethod
    def _cli_complete(cls, project_cls: "type[Project]", dest: str) -> CliCompletion:
        """
        What completes the value of the option ``dest`` of this node, the
        classes of the project at hand: its ``choices`` by default.
        """
        return CliCompletion()

    @property
    def cli_args(self) -> object:
        return self._cli_args

    def _cli_set_args(self, args: object) -> None:
        self._cli_args = args


class BaseCommand(CliNode, Entity):
    @abc.abstractmethod
    async def _run(self) -> None:
        raise NotImplementedError


class CommandsUnit(CliNode, Unit):
    """A sub-command grouping the commands and the groups of its slots."""


@dataclass(frozen=True, slots=True)
class CliTree:
    """A node of the command tree: its sub-command, its class, its parser."""

    name: str
    path: tuple[str, ...]
    cls: type[CliNode]
    parser: argparse.ArgumentParser
    children: tuple["CliTree", ...] = ()


PATH = "_cli_command_path"


def build_tree(
    cls: type[CliNode],
    parser: argparse.ArgumentParser,
    name: str = "",
    path: tuple[str, ...] = (),
) -> CliTree:
    """The tree of the parsers, as the parser of the command line builds it."""
    cls._cli_prepare_parser(parser)
    if issubclass(cls, BaseCommand):
        parser.set_defaults(**{PATH: path})
        return CliTree(name, path, cls, parser)
    assert issubclass(cls, CommandsUnit)
    sub = parser.add_subparsers(required=True)
    children = []
    for slot_name in cls.slots_names():
        child: type[CliNode] = getattr(cls, slot_name).cls
        sub_name = slot_name.replace("_", "-")
        child_parser = sub.add_parser(sub_name)
        children.append(build_tree(child, child_parser, sub_name, (*path, slot_name)))
    return CliTree(name, path, cls, parser, tuple(children))


class CommandRunner(CliNode):
    """Runs the command of the command line; its own options at the root."""

    def __init__(self, project_cls: "type[Project]", argv: list[str]) -> None:
        self._project_cls = project_cls
        self._argv = argv

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--debug", dest="runner_debug", action="store_true")
        parser.add_argument("--graceful-timeout", dest="runner_graceful_timeout")

    @classmethod
    def build_tree(cls, project_cls: "type[Project]") -> CliTree:
        parser = argparse.ArgumentParser()
        cls._cli_prepare_parser(parser)
        return build_tree(project_cls.cli.cls, parser)

    def run(self) -> None:
        tree = self.build_tree(self._project_cls)
        namespace = tree.parser.parse_args(self._argv)
        project = self._project_cls()
        node: CliNode = project.cli
        node._cli_set_args(tree.cls._cli_build_args(namespace))
        for name in getattr(namespace, PATH):
            tree = next(child for child in tree.children if child.path[-1] == name)
            node = getattr(node, name)
            node._cli_set_args(tree.cls._cli_build_args(namespace))
        assert isinstance(node, BaseCommand)
        asyncio.run(node._run())


# -- ingots.defaults.cli.commands: the completion, a command of the domain ---


class CompletionKind(enum.Enum):
    """How the program is run, so how bash finds its completion."""

    COMMAND = "command"  # shop ..., a console script
    SCRIPT = "script"  # python manage.py ..., by the path of the script
    MODULE = "module"  # python -m shop ...


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletionTarget:
    kind: CompletionKind
    name: str  # the command, the absolute path of the script, the module

    @classmethod
    def from_argv(cls) -> t.Self:
        """The program run: ``sys.argv[0]``, or the module of ``__main__``."""
        argv0 = sys.argv[0]
        if os.path.basename(argv0) == "__main__.py":
            spec = sys.modules["__main__"].__spec__
            assert spec is not None
            module = spec.name.removesuffix(".__main__")
            return cls(kind=CompletionKind.MODULE, name=module)
        if argv0.endswith(".py"):
            return cls(kind=CompletionKind.SCRIPT, name=os.path.realpath(argv0))
        return cls(kind=CompletionKind.COMMAND, name=os.path.basename(argv0))


# what every script shares, defined again by each, the same: the words bash
# split at "=" joined back, ``--mode=fast`` one word; the completion of
# python, its script by its path from here, its module by its name
SHARED = r"""
declare -gA _INGOTS_PROGRAMS
_ingots_join_words() {
    words=() cword=0
    local i w
    for ((i = 0; i < ${#COMP_WORDS[@]}; i++)); do
        w=${COMP_WORDS[i]}
        if ((i > 0)) && [[ ${words[-1]} == -* ]] &&
            [[ $w == = || ${COMP_WORDS[i-1]} == = ]]; then
            words[-1]+=$w
        else
            words+=("$w")
        fi
        ((i == COMP_CWORD)) && cword=$((${#words[@]} - 1))
    done
}
_ingots_complete_python() {
    local key start=2
    if [[ ${COMP_WORDS[1]-} == -m ]]; then
        key="-m ${COMP_WORDS[2]-}" start=3
    elif [[ -n ${COMP_WORDS[1]-} ]]; then
        key=$(realpath -q -- "${COMP_WORDS[1]}")
    fi
    if ((COMP_CWORD >= start)) && [[ -n $key && -n ${_INGOTS_PROGRAMS[$key]-} ]]; then
        "${_INGOTS_PROGRAMS[$key]}" "$start"
    fi
}
"""


class BashCompletion:
    """
    The script of the completion of bash, built from the classes: for each
    node of the tree, its sub-commands and its options, the values of an
    option by the hook of its node; a word after an option taking a value is
    that value, not a sub-command, and so is what follows its ``=``.
    """

    def __init__(
        self,
        project_cls: "type[Project]",
        runner_cls: type[CommandRunner],
        target: CompletionTarget,
    ) -> None:
        self._project_cls = project_cls
        self._runner_cls = runner_cls
        self._target = target
        self._function = "_ingots" + re.sub(r"\W", "_", f"_{target.name}") + "_complete"

    def build(self) -> str:
        nodes = list(self._iter_nodes(self._runner_cls.build_tree(self._project_cls)))
        walk = [
            f'            "{node.key}|{child.tree.name}") node={child.key} ;;'
            for node in nodes
            for child in map(Node, node.tree.children)
        ] + [
            f'            "{node.key}|{option}") ((i++)) ;;'
            for node in nodes
            for option in node.valued_options()
        ]
        values = [
            f'        "{node.key}|{option}") {self._reply(completion)}; return ;;'
            for node in nodes
            for option, completion in node.completions(self._project_cls)
        ]
        words = [
            f'        "{node.key}") COMPREPLY=($(compgen -W '
            f"'{' '.join(node.words())}' -- \"$cur\")) ;;"
            for node in nodes
        ]
        return "\n".join(
            [
                SHARED.strip("\n"),
                f"{self._function}() {{",
                "    local start=$1 words cword node= i word option value cur",
                "    _ingots_join_words",
                "    cur=${words[cword]}",
                "    for ((i = start; i < cword; i++)); do",
                "        word=${words[i]}",
                "        [[ $word == -*=* ]] && continue",
                '        case "$node|$word" in',
                *walk,
                "        esac",
                "    done",
                "    if [[ $cur == -*=* ]]; then",
                "        option=${cur%%=*} value=${cur#*=}",
                "    else",
                "        option=${words[cword-1]} value=$cur",
                "    fi",
                "    COMPREPLY=()",
                '    case "$node|$option" in',
                *values,
                "    esac",
                '    case "$node" in',
                *words,
                "    esac",
                "}",
                *self._bind(),
                "",
            ]
        )

    def _bind(self) -> list[str]:
        target = self._target
        if target.kind is CompletionKind.COMMAND:
            return [
                f"{self._function}_bound() {{ {self._function} 1; }}",
                f"complete -F {self._function}_bound {target.name}",
            ]
        key = (
            target.name if target.kind is CompletionKind.SCRIPT else f"-m {target.name}"
        )
        return [
            f"_INGOTS_PROGRAMS[{shlex.quote(key)}]={self._function}",
            "complete -o default -F _ingots_complete_python python python3",
        ]

    def _iter_nodes(self, tree: CliTree) -> "Iterator[Node]":
        yield Node(tree)
        for child in tree.children:
            yield from self._iter_nodes(child)

    def _reply(self, completion: CliCompletion) -> str:
        if completion.files:
            return 'COMPREPLY=($(compgen -f -- "$value"))'
        words = " ".join(completion.words)
        reply = f"COMPREPLY=($(compgen -W '{words}' -- \"$value\"))"
        if not completion.is_spaced:
            reply += "; compopt -o nospace 2>/dev/null"
        return reply


class Node:
    """A node of the tree as the script sees it."""

    def __init__(self, tree: CliTree) -> None:
        self.tree = tree
        self.key = ".".join(tree.path)

    def valued_options(self) -> Iterator[str]:
        for action in self.tree.parser._actions:
            if action.nargs != 0:
                yield from action.option_strings

    def completions(
        self, project_cls: "type[Project]"
    ) -> Iterator[tuple[str, CliCompletion]]:
        for action in self.tree.parser._actions:
            if action.nargs == 0 or not action.option_strings:
                continue
            completion = self.tree.cls._cli_complete(project_cls, action.dest)
            if completion == CliCompletion() and action.choices:
                completion = CliCompletion(words=tuple(map(str, action.choices)))
            if completion != CliCompletion():
                for option in action.option_strings:
                    yield option, completion

    def words(self) -> list[str]:
        options = [
            option
            for action in self.tree.parser._actions
            for option in action.option_strings
            if option not in ("-h", "--help")
        ]
        return [*options, *(child.name for child in self.tree.children)]


@dataclass(frozen=True, slots=True, kw_only=True)
class BashCompletionCliArgs:
    target: CompletionTarget


class BashCompletionCommand(BaseCommand):
    """
    ``completion bash``: prints the script of the program run, or of the one
    named, ``--command shop``, ``--script manage.py``, ``--module shop``.
    """

    cli_args: BashCompletionCliArgs
    project: "Project"

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--command", dest="completion_command")
        group.add_argument("--script", dest="completion_script")
        group.add_argument("--module", dest="completion_module")

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> BashCompletionCliArgs:
        if namespace.completion_command:
            target = CompletionTarget(
                kind=CompletionKind.COMMAND, name=namespace.completion_command
            )
        elif namespace.completion_script:
            path = os.path.realpath(namespace.completion_script)
            target = CompletionTarget(kind=CompletionKind.SCRIPT, name=path)
        elif namespace.completion_module:
            target = CompletionTarget(
                kind=CompletionKind.MODULE, name=namespace.completion_module
            )
        else:
            target = CompletionTarget.from_argv()
        return BashCompletionCliArgs(target=target)

    @t.override
    async def _run(self) -> None:
        completion = BashCompletion(
            type(self.project), CommandRunner, self.cli_args.target
        )
        print(completion.build(), end="")


class CompletionCommandsUnit(CommandsUnit):
    bash = Slot(BashCompletionCommand)


# -- ingots.defaults: the configs and the components it completes ------------


class Configs(Entity):
    IS_DEBUG: t.ClassVar[bool] = False


def iter_config_names(cls: type[Configs]) -> Iterator[str]:
    return (name for name in dir(cls) if name.isupper())


class SettingsUnit(Unit):
    configs = Slot(Configs)


class Component(Entity):
    """A long-lived entity, a server, a client."""


class RunComponentsForeverCommand(BaseCommand):
    """``components run-forever --component PATH``."""

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--component", dest="run_forever_components")

    @t.override
    @classmethod
    def _cli_complete(cls, project_cls: "type[Project]", dest: str) -> CliCompletion:
        return CliCompletion(words=tuple(walk_slots(project_cls, Component)))

    @t.override
    async def _run(self) -> None:
        pass


class ComponentsCommandsUnit(CommandsUnit):
    run_forever = Slot(RunComponentsForeverCommand)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCliArgs:
    configs: tuple[str, ...] = ()


class CliUnit(CommandsUnit):
    """The root: the options of the project, the commands of the defaults."""

    cli_args: ProjectCliArgs
    components = Slot(ComponentsCommandsUnit)
    completion = Slot(CompletionCommandsUnit)

    @t.override
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--config", dest="project_configs", action="append")
        parser.add_argument("--configs-file", dest="project_configs_files")

    @t.override
    @classmethod
    def _cli_build_args(cls, namespace: argparse.Namespace) -> ProjectCliArgs:
        return ProjectCliArgs(configs=tuple(namespace.project_configs or ()))

    @t.override
    @classmethod
    def _cli_complete(cls, project_cls: "type[Project]", dest: str) -> CliCompletion:
        if dest == "project_configs":
            configs_cls = project_cls.settings.cls.configs.cls
            names = tuple(f"{name}=" for name in iter_config_names(configs_cls))
            return CliCompletion(words=names, is_spaced=False)
        if dest == "project_configs_files":
            return CliCompletion(files=True)
        return super()._cli_complete(project_cls, dest)


class Project(BaseProject):
    settings = Slot(SettingsUnit)
    cli = Slot(CliUnit)
