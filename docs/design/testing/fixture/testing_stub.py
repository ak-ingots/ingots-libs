"""
The proposal, ``ingots.testing``: a project as a fixture of a test case, and
the project of the unit ``testing``, its command ``run`` running the tests
of the project with its configs.
"""

import asyncio
import contextlib
import os
import sys
import typing as t
import unittest
from collections.abc import Iterator, Mapping
from pathlib import Path

from ingots_stub import BaseCommand, Project, ProjectCliArgs

# what a project of a test gets, whatever the run says: its configs not
# printed, the logging of the process left to the run, unittest or ``testing run``
FIXTURE_CONFIGS: Mapping[str, str] = {
    "IS_PRINT_CONFIGS": "off",
    "IS_CONFIGURE_LOGGING": "off",
}


class TestsFailedError(Exception):
    """The tests of a run failed; the command exits non-zero."""


class OutsideRunError(Exception):
    """A test of a :class:`TestingProject` run outside ``testing run``."""


class ProjectFixture[P: Project]:
    """
    A project of a test case, created and configured for each test in its
    event loop, shut down after it, read as the attribute it is set to.
    Configured by its ``configs``, never by the environment, unless the
    tests run by ``testing run`` of a project of the same class: then as
    the command's own, the environment and the command line too. A
    :class:`TestingProject` is tested by that command only.
    """

    def __init__(self, cls: type[P], *, configs: Mapping[str, str] = {}) -> None:
        self.cls = cls
        self.configs = dict(configs)

    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...

    # any owner: a mixin declares a fixture too, a test case joins it
    @t.overload
    def __get__(self, obj: object, owner: type) -> P: ...

    def __get__(self, obj: object, owner: type) -> t.Self | P:
        if obj is None:
            return self
        try:
            return t.cast(P, t.cast(ProjectTestCase, obj)._projects[self])
        except (AttributeError, KeyError):
            raise RuntimeError("a project of a fixture exists during a test only")

    async def _create(self) -> P:
        run = RunTestsCommand.get_run(self.cls)
        if run is None and issubclass(self.cls, TestingProject):
            raise OutsideRunError(f"run by: python -m {self.cls.__module__} testing run")
        # what the test needs wins; what it leaves open the run gives
        configs = {**dict(run.configs if run else ()), **FIXTURE_CONFIGS, **self.configs}
        project = self.cls()
        project._cli_set_args(ProjectCliArgs(configs=tuple(configs.items())))
        with contextlib.nullcontext() if run else _hide_env(self.cls.env_configs_prefix):
            await project._configure()
        return project


class ProjectTestCase(unittest.IsolatedAsyncioTestCase):
    """
    A test case of the projects of its fixtures, of its class, its bases and
    its mixins, created before the ``asyncSetUp`` of the bases, which read
    them there: the last of the bases, after a contract of an addon.
    """

    _fixtures: t.ClassVar[tuple[ProjectFixture[t.Any], ...]] = ()
    _projects: dict[ProjectFixture[t.Any], Project]

    @t.override
    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        fixtures: dict[str, ProjectFixture[t.Any]] = {}
        for base in reversed(cls.__mro__):
            for name, value in vars(base).items():
                if isinstance(value, ProjectFixture):
                    fixtures[name] = value
        cls._fixtures = tuple(fixtures.values())

    @t.override
    async def asyncSetUp(self) -> None:
        self._projects = {}
        for fixture in self._fixtures:
            project = await fixture._create()
            self.addAsyncCleanup(project._do_shut_down)
            self._projects[fixture] = project
        await super().asyncSetUp()


class RunTestsCommand(BaseCommand):
    """
    ``python -m app testing run``: runs the tests found in the package of the
    project, ``test*.py``, its fixtures of the class of the project
    configured as the command is.
    """

    _runs: t.ClassVar[dict[type[Project], ProjectCliArgs]] = {}
    @classmethod
    def get_run(cls, project_cls: type[Project]) -> ProjectCliArgs | None:
        return cls._runs.get(project_cls)

    @t.override
    async def _run(self) -> None:
        project_cls = type(self.project)
        file = sys.modules[project_cls.__module__].__file__
        assert file is not None
        start = Path(file).parent
        self._runs[project_cls] = self.project.cli_args
        try:
            # a test case runs its own event loop: not in this running one
            is_ok = await asyncio.to_thread(self._run_tests, start)
        finally:
            del self._runs[project_cls]
        if not is_ok:
            raise TestsFailedError()

    def _run_tests(self, start: Path) -> bool:
        suite = unittest.defaultTestLoader.discover(
            str(start), top_level_dir=str(start.parent)
        )
        return unittest.TextTestRunner(verbosity=0).run(suite).wasSuccessful()


class TestingUnit:
    """The unit of the commands of the tests; a ``CliUnit`` in ingots."""

    def __init__(self) -> None:
        self.run = RunTestsCommand()  # a slot of the unit in ingots


class TestingProject(Project):
    """A project tested by its own command: ``python -m app testing run``."""

    testing: TestingUnit

    def __init__(self) -> None:
        super().__init__()
        self.testing = TestingUnit()  # testing = Slot(TestingUnit) in ingots


@contextlib.contextmanager
def _hide_env(prefix: str) -> Iterator[None]:
    hidden = {k: v for k, v in os.environ.items() if k.startswith(f"{prefix}_")}
    for name in hidden:
        del os.environ[name]
    try:
        yield
    finally:
        os.environ.update(hidden)
