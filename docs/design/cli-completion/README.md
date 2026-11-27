# The completion of the command line by a shell

- Status: Built, released as ingots 0.38.0 (2026-11-27)
- Packages: ingots
- Date: 2026-11-26
- ADRs: [0012](../../adr/0012-design-a-feature-before-building-it.md);
  follows [the command line, a domain](../cli-domain/README.md)

## Problem

An operator types the command lines of an application by heart: the
sub-commands of every addon, `auth tags list`, the options of each node,
the names of the configs after `--config`, the paths of the components
after `--component`. The tree is there, built from the classes without
creating anything; the shell knows none of it.

## Actors

- An operator: presses Tab.
- The author of an application: gives the command a name the shell can bind.
- The author of an addon: an option whose values are known.

## Stories

| # | Actor | Story | Now or later |
|---|---|---|---|
| <a id="cli-completion-1"></a>1 | operator | **`completion bash` prints a script; sourced, Tab completes the sub-commands and the options of the node at hand, the runner's at the root, and the value of an option, after a space or an `=`: its choices, the names of the configs, `--config=SHOP_` to `SHOP_PORT=`, the paths of the components, the files of `--configs-file`.**<br>• The program run three ways, each completed: a console script, `shop --debug unit --unit-param=val command --param=value`; a script, `python manage.py ...`, `python cli.py ...`; a module, `python -m shop ...`.<br>• A value given is skipped: `shop --config=SHOP_PORT=1 sh` completes `shop`.<br>• Installed once: a console script, `shop completion bash > ~/.local/share/bash-completion/completions/shop`, loaded by bash on the first Tab of `shop`; a script or a module, a file sourced by `.bashrc`, `python manage.py completion bash > ~/.local/share/ingots/completion/shop.bash`, no Python at the start of a shell. | now |
| <a id="cli-completion-2"></a>2 | author of an application | **I write nothing for it: the program is completed as it is run, a console script, a `manage.py`, a module.** | now |
| <a id="cli-completion-3"></a>3 | author of an addon | **An option with `choices` completes by itself; one whose values come from the project gives them by a hook of its node, `_cli_complete(project_cls, dest)`, from the classes.** | now |
| <a id="cli-completion-4"></a>4 | operator | **zsh, through `bashcompinit`; fish, a script of its own.** | zsh now, fish later |
| <a id="cli-completion-5"></a>5 | operator | **The values of a positional argument, the tests of `testing run`.** | later |

## Rules and examples

- Rule: the script is static, built from the classes as the parser builds
  the command line: no Python runs on Tab, where an application imports
  gRPC and its drivers in half a second.
  - Question: a script out of date after an upgrade? Built again by the same
    command; the packaging of an application may install it.
- Rule: `completion` is a command of the domain `cli` itself, so it is in
  `ingots/defaults/cli/commands.py`, its group in the root `CliUnit`, not in
  `extensions/`, which holds the commands of the other domains.
- Rule: the value of an option is completed by the hook of its node,
  `_cli_complete(project_cls, dest) -> CliCompletion`: `words`, `files`,
  `is_spaced` off when the value goes on after the word; its `choices` by
  default. The root completes `--config` and `--configs-file`,
  `components run-forever` its `--component`, all from the classes:
  `iter_configs` of the class of the configs, `slots_walk(Component)`.
- Rule: a command printing for a machine prints alone on the standard
  output: `IS_PRINT_CONFIGS` is off by default; on, the configs printed at
  the start go to the standard error, a diagnostic as the logs are, and a
  quiet command, `cli_is_quiet`, turns them off unless the command line
  turns them on: `settings list`, `logging info`, `components list`,
  `completion bash`, `perf plan`.
  - Example: `perf plan`, read by `eval`, has the same need, met by
    `--config IS_PRINT_CONFIGS=off` in its runner.
- Rule: the program is completed as it is run, told by `sys.argv[0]`, or
  named, `--command`, `--script`, `--module`:
  - a console script, `shop`: bash binds the completion to the name;
  - a script, `python manage.py`: bash completes `python`, so every script
    binds one function to `python` and `python3`, the same in each, which
    takes the script of the line by its absolute path, from the directory
    at hand, and calls the completion that script registered;
  - a module, `python -m shop`: the same function, by the name of the
    module;
  - the script run by itself, `./manage.py`, by its shebang,
    `#!/usr/bin/env -S uv run python`: a function bound to the name of the
    script, by its path; and `uv run manage.py`, `uv run python
    manage.py`, `uv run -m shop`: a function bound to `uv`.
  - Example: two projects on one host, each with its `manage.py`: each
    completes its own, in its directory or by a path to it.
  - Example: a `manage.py` of no project of ours, elsewhere: its path is
    registered by none, so bash completes its files. Only a file put at the
    very path of a registered one, a project removed and another cloned in
    its place, takes its completion, until its file is removed.
  - Example: `python other.py`: no project registered it, bash completes
    the files, as for any program. The completion of python that bash
    gives otherwise, of its own options, is taken over by this one.
  - Example: two console scripts of one name in two environments: bash
    binds a completion to the name, not the environment, so the last
    installed completes both; their commands are to be named apart.
- Rule: bash splits the words at `=`; the script joins them back, so that
  `--mode=fast` is one word, its value skipped, and completes what follows
  the `=` as the value of the option.
- Rule: the functions are prefixed `_ingots_`, their names made of word
  characters of the program, so that none meets the function of another
  tool, nor of another project.

## API sketch

The prototype is in [bash/](bash/): `ingots_stub.py` the command line of
the defaults with the completion, `app.py` two projects, a shop with
configs, a component and a command with choices, and a game;
`check_types.py` prints the scripts and runs bash on the command lines of
an operator, the three ways a program is run; `mistakes.py` what mypy
refuses.

```python
# an addon: an option of known values
class RestockCommand(BaseCommand):
    @classmethod
    def _cli_prepare_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--mode", dest="restock_mode", choices=("fast", "slow"))


# the defaults: values from the classes of the project
class RunComponentsForeverCommand(BaseCommand):
    @classmethod
    def _cli_complete(cls, project_cls: type[Project], dest: str) -> CliCompletion:
        return CliCompletion(words=tuple(walk_slots(project_cls, Component)))
```

```console
$ python manage.py completion bash > ~/.local/share/ingots/completion/shop.bash
$ python manage.py --config=SH<Tab>                         # SHOP_PORT=
$ python manage.py components run-forever --component <Tab>  # shop.server
$ python manage.py shop restock --mode=<Tab>                # fast slow
```

What is checked where: mypy, the type of what a hook gives; the
prototype, the script under bash; the tests of the slice, the same, bash
being on every host of CI.

## Pre-mortem

- The parser reads the options from `ArgumentParser._actions`, a private
  name of argparse: stable for two decades, argcomplete reads it too; a
  test of the slice runs the script under bash, so a change shows.
- `=` breaks the words of bash: `--config SHOP_PORT=` completes to `=` and
  stops there, the value the operator's.
- A component path is long, `grpc.servers.default`; bash completes it in one
  word, as it is.
- The completions of `python`, `uv` and `manage.py` are shared with other
  tools: a line not of ours goes to the completion bound to the name
  before, or that bash-completion loads for it on demand, `uv add`, the
  `manage.py` of Django, then to the files; the options of python and of
  `uv run` before the script are skipped, a value of an option of `uv run`
  it does not know leaving the line to uv.

## Alternatives

- **argcomplete**: bash, zsh and fish, mature; but a dependency of a
  package that has none, an extra at best, and Python on every Tab, the
  application imported each time.
- **`completion install` and `uninstall`**, the file written where it
  belongs and removed: the installation is three lines of the docs, read
  once; not worth commands of their own.
- **A hidden option the shell calls**, `app --complete <words>`: dynamic,
  no script to rebuild, the same price on Tab.

## Open questions

- fish: a script of its own from the same tree.
- A positional argument: the hook by its `dest` too, or nothing.
- A runner of its own options: the completion builds the root with those
  of `CommandRunner`; a subclass adding some is not seen.

## Slices

1. ingots: `completion bash`, the hook and `CliCompletion`, the values of
   the defaults, the configs printed at the start on the standard error;
   its first consumer, the tests running the script under bash, and an
   example's console script.
