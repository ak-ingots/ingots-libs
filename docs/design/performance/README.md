# The cost of reaching a config through the project

Status: a measurement, taken on 2026-10-25 with ingots 0.31.0 (`272cb58`),
CPython 3.14.4 on x86_64. Not a decision.

## The question

What does a chain such as
`self.project.settings.configs.GRPC_DEFAULT_MAX_CONCURRENT_RPCS` cost,
and does it grow with the project: say 20 units and 500 configs?

## The numbers

The best time per access, from 5 repeats of a million calls each.
[`config_access_bench.py`](config_access_bench.py) builds the projects;
run it with `uv --directory ingots run python <path>`.

| Project | `….project.settings.configs.X` | `configs.X` (the configs in a variable) | a plain `dict["v"]` |
|---|---|---|---|
| 6 configs, 1 unit | 460 ns | 212 ns | 47 ns |
| 500 configs, 20 units | 463 ns | 219 ns | 45 ns |

## Why it does not grow

Every link of the chain is a hash lookup, O(1) at any size:

- `self.project`: a weakref dereferenced in a property;
- a slot (`settings`, `configs`): `obj.__dict__.get(key)`, because the
  entity is created once and kept in its owner's `__dict__`;
- a config: a class descriptor, found through CPython's type attribute
  cache, whose value is `configs._configs_values.get(name, default)`.

Nothing iterates over the units or the configs.

## What it means

- A config read at start, as servers and clients read theirs in
  `_configure()`, costs microseconds over the whole life of the process.
- Per request, half a microsecond is lost against the request itself: a
  unary gRPC call takes tens to hundreds of microseconds, a MongoDB query
  milliseconds.
- In a tight loop of millions of iterations, take the value into a local
  variable first, as for any attribute chain in Python.

## If it ever matters

About half of the cost of the config link is wrappers, not the lookup:
`BaseConfig.__get__` calls `get_value()`, and the `t.cast(...)` in it is
a function call at run time. Inlining the lookup into `__get__` would
likely make that link noticeably faster, at the price of a
`# type: ignore`. It is not worth doing until a real case shows the cost.
