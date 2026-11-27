"""
Runs the completion: ``completion bash`` prints the script, bash sources
it and completes the command lines of an operator, run three ways: a
console script, ``shop``; a script, ``python manage.py``, by its path, two
projects on one host each completing its own; a module, ``python -m shop``.
Each node completes its sub-commands and its options, the runner's at the
root; an option its value, after a space or an ``=``: its choices, the
names of the configs, the paths of the components, the files. A value given
is skipped.
"""

import contextlib
import io
import pathlib
import re
import subprocess
import tempfile

from app import GameProject, ShopProject
from ingots_stub import CommandRunner, Project


def build(project_cls: type[Project], *target: str) -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        CommandRunner(project_cls, ["completion", "bash", *target]).run()
    return out.getvalue()


def complete(scripts: list[str], line: str, cwd: str = ".") -> list[str]:
    """
    What bash offers at the end of ``line``, an operator pressing Tab: the
    words split at the spaces and at ``=``, as bash splits them.
    """
    words = [
        part
        for word in line.split(" ")
        for part in (re.split("(=)", word) if word else [word])
        if part != "" or word == ""
    ]
    words_bash = " ".join(f"'{word}'" for word in words)
    program = "\n".join(
        [
            *scripts,
            f"COMP_WORDS=({words_bash}); COMP_CWORD={len(words) - 1}",
            # what bash calls for the command of the line
            "fn=$(complete -p \"${COMP_WORDS[0]}\" | sed -E 's/.* -F ([^ ]+) .*/\\1/')",
            '"$fn" "${COMP_WORDS[0]}"',
            "printf '%s\\n' \"${COMPREPLY[@]}\"",
        ]
    )
    result = subprocess.run(
        ["bash", "-c", program], capture_output=True, text=True, cwd=cwd, check=True
    )
    return sorted(filter(None, result.stdout.splitlines()))


# -- a console script ----------------------------------------------------------

SHOP = [build(ShopProject, "--command", "shop")]
ROOT = ["--config", "--configs-file", "--debug", "--graceful-timeout"]

assert complete(SHOP, "shop ") == [*ROOT, "completion", "components", "shop"]
assert complete(SHOP, "shop co") == ["completion", "components"]
assert complete(SHOP, "shop --d") == ["--debug"]
assert complete(SHOP, "shop --debug shop ") == ["restock"]
assert complete(SHOP, "shop shop restock ") == ["--mode"]
assert complete(SHOP, "shop shop restock --mode ") == ["fast", "slow"]
assert complete(SHOP, "shop shop restock --mode=") == ["fast", "slow"]
assert complete(SHOP, "shop shop restock --mode=f") == ["fast"]
assert complete(SHOP, "shop --config SH") == ["SHOP_PORT="]
assert complete(SHOP, "shop --config=SH") == ["SHOP_PORT="]
assert complete(SHOP, "shop --config ") == ["IS_DEBUG=", "SHOP_PORT="]
assert complete(SHOP, "shop --config SHOP_PORT=1 sh") == ["shop"]
assert complete(SHOP, "shop --config=SHOP_PORT=1 sh") == ["shop"]
assert complete(SHOP, "shop components run-forever --component ") == ["shop.server"]

with tempfile.TemporaryDirectory() as tmp:
    pathlib.Path(tmp, "shop.ini").touch()
    assert complete(SHOP, "shop --configs-file sh", cwd=tmp) == ["shop.ini"]
    assert complete(SHOP, "shop --configs-file=sh", cwd=tmp) == ["shop.ini"]

# -- a script, two projects on one host ----------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    for name in ("shop", "game"):
        pathlib.Path(tmp, name).mkdir()
        pathlib.Path(tmp, name, "manage.py").touch()
    scripts = [
        build(ShopProject, "--script", f"{tmp}/shop/manage.py"),
        build(GameProject, "--script", f"{tmp}/game/manage.py"),
    ]
    assert complete(scripts, "python manage.py --debug sh", f"{tmp}/shop") == ["shop"]
    assert complete(scripts, "python manage.py ga", f"{tmp}/game") == ["game"]
    assert complete(scripts, "python manage.py sh", f"{tmp}/game") == []
    assert complete(scripts, "python ../shop/manage.py sh", f"{tmp}/game") == ["shop"]
    # python of anything else: its files, the default of bash
    assert complete(scripts, "python other.py ", f"{tmp}/shop") == []

# -- a module -------------------------------------------------------------------

MODULE = [build(ShopProject, "--module", "shop")]
assert complete(MODULE, "python -m shop shop ") == ["restock"]
assert complete(MODULE, "python -m game ") == []
