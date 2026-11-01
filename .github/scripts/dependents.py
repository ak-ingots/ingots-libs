"""
The tree of the ecosystem, read from the pyproject.toml of each repository as
its last fetch of main has it: who depends on whom, an extra included.

    dependents.py tree               the tree, each repository unfolded once
    dependents.py list PACKAGE       what depends on PACKAGE, through others too
    dependents.py behind [PACKAGE]   the pins on the latest tags; fails when behind
    dependents.py next               what can move or be released right now
"""

import graphlib
import pathlib
import subprocess
import sys
import tomllib
from collections.abc import Iterable

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = pathlib.Path(__file__).parent.parent.parent


def git(repo: str, *argv: str) -> str:
    command = ["git", "-C", str(ROOT / repo), *argv]
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def read_repos() -> list[str]:
    lines = (ROOT / "repos.txt").read_text().splitlines()
    return [line for line in lines if line and not line.startswith("#")]


def read_requirements(repo: str, ref: str = "origin/main") -> dict[str, Requirement]:
    project = tomllib.loads(git(repo, "show", f"{ref}:pyproject.toml"))["project"]
    extras = project.get("optional-dependencies", {}).values()
    lines = [
        *project.get("dependencies", []),
        *(line for extra in extras for line in extra),
    ]
    return {req.name: req for req in map(Requirement, lines)}


def read_tree() -> dict[str, dict[str, Requirement]]:
    """Each repository with what it requires of the ecosystem, dependencies first."""
    repos = read_repos()
    requirements = {repo: read_requirements(repo) for repo in repos}
    tree = {
        repo: {name: req for name, req in reqs.items() if name in repos}
        for repo, reqs in requirements.items()
    }
    return {
        repo: tree[repo] for repo in graphlib.TopologicalSorter(tree).static_order()
    }


def find_dependents(tree: dict[str, dict[str, Requirement]], package: str) -> list[str]:
    found = {package}
    for repo, requirements in tree.items():  # dependencies come first
        if found & requirements.keys():
            found.add(repo)
    return [repo for repo in tree if repo in found and repo != package]


def read_latest(repo: str) -> Version | None:
    tags = git(repo, "tag", "--list", "v*").split()
    return max((Version(tag.removeprefix("v")) for tag in tags), default=None)


def read_released(repo: str, ecosystem: Iterable[str]) -> dict[str, Requirement]:
    """What the latest release of a repository requires of the ecosystem."""
    latest = read_latest(repo)
    if latest is None:
        return {}
    requirements = read_requirements(repo, f"v{latest}")
    return {name: req for name, req in requirements.items() if name in ecosystem}


def takes_latest(requirements: dict[str, Requirement]) -> bool:
    return all(
        (latest := read_latest(name)) is not None and req.specifier.contains(latest)
        for name, req in requirements.items()
    )


def print_tree(tree: dict[str, dict[str, Requirement]]) -> None:
    seen = set()

    def find_children(repo: str) -> list[str]:
        # a child reached through another child is shown under that one
        children = [child for child, reqs in tree.items() if repo in reqs]
        indirect = {
            found for child in children for found in find_dependents(tree, child)
        }
        return [child for child in children if child not in indirect]

    def show(repo: str, depth: int) -> None:
        if repo in seen:
            print(f"{'  ' * depth}{repo} (above)")
            return
        seen.add(repo)
        print(f"{'  ' * depth}{repo}")
        for child in find_children(repo):
            show(child, depth + 1)

    for repo, requirements in tree.items():
        if not requirements:
            show(repo, 0)


def check_behind(
    tree: dict[str, dict[str, Requirement]], only: str | None = None
) -> int:
    behind = 0
    for repo, requirements in tree.items():
        for name, requirement in requirements.items():
            if only not in (None, name):
                continue
            is_fine = takes_latest({name: requirement})
            behind += not is_fine
            mark = "" if is_fine else f" <- behind {name} {read_latest(name)}"
            print(f"{repo:<16} {name}{requirement.specifier}{mark}")
    return 1 if behind else 0


def print_next(tree: dict[str, dict[str, Requirement]]) -> None:
    """
    A repository waits until all it requires is settled: moved and released, so
    that it moves once, whatever the number of its parents.
    """
    settled = set()
    found = False
    for repo, requirements in tree.items():  # dependencies come first
        if not settled.issuperset(requirements):
            continue
        if not takes_latest(requirements):
            print(f"{repo}: move on to the latest of its dependencies")
            found = True
        elif not takes_latest(read_released(repo, tree)):
            print(f"{repo}: release, main has moved")
            found = True
        else:
            settled.add(repo)
    if not found:
        print("nothing to do: every release takes the latest of its dependencies")


def main(command: str, *argv: str) -> int:
    tree = read_tree()
    if command == "tree":
        print_tree(tree)
    elif command == "list":
        print("\n".join(find_dependents(tree, *argv)))
    elif command == "behind":
        return check_behind(tree, *argv)
    elif command == "next":
        print_next(tree)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
