"""
Runs the fixtures as their consumers meet them: the tests of an addon,
configured by the test alone whatever the environment says, a project for
each test in its own event loop; the scenarios of an application run by its
command ``testing run``, configured as the application is, by the environment and
the command line, and by it only. mypy refuses the lines of ``mistakes.py``.
"""

import contextlib
import io
import os
import unittest

import addon_tests
import scenarios.test_play
from ingots_stub import LOGGING_CONFIGURED_BY, ProjectCliArgs, run_command
from scenarios import ScenariosProject
from testing_stub import RunTestsCommand, TestsFailedError


def run_module(module: object) -> unittest.TestResult:
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)  # type: ignore[arg-type]
    return unittest.TextTestRunner(verbosity=0).run(suite)


def main() -> None:
    # the tests of an addon: the environment of the developer is not theirs
    os.environ["INGOT_REDIS_PORT"] = "6379"
    result = run_module(addon_tests)
    assert result.wasSuccessful() and result.testsRun == 3, result
    first, second = addon_tests.LOOPS
    assert first is not second and first.is_closed() and second.is_closed()
    # the logging of the process is of unittest, not of the projects of tests
    assert LOGGING_CONFIGURED_BY == [], LOGGING_CONFIGURED_BY

    # the scenarios: the environment and the command line of the run
    os.environ["GAME_TEST_GAME_HOST"] = "game.local"
    os.environ["GAME_TEST_MAILPIT_URL"] = "http://mailpit.local:8025"
    # even told by the run, the fixtures leave the logging to the command
    os.environ["GAME_TEST_IS_CONFIGURE_LOGGING"] = "on"
    args = ProjectCliArgs(configs=(("GAME_PORT", "50061"),))
    run_command(ScenariosProject, lambda project: project.testing.run, args)
    assert RunTestsCommand.get_run(ScenariosProject) is None
    # once: the project of the command, not that of the scenario
    assert LOGGING_CONFIGURED_BY == [ScenariosProject], LOGGING_CONFIGURED_BY

    # the scenarios outside their command: an error telling how to run them
    with contextlib.redirect_stderr(io.StringIO()):
        result = run_module(scenarios.test_play)
    ((_, error),) = result.errors
    assert "OutsideRunError: run by: python -m scenarios testing run" in error, error

    # a run failing fails the command
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            run_command(ScenariosProject, lambda project: project.testing.run, ProjectCliArgs())
    except TestsFailedError:
        print("a failed run fails the command")
    else:
        raise AssertionError("the run passed on the defaults")


if __name__ == "__main__":
    main()
