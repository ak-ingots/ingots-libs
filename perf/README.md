# perf

The runner of the load on the dev server, outside the framework. The
design: [docs/design/load](../docs/design/load/README.md); what is loaded
and how: `ingots.perf` of ingots.

| Who | What | Where |
|---|---|---|
| scenario | what is loaded and how: a `PerfProject` | `<stand>/scenarios/<name>.py` |
| stand | the target up and down, how its scenarios run | `<stand>/stand` |
| runner | the host, the roles, the rounds, the cores of the load | `perf/run` |

## Files

- `run <stand> [<scenario>...] [-- <options>...]`: a run, the candidate
  against the baseline; every scenario of the stand unless named, the
  options of `ingots.perf` after `--`. `TRIAL=1` on a host that is not
  quiet: the run marked a trial, its reports in `work/` of the stand.
- `compose-stand --stand <dir> --example <dir> [--file <compose>]...`:
  the stand of Docker Compose, what `stand` of such a stand delegates to.
- `check-host [--system-cpus CPUS]`: the state of the host on stdout,
  why a run refuses on stderr, exiting 1.
- `tune-host on|off`, as root: the boost off and the cores steady, or back.

## The contract of a stand

```
<stand>/stand up TREE        # the target of TREE up; prints PERF_CGROUPS,
                             # PERF_SERVERS, NAME=value quoted for the shell
<stand>/stand down TREE      # the target of TREE down, its data too
<stand>/stand perf ARGS...   # python -m ingots.perf ARGS as its scenarios import
```

## A run

From the root of the meta repository, the stand named from it:

```sh
make -C perf tune-host               # once a boot, sudo; MODE=off gives it back
make -C perf check-host              # the IDE closed, Claude Code on the system cores
make -C perf run STAND=ingot-auth/perf/game
make -C perf run STAND=ingot-auth/perf/game SCENARIOS=sign-in \
    ARGS="--config PERF_ROUNDS=1"
TRIAL=1 make -C perf run STAND=...   # a trial on a busy host
```

An addon keeps two targets of its own: `make perf-build`, what
`compose-stand` builds a role by in its tree, and `make perf-smoke`, the
scenarios dry against its example, as its CI runs them, needing no meta
repository.

The reports land in `<stand>/reports/<scenario>/<date>-<time>-<host>.csv`
and `.ini`, the analysis printed at the end; those of a release are
committed with it.
