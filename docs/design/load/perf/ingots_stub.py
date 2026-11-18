"""
What the prototype needs of ingots: a slot creating its entity once per
owner, a unit of a project, typed configs from the files of
``--configs-file``, INI, then the environment by its prefix, then
``--config`` of the command line, the later winning.
"""

import configparser
import json
import os
import typing as t
from pathlib import Path


class Entity:
    project: "Project"


class Slot[E: Entity]:
    """An entity of the class, created once for its owner, as in ingots."""

    def __init__(self, cls: type[E]) -> None:
        self.cls = cls

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    @t.overload
    def __get__(self, obj: object, owner: type) -> E: ...

    def __get__(self, obj: object, owner: type) -> "t.Self | E":
        if obj is None:
            return self
        try:
            return t.cast(E, obj.__dict__[self.name])
        except KeyError:
            entity = self.cls()
            entity.project = t.cast(Entity, obj).project
            obj.__dict__[self.name] = entity
            return entity


class Unit(Entity):
    pass


class Configs(Entity):
    """A typed attribute a config, its default the value here."""

    def apply(self, data: dict[str, str]) -> None:
        hints = t.get_type_hints(type(self))
        for name, raw in data.items():
            if name not in hints:
                raise KeyError(f"no config {name}")
            kind = hints[name]
            value: object
            if kind is bool:
                value = raw.lower() in ("1", "on", "true")
            elif t.get_origin(kind) is tuple:
                value = tuple(json.loads(raw))
            else:
                value = kind(raw)
            setattr(self, name, value)


class SettingsUnit(Unit):
    configs = Slot(Configs)


class Project(Entity):
    env_configs_prefix: t.ClassVar[str] = "INGOT"
    settings = Slot(SettingsUnit)

    def __init__(self) -> None:
        self.project = self

    def configure(
        self, files: t.Sequence[Path] = (), configs: t.Sequence[tuple[str, str]] = ()
    ) -> None:
        """The files in their order, the environment, the command line."""
        data: dict[str, str] = {}
        for path in files:
            parser = configparser.ConfigParser(allow_unnamed_section=True)
            parser.optionxform = str  # type: ignore[assignment,method-assign]
            parser.read_string(path.read_text())
            data |= {
                name: value
                for section in parser.sections()
                for name, value in parser.items(section)
            }
        prefix = f"{self.env_configs_prefix}_"
        data |= {
            name.removeprefix(prefix): value
            for name, value in os.environ.items()
            if name.startswith(prefix)
        }
        data |= dict(configs)
        self.settings.configs.apply(data)
