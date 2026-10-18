# Extension composition: three concepts

Supporting material for [ADR 0004](../../adr/0004-static-composition-with-typed-slots.md).
A frozen snapshot of the prototypes compared while making the decision: not
maintained, not part of any package. Runner, CLI, lifecycle and object lifetime
are left out on purpose; only composition and customization are compared.

## The scenario

The same one in every concept:

- `ingots.py`: the framework core and its defaults (`Settings`, a default
  project holding them).
- `pkg1.py`: an addon with a tree three levels deep
  (`project.pkg1_unit.sub_unit.entity`) and its own settings.
- `pkg2.py`: an unrelated addon with its own settings.
- `app.py`: the application. It combines both addons, joins their settings,
  replaces pkg1's entity three levels deep with its own one, which calls
  `super()` and uses pkg2's unit and the app's setting.
- `check_types.py`: what mypy (and the IDE) sees, and what is rejected.

Common to all three: behaviour is extended by inheritance, so an override
that forgets `super()` silently cuts off the classes behind it in the MRO
(`AppEntity.method` relies on it). None of the concepts detects it.

```sh
cd <concept>
python3.14 app.py              # Pkg1Entity(pkg1) + Pkg2Unit(pkg2) + app
python3.14 check_types.py      # runtime types, runtime rejections
mypy --strict .                # static types; "error:" comments mark expected errors
```

## dynamic

Every entity class carries a descriptor (`cls.d`); addons and the application
register extensions on it in a cooperative `register_extensions()`. The
created instance is of a class built by `type()` from the "leaves" of the
registered classes, so diamonds merge without MRO errors.

- One operation per integration, at any depth: `Pkg1Entity.d.add(AppEntity)`.
  Settings of all addons are joined without any code.
- mypy sees the declared class, not the built one: `p.pkg1_unit.sub_unit.entity`
  is `Pkg1Entity`, `p.settings` is `Settings`. An addon reaches its own
  settings through `t.cast`; a mistake is an `AttributeError` at runtime.
- The bases of a built class come from a `set`: their order, and so which
  extension wins a conflict, changes between runs.
- Extensions are global state: a `Pkg2Project` in the same process gets pkg1's
  and the app's settings. Subclasses silently share their parent's descriptor.
  This is mostly harmless in production, where a process runs a single
  project; it hurts in development and testing, where several projects share
  one process.
- A `register_extensions()` without `super()` silently drops addons.

## static

The true classes of the children are threaded down as type parameters
(`Pkg1Unit[P, S]`, `Pkg1SubUnit[P, E]`, `Entity[P]`); each level has a
`*_cls` attribute and a property cast to the parameter.

- Everything is typed and checked: the deep entity is `AppEntity`, its project
  is `AppProject`, settings are `AppSettings`; unjoined settings are a mypy
  error.
- Parameters pile up: every level repeats the parameters of the levels below,
  and every addon class needs bounds with explicit arguments. mypy forbids
  cyclic parameter defaults, and a mutable `project` makes the parameters
  invariant, so no subclass fits the bounds (`project` has to be read-only).
- The parameter and the `*_cls` attribute say the same thing twice, and
  nothing checks that they agree (`Lying` in `check_types.py`).

Removing these problems while keeping the types led to the third concept:
the class attribute itself becomes the typed declaration, and a subclass
narrows it instead of re-threading parameters.

## slots

A parent declares its children as typed descriptors (`sub_unit =
Slot(Pkg1SubUnit)`); a subclass narrows a slot by assigning a subclass. An
entity narrows its back-reference with an annotation:
`project: "AppProject"`.

- Typed as precisely as static, without type parameters: one short class per
  level down to the customized entity.
- Slot conflicts are rejected twice: by mypy, and by `check_slots` when the
  class is created (a slot must hold a subclass of what every base holds).
  Two addons extending the same default need an explicit join class.
- A slot cannot be assigned on an instance (`__set__` rejects it, typed
  `Never` for mypy).
- The `project` annotation is a promise mypy does not verify: nothing stops
  `AppEntity` from being placed into another project's tree.
