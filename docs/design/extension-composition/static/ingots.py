"""Static: the true classes of the children are threaded down as type parameters."""

import typing as t


class Project:
    pass


class Entity[P: Project]:
    def __init__(self, project: P) -> None:
        self._project: Project = project

    @property
    def project(self) -> P:  # read-only, or P is invariant and no subclass fits the bounds
        return t.cast(P, self._project)


class Unit[P: Project](Entity[P]):
    pass


# ingots/defaults


class Settings(Entity[Project]):
    DEBUG = False


class DefaultProject[S: Settings](Project):
    settings_cls: type[Settings] = Settings  # a subclass replaces it and the parameter

    def __init__(self) -> None:
        self._settings = self.settings_cls(self)

    @property
    def settings(self) -> S:
        return t.cast(S, self._settings)
