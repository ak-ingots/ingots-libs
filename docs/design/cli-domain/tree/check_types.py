"""
Runs the command line of the application: the commands of the defaults, of
both addons and of its own, at the paths they have today; only the units on
the path of a command are created. A domain unit in a unit of commands and
a join forgotten are refused at the creation of the class.
"""

import contextlib
import io

from addons import AuthCliUnit, GrpcCliUnit, GrpcUnit
from app import AppProject
from ingots_stub import CommandsUnit, CommandRunner, Slot


def run(*argv: str) -> tuple[AppProject, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        project = CommandRunner(AppProject, list(argv)).run()
    assert isinstance(project, AppProject)
    return project, out.getvalue().strip()


project, out = run("--config", "IS_DEBUG=on", "auth", "tags", "list")
assert out == "vip beta"
assert project.cli.cli_args.configs == (("IS_DEBUG", "on"),)
assert "_slot_grpc" not in project.cli.__dict__  # off the path, not created

assert run("settings", "list")[1] == "IS_DEBUG = False"
assert run("grpc", "export")[1] == "services.json"
assert run("shop", "count-orders")[1] == "3"

# a domain unit in a unit of commands
try:

    class Mixed(CommandsUnit):
        grpc = Slot(GrpcUnit)

except TypeError as error:
    assert "not on the command line" in str(error)
else:
    raise AssertionError("a domain unit under cli passed")

# the trees of two addons, not joined
try:
    type("Forgotten", (AuthCliUnit, GrpcCliUnit), {})
except TypeError:
    raise AssertionError("two units of commands, disjoint, need no join")

try:
    from addons import AuthProject, GrpcProject

    type("Forgotten", (AuthProject, GrpcProject), {})
except TypeError as error:
    assert "cli" in str(error)
else:
    raise AssertionError("a join of the command line forgotten passed")
